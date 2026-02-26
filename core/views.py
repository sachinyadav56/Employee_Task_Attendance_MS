from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta, date, time

from .models import Employee, Task, Attendance, Department
from .forms import EmployeeForm, TaskForm
from .decorators import employee_login_required


# EMPLOYEE LOGIN
def employee_login(request):
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id', '').strip()
        department = request.POST.get('department')
        role = request.POST.get('role')
        password = request.POST.get('password', '').strip()

        try:
            employee = Employee.objects.get(
                employee_id=emp_id,
                department__name=department,
                role=role,
                is_active=True
            )
        except Employee.DoesNotExist:
            messages.error(request, "Invalid Employee ID / Department / Role")
            return redirect('employee_login')

        if not employee.check_password(password):
            messages.error(request, "Invalid password")
            return redirect('employee_login')

        # LOGIN SUCCESS
        request.session['employee_id'] = employee.id
        now = timezone.localtime(timezone.now())
        login_time = now.time()

        SHIFT_START = time(10, 0)
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
@employee_login_required
def employee_dashboard(request):
    employee = Employee.objects.get(id=request.session['employee_id'])

    attendance = Attendance.objects.filter(
        employee=employee,
        date=date.today()
    ).first()

    tasks = Task.objects.filter(employee=employee).order_by('-assigned_date')

    # Live work timer calculation
    working_seconds = 0
    late_display = None

    if attendance and attendance.login_time:
        tz = timezone.get_current_timezone()
        now = timezone.localtime(timezone.now())
        dt_login = timezone.make_aware(datetime.combine(date.today(), attendance.login_time), tz)

        # Include already saved net working hours from previous breaks
        prev_work_seconds = int(attendance.net_working_hours.total_seconds()) if attendance.net_working_hours else 0

        if now > dt_login:
            working_seconds = int((now - dt_login).total_seconds()) + prev_work_seconds
        else:
            working_seconds = prev_work_seconds

        # Late calculation
        office_start = timezone.make_aware(datetime.combine(date.today(), time(10, 15)), tz)
        if dt_login > office_start:
            late_seconds = int((dt_login - office_start).total_seconds())
            late_hours = late_seconds // 3600
            late_minutes = (late_seconds % 3600) // 60
            late_display = f"{late_hours} hr {late_minutes} min" if late_hours > 0 else f"{late_minutes} min"

    return render(request, 'dashboard.html', {
        'employee': employee,
        'attendance': attendance,
        'tasks': tasks,
        'working_seconds': working_seconds,
        'late_display': late_display,
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
    return render(request, 'assign_task.html', {
        'tasks': tasks,
        'employee': employee
    })


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

    # Get current time as logout
    now = timezone.localtime(timezone.now())
    logout_time = now.time()

    tz = timezone.get_current_timezone()
    dt_login = timezone.make_aware(datetime.combine(date.today(), attendance.login_time), tz)
    dt_logout = timezone.make_aware(datetime.combine(date.today(), logout_time), tz)

    # Cap at shift end 17:00
    SHIFT_END = timezone.make_aware(datetime.combine(date.today(), time(17, 0)), tz)
    if dt_logout > SHIFT_END:
        dt_logout = SHIFT_END

    gross_work = dt_logout - dt_login

    # Get work_seconds & break_seconds from POST
    try:
        work_seconds = int(request.POST.get("work_seconds", 0))
        break_seconds = int(request.POST.get("break_seconds", 0))
    except ValueError:
        work_seconds = int((gross_work.total_seconds()))
        break_seconds = 0

    real_break = timedelta(seconds=break_seconds)
    net_work = timedelta(seconds=work_seconds)

    # Ensure net_work is at least zero
    if net_work < timedelta():
        net_work = timedelta()

    # Save attendance
    attendance.logout_time = dt_logout.time()
    attendance.total_hours = gross_work
    attendance.break_time = real_break
    attendance.net_working_hours = net_work
    attendance.status = 'Late' if attendance.late_by and attendance.late_by > timedelta() else 'Present'
    attendance.save()

    # Clear session and localStorage on frontend handled automatically
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