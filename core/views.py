from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta, date, time
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import logout
from django.db.models import Q
import csv

from .models import (
    Employee, Task, Attendance, Department, Role, BreakSession,
    Announcement, Meeting, ITReport
)
from .forms import (
    EmployeeForm, TaskForm,
    AnnouncementForm, MeetingForm, ITReportForm
)
from .decorators import employee_login_required, manager_required


# -----------------------------
# AUTO CREATE ABSENT ATTENDANCE
# -----------------------------
def create_daily_absent_records():
    """
    Create attendance for all active employees for today.
    Only runs on weekdays (Mon-Fri).
    Default status = Absent
    """
    today = timezone.localdate()

    # Skip Saturday(5) and Sunday(6)
    if today.weekday() in (5, 6):
        return

    active_employees = Employee.objects.filter(is_active=True)

    for employee in active_employees:
        Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                "status": "Absent",
                "login_time": None,
                "logout_time": None,
                "late_by": timedelta(),
                "total_hours": timedelta(),
                "break_time": timedelta(),
                "net_working_hours": timedelta(),
                "is_on_break": False,
                "break_started_at": None,
            }
        )


def admin_logout(request):
    logout(request)
    return redirect("/admin")


# -----------------------------
# EMPLOYEE LOGIN
# -----------------------------
def employee_login(request):
    create_daily_absent_records()

    today = timezone.localdate()
    now = timezone.localtime(timezone.now())
    current_time = now.time()

    is_weekend_off = today.weekday() in (5, 6)  # Sat, Sun

    # Office timing
    LOGIN_START_TIME = time(10, 0)   # login allowed from 10:00 AM
    GRACE_TIME = time(10, 10)        # no delay till 10:10 AM

    is_before_login_time = current_time < LOGIN_START_TIME

    # AJAX: fetch roles by department
    if request.method == 'GET' and request.GET.get('dept_id'):
        dept_id = request.GET.get('dept_id')
        roles = Role.objects.filter(department_id=dept_id).values('id', 'name')
        return JsonResponse(list(roles), safe=False)

    if request.method == 'POST':
        if is_weekend_off:
            messages.error(request, "Today is off (Saturday/Sunday). Login is disabled.")
            return redirect('employee_login')

        if is_before_login_time:
            messages.error(request, "Login starts at 10:00 AM.")
            return redirect('employee_login')

        emp_id = request.POST.get('employee_id', '').strip()
        department_id = request.POST.get('department')
        password = request.POST.get('password', '').strip()

        try:
            employee = Employee.objects.get(
                employee_id=emp_id,
                department_id=department_id,
                is_active=True
            )
        except Employee.DoesNotExist:
            messages.error(request, "Invalid Employee ID / Department")
            return redirect('employee_login')

        if not employee.check_password(password):
            messages.error(request, "Invalid password")
            return redirect('employee_login')

        request.session['employee_id'] = employee.id

        login_time = current_time

        # Delay calculation only after 10:10 AM
        if login_time <= GRACE_TIME:
            late_by = timedelta()
        else:
            dt_login = datetime.combine(today, login_time)
            dt_grace = datetime.combine(today, GRACE_TIME)
            late_by = dt_login - dt_grace

        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                'login_time': login_time,
                'status': 'Present',
                'late_by': late_by,
                'total_hours': timedelta(),
                'break_time': timedelta(),
                'net_working_hours': timedelta()
            }
        )

        if attendance.login_time is None:
            attendance.login_time = login_time
            attendance.status = "Present"
            attendance.late_by = late_by
            attendance.save(update_fields=["login_time", "status", "late_by"])

        messages.success(request, "Login successful.")
        return redirect('employee_dashboard')

    departments = Department.objects.all()
    return render(request, 'login.html', {
        'departments': departments,
        'is_weekend_off': is_weekend_off,
        'today_name': today.strftime("%A"),
        'is_before_login_time': is_before_login_time,
        'login_start_time': "10:00 AM",
        'grace_time': "10:10 AM",
    })




# -----------------------------
# UPDATE TASK STATUS
# -----------------------------
@employee_login_required
def update_task_status(request, task_id):
    task = get_object_or_404(Task, id=task_id, employee__id=request.session['employee_id'])
    task.is_completed = True
    task.save()
    messages.success(request, f"Task '{task.title}' marked as completed!")
    return redirect('employee_dashboard')


# -----------------------------
# ASSIGN TASK VIEW
# -----------------------------
@employee_login_required
def assign_task(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    tasks = Task.objects.filter(employee=employee).order_by('-assigned_date')
    return render(request, 'assign_task.html', {'tasks': tasks, 'employee': employee})


def format_td(td):
    if not td:
        return "00h 00m 00s"
    total_seconds = int(td.total_seconds())
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}h {m:02d}m {s:02d}s"


