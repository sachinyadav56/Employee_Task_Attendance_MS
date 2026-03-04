from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta, date, time
from django.views.decorators.http import require_POST
from .models import BreakSession

from .models import Employee, Task, Attendance, Department, Role
from .forms import EmployeeForm, TaskForm
from .decorators import employee_login_required
from django.http import JsonResponse


# EMPLOYEE LOGIN
def employee_login(request):
    # ✅ Weekend OFF check (Saturday=5, Sunday=6)
    today = timezone.localdate()
    is_weekend_off = today.weekday() in (5, 6)  # Sat, Sun

    # AJAX: fetch roles by department (keep as is)
    if request.method == 'GET' and request.GET.get('dept_id'):
        dept_id = request.GET.get('dept_id')
        roles = Role.objects.filter(department_id=dept_id).values('id', 'name')
        return JsonResponse(list(roles), safe=False)

    if request.method == 'POST':
        # ✅ Block login on Saturday/Sunday
        if is_weekend_off:
            messages.error(request, "Today is off (Saturday/Sunday). Login is disabled.")
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
            messages.error(request, "Invalid Employee ID / Department / Role")
            return redirect('employee_login')

        if not employee.check_password(password):
            messages.error(request, "Invalid password")
            return redirect('employee_login')

        request.session['employee_id'] = employee.id

        now = timezone.localtime(timezone.now())
        login_time = now.time()
        GRACE_TIME = time(10, 15)

        # ✅ CHANGE: status always Present if logged in
        if login_time <= GRACE_TIME:
            late_by = timedelta()
        else:
            dt_login = datetime.combine(date.today(), login_time)
            dt_grace = datetime.combine(date.today(), GRACE_TIME)
            late_by = dt_login - dt_grace

        status = "Present"

        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=date.today(),
            defaults={
                'login_time': login_time,
                'status': status,
                'late_by': late_by,
                'total_hours': timedelta(),
                'break_time': timedelta(),
                'net_working_hours': timedelta()
            }
        )

        if not created and not attendance.login_time:
            attendance.login_time = login_time
            attendance.status = status
            attendance.late_by = late_by
            attendance.save()

        messages.success(request, "Login successful")
        return redirect('employee_dashboard')

    departments = Department.objects.all()

    # ✅ Pass flag + day name to template for banner
    return render(request, 'login.html', {
        'departments': departments,
        'is_weekend_off': is_weekend_off,
        'today_name': today.strftime("%A"),
    })


# EMPLOYEE DASHBOARD
# views.py (inside employee_dashboard)

from .models import BreakSession  # add this import

@employee_login_required
def employee_dashboard(request):
    employee = Employee.objects.get(id=request.session['employee_id'])

    attendance = Attendance.objects.filter(employee=employee, date=date.today()).first()
    tasks = Task.objects.filter(employee=employee).order_by('-assigned_date')

    working_seconds = 0     # ✅ NET working seconds (live)
    break_seconds = 0       # ✅ total break seconds (live)
    late_display = None
    status = "Present"
    is_on_break = False

    if attendance and attendance.login_time:
        tz = timezone.get_current_timezone()
        now = timezone.localtime(timezone.now())
        dt_login = timezone.make_aware(datetime.combine(date.today(), attendance.login_time), tz)

        # Late display (keep as you have)
        office_start = timezone.make_aware(datetime.combine(date.today(), time(10, 15)), tz)
        if dt_login > office_start:
            late_seconds = int((dt_login - office_start).total_seconds())
            h = late_seconds // 3600
            m = (late_seconds % 3600) // 60
            s = late_seconds % 60
            late_display = f"{h:02d}:{m:02d}:{s:02d}"
        status = "Present"

        # ✅ Calculate total break seconds from break sessions
        total_break = timedelta()
        sessions = attendance.break_sessions.all()

        for bs in sessions:
            if bs.end_at:
                total_break += bs.duration
            else:
                # ongoing break
                total_break += (timezone.now() - bs.start_at)

        break_seconds = int(total_break.total_seconds())

        # ✅ Gross working seconds since login
        gross_seconds = max(0, int((now - dt_login).total_seconds()))

        # ✅ NET work = gross - break
        working_seconds = max(0, gross_seconds - break_seconds)

        # keep DB fields updated (optional but good)
        attendance.break_time = total_break
        attendance.net_working_hours = timedelta(seconds=working_seconds)
        attendance.total_hours = timedelta(seconds=gross_seconds)
        attendance.status = "Present"
        attendance.save(update_fields=["break_time", "net_working_hours", "total_hours", "status"])

        is_on_break = attendance.is_on_break

    return render(request, 'dashboard.html', {
        'employee': employee,
        'attendance': attendance,
        'tasks': tasks,
        'working_seconds': working_seconds,   # ✅ net
        'break_seconds': break_seconds,       # ✅ break
        'late_display': late_display,
        'status': status,
        'is_on_break': is_on_break,
        'target_seconds': 8 * 3600,           # ✅ 8 hours target
    })

