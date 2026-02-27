from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta, date, time

from .models import Employee, Task, Attendance, Department, Role
from .forms import EmployeeForm, TaskForm
from .decorators import employee_login_required
from django.http import JsonResponse


# EMPLOYEE LOGIN
def employee_login(request):
    # AJAX: fetch roles by department
    if request.method == 'GET' and request.GET.get('dept_id'):
        dept_id = request.GET.get('dept_id')
        roles = Role.objects.filter(department_id=dept_id).values('id', 'name')
        return JsonResponse(list(roles), safe=False)

    if request.method == 'POST':
        emp_id = request.POST.get('employee_id', '').strip()
        department_id = request.POST.get('department')
        # role_id = request.POST.get('role')
        password = request.POST.get('password', '').strip()

        try:
            employee = Employee.objects.get(
                employee_id=emp_id,
                department_id=department_id,
                # role_id=role_id,
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

        if login_time <= GRACE_TIME:
            status = 'Present'
            late_by = timedelta()
        else:
            status = 'Late'
            dt_login = datetime.combine(date.today(), login_time)
            dt_grace = datetime.combine(date.today(), GRACE_TIME)
            late_by = dt_login - dt_grace

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
    return render(request, 'login.html', {'departments': departments})


# EMPLOYEE DASHBOARD
# EMPLOYEE DASHBOARD (FIXED LIVE TIMER)
@employee_login_required
def employee_dashboard(request):
    employee = Employee.objects.get(id=request.session['employee_id'])

    attendance = Attendance.objects.filter(
        employee=employee,
        date=date.today()
    ).first()

    tasks = Task.objects.filter(employee=employee).order_by('-assigned_date')

    working_seconds = 0
    break_seconds = 0
    late_display = None
    status = "Present"

    if attendance and attendance.login_time:
        tz = timezone.get_current_timezone()
        now = timezone.localtime(timezone.now())
        dt_login = timezone.make_aware(datetime.combine(date.today(), attendance.login_time), tz)

        # Late logic
        office_start = timezone.make_aware(datetime.combine(date.today(), time(10, 15)), tz)
        if dt_login > office_start:
            late_seconds = int((dt_login - office_start).total_seconds())
            late_display = f"{late_seconds // 60} min"
            status = "Late"
        else:
            status = "Present"

        # 🔹 Fixed breaks (add AFTER break end)
        breaks = [
            ("break1_added", time(11, 30), 15 * 60),
            ("break2_added", time(13, 30), 30 * 60),
            ("break3_added", time(16, 30), 15 * 60),
        ]

        total_break_seconds = int(attendance.break_time.total_seconds()) if attendance.break_time else 0

        for flag, break_end, sec in breaks:
            break_end_dt = timezone.make_aware(datetime.combine(date.today(), break_end), tz)
            if now >= break_end_dt and not getattr(attendance, flag):
                total_break_seconds += sec
                setattr(attendance, flag, True)

        attendance.break_time = timedelta(seconds=total_break_seconds)
        attendance.save(update_fields=["break_time", "break1_added", "break2_added", "break3_added"])

        break_seconds = total_break_seconds

        # 🔹 Live working time (continuous)
        if now > dt_login:
            working_seconds = int((now - dt_login).total_seconds())
        else:
            working_seconds = 0

    return render(request, 'dashboard.html', {
        'employee': employee,
        'attendance': attendance,
        'tasks': tasks,
        'working_seconds': working_seconds,
        'break_seconds': break_seconds,
        'late_display': late_display,
        'status': status
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

    now = timezone.localtime(timezone.now())
    logout_time = now.time()

    tz = timezone.get_current_timezone()
    dt_login = timezone.make_aware(datetime.combine(date.today(), attendance.login_time), tz)
    dt_logout = timezone.make_aware(datetime.combine(date.today(), logout_time), tz)

    gross_work = dt_logout - dt_login

    try:
        work_seconds = int(request.POST.get("work_seconds", 0))
        break_seconds = int(request.POST.get("break_seconds", 0))
    except:
        work_seconds = int(gross_work.total_seconds())
        break_seconds = 0

    real_break = timedelta(seconds=break_seconds)
    net_work = timedelta(seconds=work_seconds)

    if net_work < timedelta():
        net_work = timedelta()

    attendance.logout_time = dt_logout.time()
    attendance.total_hours = gross_work
    attendance.break_time = real_break
    attendance.net_working_hours = net_work
    attendance.status = 'Late' if attendance.late_by and attendance.late_by > timedelta() else 'Present'
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