# -----------------------------
# EMPLOYEE LOGOUT
# -----------------------------
@employee_login_required
def employee_logout(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    attendance = Attendance.objects.filter(employee=employee, date=date.today()).first()

    if not attendance or not attendance.login_time:
        messages.error(request, "Attendance not found for today.")
        return redirect('employee_dashboard')

    if attendance.is_on_break:
        bs = attendance.break_sessions.filter(end_at__isnull=True).order_by("-start_at").first()
        if bs:
            bs.close()
        attendance.is_on_break = False
        attendance.break_started_at = None
        attendance.save(update_fields=["is_on_break", "break_started_at"])

    tz = timezone.get_current_timezone()
    now = timezone.localtime(timezone.now())
    logout_time = now.time()

    dt_login = timezone.make_aware(datetime.combine(date.today(), attendance.login_time), tz)
    dt_logout = timezone.make_aware(datetime.combine(date.today(), logout_time), tz)

    # total time from login to logout (INCLUDING break time)
    total_work = dt_logout - dt_login

    total_break = timedelta()
    for bs in attendance.break_sessions.all():
        if bs.end_at:
            total_break += bs.duration
        else:
            total_break += (timezone.now() - bs.start_at)

    net_work = total_work - total_break
    if net_work < timedelta():
        net_work = timedelta()

    # check TOTAL time, not net working time
    if total_work < timedelta(hours=8):
        remaining = timedelta(hours=8) - total_work
        rem_sec = int(remaining.total_seconds())
        rh = rem_sec // 3600
        rm = (rem_sec % 3600) // 60
        rs = rem_sec % 60
        messages.error(
            request,
            f"You can logout after 8 hours total time. Remaining: {rh:02d}:{rm:02d}:{rs:02d}"
        )
        return redirect('employee_dashboard')

    attendance.logout_time = logout_time
    attendance.total_hours = total_work
    attendance.break_time = total_break
    attendance.net_working_hours = net_work
    attendance.status = "Present"
    attendance.is_on_break = False
    attendance.break_started_at = None
    attendance.save(update_fields=[
        "logout_time",
        "total_hours",
        "break_time",
        "net_working_hours",
        "status",
        "is_on_break",
        "break_started_at",
    ])

    request.session.flush()
    messages.success(request, "Logout successful. Have a great day!")
    return redirect('employee_login')

# -----------------------------
# EMPLOYEE DASHBOARD
# -----------------------------
@employee_login_required
def employee_dashboard(request):
    create_daily_absent_records()

    employee = Employee.objects.get(id=request.session['employee_id'])

    attendance = Attendance.objects.filter(employee=employee, date=date.today()).first()
    tasks = Task.objects.filter(employee=employee).order_by('-assigned_date')

    total_seconds = 0
    break_seconds = 0
    late_display = None
    status = "Present"
    is_on_break = False

    # NEW: break limit config
    BREAK_LIMIT_SECONDS = 3600
    break_limit_reached = False

    if attendance and attendance.login_time:
        tz = timezone.get_current_timezone()
        now = timezone.localtime(timezone.now())
        dt_login = timezone.make_aware(datetime.combine(date.today(), attendance.login_time), tz)

        office_start = timezone.make_aware(datetime.combine(date.today(), time(10, 10)), tz)
        if dt_login > office_start:
            late_seconds = int((dt_login - office_start).total_seconds())
            h = late_seconds // 3600
            m = (late_seconds % 3600) // 60
            s = late_seconds % 60
            late_display = f"{h:02d}:{m:02d}:{s:02d}"

        total_break = timedelta()
        sessions = attendance.break_sessions.all().order_by("start_at")
        for bs in sessions:
            if bs.end_at:
                total_break += bs.duration
            else:
                total_break += (timezone.now() - bs.start_at)

        # NEW: if total break >= 1 hour, cap it and stop active break
        if total_break >= timedelta(hours=1):
            total_break = timedelta(hours=1)
            break_limit_reached = True

            if attendance.is_on_break:
                open_bs = attendance.break_sessions.filter(end_at__isnull=True).order_by("-start_at").first()
                if open_bs:
                    used_break = timedelta()
                    for old_bs in attendance.break_sessions.exclude(id=open_bs.id):
                        if old_bs.end_at:
                            used_break += old_bs.duration

                    remaining_break = timedelta(hours=1) - used_break
                    if remaining_break < timedelta():
                        remaining_break = timedelta()

                    forced_end = open_bs.start_at + remaining_break
                    now_dt = timezone.now()

                    if forced_end > now_dt:
                        forced_end = now_dt
                    if forced_end < open_bs.start_at:
                        forced_end = open_bs.start_at

                    open_bs.end_at = forced_end
                    open_bs.duration = open_bs.end_at - open_bs.start_at
                    open_bs.save(update_fields=["end_at", "duration"])

                attendance.is_on_break = False
                attendance.break_started_at = None
                attendance.save(update_fields=["is_on_break", "break_started_at"])

        break_seconds = int(total_break.total_seconds())
        total_seconds = max(0, int((now - dt_login).total_seconds()))
        net_seconds = max(0, total_seconds - break_seconds)

        attendance.break_time = total_break
        attendance.net_working_hours = timedelta(seconds=net_seconds)
        attendance.total_hours = timedelta(seconds=total_seconds)
        attendance.status = "Present"
        attendance.save(update_fields=["break_time", "net_working_hours", "total_hours", "status"])

        is_on_break = attendance.is_on_break

    last7 = Attendance.objects.filter(employee=employee).order_by("-date")[:7]
    last7 = list(reversed(last7))

    chart_labels = []
    chart_total_hours = []
    chart_break_hours = []
    chart_late_minutes = []

    for r in last7:
        chart_labels.append(r.date.strftime("%d-%b"))
        total_h = (r.total_hours.total_seconds() if r.total_hours else 0) / 3600
        break_h = (r.break_time.total_seconds() if r.break_time else 0) / 3600
        late_m = (r.late_by.total_seconds() if r.late_by else 0) / 60
        chart_total_hours.append(round(total_h, 2))
        chart_break_hours.append(round(break_h, 2))
        chart_late_minutes.append(int(late_m))

    today_now = timezone.localdate()

    announcements = Announcement.objects.filter(is_active=True).filter(
        Q(is_for_all=True) | Q(department=employee.department)
    ).order_by("-created_at")

    announcements = [
        a for a in announcements
        if not a.expiry_date or a.expiry_date >= today_now
    ][:5]

    upcoming_meetings = Meeting.objects.filter(
        status="Scheduled",
        date__gte=today_now
    ).filter(
        Q(department=employee.department) | Q(participants=employee)
    ).distinct().order_by("date", "start_time")[:5]

    return render(request, 'dashboard.html', {
        'employee': employee,
        'attendance': attendance,
        'tasks': tasks,
        'working_seconds': total_seconds,  # total time including break
        'break_seconds': break_seconds,
        'late_display': late_display,
        'status': status,
        'is_on_break': is_on_break,
        'target_seconds': 8 * 3600,

        'chart_labels': chart_labels,
        'chart_total_hours': chart_total_hours,
        'chart_break_hours': chart_break_hours,
        'chart_late_minutes': chart_late_minutes,

        'announcements': announcements,
        'upcoming_meetings': upcoming_meetings,
        'is_manager': employee.is_manager(),

        # NEW
        'break_limit_seconds': BREAK_LIMIT_SECONDS,
        'break_limit_reached': break_limit_reached,
    })


# -----------------------------
# START BREAK
# -----------------------------
@employee_login_required
@require_POST
def start_break(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    attendance = Attendance.objects.filter(employee=employee, date=date.today()).first()

    if not attendance or not attendance.login_time:
        return JsonResponse({"ok": False, "msg": "Login first."})

    if attendance.is_on_break:
        return JsonResponse({"ok": False, "msg": "Break already started."})

    # NEW: total break limit = 1 hour
    total_break = timedelta()
    for bs in attendance.break_sessions.all():
        if bs.end_at:
            total_break += bs.duration
        else:
            total_break += (timezone.now() - bs.start_at)

    if total_break >= timedelta(hours=1):
        attendance.is_on_break = False
        attendance.break_started_at = None
        attendance.break_time = timedelta(hours=1)
        attendance.save(update_fields=["is_on_break", "break_started_at", "break_time"])
        return JsonResponse({"ok": False, "msg": "Break limit of 1 hour is completed."})

    now = timezone.now()
    BreakSession.objects.create(attendance=attendance, start_at=now)
    attendance.is_on_break = True
    attendance.break_started_at = now
    attendance.save(update_fields=["is_on_break", "break_started_at"])

    return JsonResponse({"ok": True})


# -----------------------------
# END BREAK
# -----------------------------
@employee_login_required
@require_POST
def end_break(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    attendance = Attendance.objects.filter(employee=employee, date=date.today()).first()

    if not attendance or not attendance.login_time:
        return JsonResponse({"ok": False, "msg": "Login first."})

    # NEW: total break limit = 1 hour
    total_break = timedelta()
    for bs in attendance.break_sessions.all():
        if bs.end_at:
            total_break += bs.duration
        else:
            total_break += (timezone.now() - bs.start_at)

    if total_break >= timedelta(hours=1):
        open_bs = attendance.break_sessions.filter(end_at__isnull=True).order_by("-start_at").first()
        if open_bs:
            used_break = timedelta()
            for old_bs in attendance.break_sessions.exclude(id=open_bs.id):
                if old_bs.end_at:
                    used_break += old_bs.duration

            remaining_break = timedelta(hours=1) - used_break
            if remaining_break < timedelta():
                remaining_break = timedelta()

            forced_end = open_bs.start_at + remaining_break
            now_dt = timezone.now()

            if forced_end > now_dt:
                forced_end = now_dt
            if forced_end < open_bs.start_at:
                forced_end = open_bs.start_at

            open_bs.end_at = forced_end
            open_bs.duration = open_bs.end_at - open_bs.start_at
            open_bs.save(update_fields=["end_at", "duration"])

        attendance.is_on_break = False
        attendance.break_started_at = None
        attendance.break_time = timedelta(hours=1)
        attendance.save(update_fields=["is_on_break", "break_started_at", "break_time"])
        return JsonResponse({"ok": False, "msg": "Break limit of 1 hour is completed."})

    if not attendance.is_on_break:
        return JsonResponse({"ok": False, "msg": "Break is not running."})

    bs = attendance.break_sessions.filter(end_at__isnull=True).order_by("-start_at").first()
    if bs:
        bs.close()

    # NEW: if after closing the break reaches 1 hour, lock break actions
    total_break = timedelta()
    for item in attendance.break_sessions.all():
        if item.end_at:
            total_break += item.duration

    if total_break > timedelta(hours=1):
        total_break = timedelta(hours=1)

    attendance.is_on_break = False
    attendance.break_started_at = None
    attendance.break_time = total_break
    attendance.save(update_fields=["is_on_break", "break_started_at", "break_time"])

    return JsonResponse({"ok": True})





# -----------------------------
# ADD EMPLOYEE
# -----------------------------
def add_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.set_password(employee.phone)
            employee.save()
            messages.success(request, "Employee added successfully. Password is phone number.")
            return redirect('add_employee')
    else:
        form = EmployeeForm()
    return render(request, 'add_employee.html', {'emp_form': form})


# -----------------------------
# ATTENDANCE REPORT
# -----------------------------
@employee_login_required
def attendance_report(request):
    create_daily_absent_records()

    employee = Employee.objects.get(id=request.session['employee_id'])

    month = request.GET.get("month", "")
    export = request.GET.get("export", "")

    qs = employee.attendance.all().order_by("-date")

    if month:
        try:
            y, m = month.split("-")
            y = int(y)
            m = int(m)
            qs = qs.filter(date__year=y, date__month=m)
        except:
            pass

    records = list(qs.order_by("date"))

    for r in records:
        r.total_hours_fmt = format_td(r.total_hours)
        r.break_time_fmt = format_td(r.break_time)
        r.net_working_fmt = format_td(r.net_working_hours)

    if export == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="attendance_report.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date", "Login Time", "Logout Time", "Total Time", "Break Time", "Net Time", "Late By (min)", "Status"])

        for r in records:
            late_min = int((r.late_by.total_seconds() if r.late_by else 0) / 60)
            writer.writerow([
                r.date.strftime("%Y-%m-%d"),
                r.login_time.strftime("%I:%M %p") if r.login_time else "--",
                r.logout_time.strftime("%I:%M %p") if r.logout_time else "--",
                r.total_hours_fmt,
                r.break_time_fmt,
                r.net_working_fmt,
                late_min,
                r.status or ""
            ])
        return response

    chart_labels = []
    chart_total = []
    chart_break = []
    chart_net = []
    chart_late_minutes = []

    for r in records:
        chart_labels.append(r.date.strftime("%d %b"))
        total_h = (r.total_hours.total_seconds() if r.total_hours else 0) / 3600
        break_h = (r.break_time.total_seconds() if r.break_time else 0) / 3600
        net_h = (r.net_working_hours.total_seconds() if r.net_working_hours else 0) / 3600
        late_m = int((r.late_by.total_seconds() if r.late_by else 0) / 60)

        chart_total.append(round(total_h, 2))
        chart_break.append(round(break_h, 2))
        chart_net.append(round(net_h, 2))
        chart_late_minutes.append(late_m)

    months = []
    seen = set()
    for r in employee.attendance.all().order_by("-date"):
        key = r.date.strftime("%Y-%m")
        if key not in seen:
            seen.add(key)
            months.append(key)
        if len(months) >= 12:
            break

    return render(request, 'attendance_report.html', {
        "records": records,
        "month": month,
        "months": months,
        "chart_labels": chart_labels,
        "chart_total": chart_total,
        "chart_break": chart_break,
        "chart_net": chart_net,
        "chart_late_minutes": chart_late_minutes,
    })


# -----------------------------
# AJAX: GET ROLES
# -----------------------------
def get_roles(request):
    department_id = request.GET.get('department_id')
    roles = Role.objects.filter(department_id=department_id).values('id', 'name')
    return JsonResponse(list(roles), safe=False)


# -----------------------------
# EMPLOYEE: SUBMIT IT REPORT
# -----------------------------
@employee_login_required
def submit_it_report(request):
    employee = Employee.objects.get(id=request.session['employee_id'])

    if request.method == 'POST':
        form = ITReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.employee = employee
            report.save()
            messages.success(request, "IT report submitted successfully.")
            return redirect('my_it_reports')
    else:
        form = ITReportForm()

    return render(request, 'submit_report.html', {
        'form': form,
        'employee': employee
    })


# -----------------------------
# EMPLOYEE: MY IT REPORTS
# -----------------------------
@employee_login_required
def my_it_reports(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    reports = ITReport.objects.filter(employee=employee)
    return render(request, 'my_it_reports.html', {
        'reports': reports,
        'employee': employee
    })


# -----------------------------
# MANAGEMENT DASHBOARD
# -----------------------------
@manager_required
def management_dashboard(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    today = timezone.localdate()

    total_employees = Employee.objects.filter(is_active=True).count()
    present_today = Attendance.objects.filter(date=today, status="Present").count()
    absent_today = Attendance.objects.filter(date=today, status="Absent").count()
    pending_tasks = Task.objects.filter(is_completed=False).count()
    open_it_reports = ITReport.objects.filter(status__in=["Open", "In Progress"]).count()
    upcoming_meetings = Meeting.objects.filter(status="Scheduled", date__gte=today).order_by("date", "start_time")[:5]
    latest_announcements = Announcement.objects.filter(is_active=True).order_by("-created_at")[:5]

    return render(request, 'management_dashboard.html', {
        'employee': employee,
        'total_employees': total_employees,
        'present_today': present_today,
        'absent_today': absent_today,
        'pending_tasks': pending_tasks,
        'open_it_reports': open_it_reports,
        'upcoming_meetings': upcoming_meetings,
        'latest_announcements': latest_announcements,
    })


@manager_required
def add_announcement(request):
    employee = Employee.objects.get(id=request.session['employee_id'])

    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = employee
            announcement.save()
            messages.success(request, "Announcement created successfully.")
            return redirect('announcement_list')
    else:
        form = AnnouncementForm()

    return render(request, 'add_announcement.html', {'form': form})






@manager_required
def add_meeting(request):
    employee = Employee.objects.get(id=request.session['employee_id'])

    if request.method == 'POST':
        form = MeetingForm(request.POST)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.created_by = employee
            meeting.save()
            form.save_m2m()
            messages.success(request, "Meeting scheduled successfully.")
            return redirect('meeting_list')
    else:
        form = MeetingForm()

    return render(request, 'add_meeting.html', {'form': form})


# -----------------------------
# MANAGEMENT: IT REPORTS
# -----------------------------
@manager_required
def management_it_reports(request):
    reports = ITReport.objects.all()
    return render(request, 'management_it_reports.html', {'reports': reports})


@manager_required
def update_it_report_status(request, report_id):
    report = get_object_or_404(ITReport, id=report_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ["Open", "In Progress", "Resolved", "Closed"]:
            report.status = new_status
            report.save(update_fields=["status", "updated_at"])
            messages.success(request, "IT report status updated.")

    return redirect('management_it_reports')



@employee_login_required
def announcement_list(request):
    employee = Employee.objects.get(id=request.session['employee_id'])

    announcements = Announcement.objects.filter(
        models.Q(is_for_all=True) | models.Q(department=employee.department),
        is_active=True
    ).order_by("-created_at")

    return render(request, "announcement_list.html", {
        "announcements": announcements
    })


@employee_login_required
def meeting_list(request):
    employee = Employee.objects.get(id=request.session['employee_id'])

    meetings = Meeting.objects.filter(
        models.Q(participants=employee) | models.Q(department=employee.department)
    ).distinct().order_by("date", "start_time")

    return render(request, "meeting_list.html", {
        "meetings": meetings
    })
    