# UPDATE TASK STATUS
@employee_login_required
def update_task_status(request, task_id):
    task = get_object_or_404(Task, id=task_id, employee__id=request.session['employee_id'])
    task.is_completed = True
    task.save()
    messages.success(request, f"Task '{task.title}' marked as completed!")
    return redirect('employee_dashboard')


# ASSIGN TASK VIEW
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


# EMPLOYEE LOGOUT
@employee_login_required
def employee_logout(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    attendance = Attendance.objects.filter(employee=employee, date=date.today()).first()

    if not attendance or not attendance.login_time:
        messages.error(request, "Attendance not found for today.")
        return redirect('employee_dashboard')

    # ✅ if break running, end it automatically
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
    gross_work = dt_logout - dt_login

    # total break from sessions
    total_break = timedelta()
    for bs in attendance.break_sessions.all():
        if bs.end_at:
            total_break += bs.duration

    net_work = gross_work - total_break
    if net_work < timedelta():
        net_work = timedelta()

    # ✅ REQUIRED NET WORK = 8 hours
    if net_work < timedelta(hours=8):
        remaining = timedelta(hours=8) - net_work
        rem_sec = int(remaining.total_seconds())
        rh = rem_sec // 3600
        rm = (rem_sec % 3600) // 60
        rs = rem_sec % 60
        messages.error(request, f"You can logout after 8 hours net work. Remaining: {rh:02d}:{rm:02d}:{rs:02d}")
        return redirect('employee_dashboard')

    attendance.logout_time = dt_logout.time()
    attendance.total_hours = gross_work
    attendance.break_time = total_break
    attendance.net_working_hours = net_work
    attendance.status = "Present"
    attendance.save()

    request.session.flush()
    messages.success(request, "Logout successful. Have a great day!")
    return redirect('employee_login')

# ADD EMPLOYEE
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


# ATTENDANCE REPORT
@employee_login_required
def attendance_report(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    records = employee.attendance.all()

    for r in records:
        r.total_hours_fmt = format_td(r.total_hours)
        r.break_time_fmt = format_td(r.break_time)
        r.net_working_fmt = format_td(r.net_working_hours)

    return render(request, 'attendance_report.html', {'records': records})


# AJAX: Get roles by department
def get_roles(request):
    department_id = request.GET.get('department_id')
    roles = Role.objects.filter(department_id=department_id).values('id', 'name')
    return JsonResponse(list(roles), safe=False)



@employee_login_required
@require_POST
def start_break(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    attendance = Attendance.objects.filter(employee=employee, date=date.today()).first()

    if not attendance or not attendance.login_time:
        return JsonResponse({"ok": False, "msg": "Login first."})

    if attendance.is_on_break:
        return JsonResponse({"ok": False, "msg": "Break already started."})

    now = timezone.now()
    BreakSession.objects.create(attendance=attendance, start_at=now)
    attendance.is_on_break = True
    attendance.break_started_at = now
    attendance.save(update_fields=["is_on_break", "break_started_at"])

    return JsonResponse({"ok": True})


@employee_login_required
@require_POST
def end_break(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    attendance = Attendance.objects.filter(employee=employee, date=date.today()).first()

    if not attendance or not attendance.login_time:
        return JsonResponse({"ok": False, "msg": "Login first."})

    if not attendance.is_on_break:
        return JsonResponse({"ok": False, "msg": "Break is not running."})

    # close latest open break
    bs = attendance.break_sessions.filter(end_at__isnull=True).order_by("-start_at").first()
    if not bs:
        attendance.is_on_break = False
        attendance.break_started_at = None
        attendance.save(update_fields=["is_on_break", "break_started_at"])
        return JsonResponse({"ok": True})

    bs.close()

    attendance.is_on_break = False
    attendance.break_started_at = None
    attendance.save(update_fields=["is_on_break", "break_started_at"])

    return JsonResponse({"ok": True})