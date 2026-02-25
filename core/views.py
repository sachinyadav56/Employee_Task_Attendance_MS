from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta, date

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

        # ---------- AUTHENTICATION ----------
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

        # ---------- LOGIN SUCCESS ----------
        request.session['employee_id'] = employee.id

        now = timezone.localtime(timezone.now())
        login_time = now.time()

        # ---------- COMPANY RULES ----------
        SHIFT_START = time(10, 0)
        GRACE_TIME = time(10, 15)

        # ---------- STATUS & LATE CALCULATION ----------
        if login_time <= GRACE_TIME:
            status = 'Present'
            late_by = timedelta()
        else:
            status = 'Late'
            dt_login = datetime.combine(date.today(), login_time)
            dt_grace = datetime.combine(date.today(), GRACE_TIME)
            late_by = dt_login - dt_grace

        # ---------- ATTENDANCE ----------
        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=date.today(),
            defaults={
                'login_time': login_time,
                'status': status,
                'late_by': late_by
            }
        )

        # Safety update if record already exists
        if not created and not attendance.login_time:
            attendance.login_time = login_time
            attendance.status = status
            attendance.late_by = late_by
            attendance.save()

        messages.success(request, "Login successful")
        return redirect('employee_dashboard')

    # ---------- GET REQUEST ----------
    departments = Department.objects.all()
    return render(request, 'login.html', {'departments': departments})



# EMPLOYEE DASHBOARD FIXED

@employee_login_required
def employee_dashboard(request):
    employee = Employee.objects.get(id=request.session['employee_id'])

    # Fetch today's attendance
    attendance = Attendance.objects.filter(
        employee=employee,
        date=date.today()
    ).first()

    # Fetch tasks
    tasks = Task.objects.filter(
        employee=employee
    ).order_by('-assigned_date')

    # ---------------- LIVE WORK TIMER ----------------
    working_seconds = 0
    late_display = None

    if attendance and attendance.login_time:
        tz = timezone.get_current_timezone()

        # Current time (aware)
        now = timezone.localtime(timezone.now())

        # Login datetime (aware)
        dt_login = timezone.make_aware(
            datetime.combine(date.today(), attendance.login_time),
            tz
        )

        # Safety check
        if now > dt_login:
            working_seconds = int((now - dt_login).total_seconds())
        else:
            working_seconds = 0

        # ---------------- LATE CALCULATION ----------------
        office_start = timezone.make_aware(
            datetime.combine(date.today(), time(10, 15)),  # 10:15 AM
            tz
        )

        if dt_login > office_start:
            late_seconds = int((dt_login - office_start).total_seconds())

            late_hours = late_seconds // 3600
            late_minutes = (late_seconds % 3600) // 60

            if late_hours > 0:
                late_display = f"{late_hours} hr {late_minutes} min"
            else:
                late_display = f"{late_minutes} min"


    return render(request, 'dashboard.html', {
        'employee': employee,
        'attendance': attendance,
        'tasks': tasks,
        'working_seconds': working_seconds,
        'late_display': late_display,
    })

# UPDATE TASK STATUS ✅ NEW

@employee_login_required
def update_task_status(request, task_id):
    # Security: Ensure task belongs to the logged-in employee
    task = get_object_or_404(Task, id=task_id, employee__id=request.session['employee_id'])
    
    task.is_completed = True 
    task.save()
    
    messages.success(request, f"Task '{task.title}' marked as completed!")
    # Redirect to whichever page you want (dashboard or assign_task)
    return redirect('employee_dashboard') 



# ASSIGN TASK (VIEW ONLY)
# =========================
@employee_login_required
def assign_task(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    tasks = Task.objects.filter(employee=employee).order_by('-assigned_date')

    return render(request, 'assign_task.html', {
        'tasks': tasks,
        'employee': employee
    })




from datetime import datetime, time, date
from django.utils import timezone

def format_time_pro(seconds):
    """Formats raw seconds into clean 00h 00m 00s format"""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}h {m:02d}m {s:02d}s"

@employee_login_required
def employee_logout(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    attendance = Attendance.objects.filter(
        employee=employee,
        date=date.today()
    ).first()

    if not attendance or not attendance.login_time:
        messages.error(request, "No login record found for today.")
        return redirect('employee_dashboard')

    now = timezone.localtime(timezone.now())
    logout_time = now.time()

    # ---------------- COMPANY RULES ----------------
    SHIFT_START = time(10, 0)
    SHIFT_END = time(17, 0)

    BREAK_11_30 = timedelta(minutes=15)
    LUNCH_BREAK = timedelta(minutes=30)
    BREAK_4_30 = timedelta(minutes=15)

    TOTAL_BREAK = BREAK_11_30 + LUNCH_BREAK + BREAK_4_30  # 1 hour
    REQUIRED_WORK = timedelta(hours=8)

    # ------------------------------------------------

    # Combine date & time
    dt_login = datetime.combine(date.today(), attendance.login_time)
    dt_logout = datetime.combine(date.today(), logout_time)

    # Safety: Cap logout at 5 PM
    if logout_time > SHIFT_END:
        dt_logout = datetime.combine(date.today(), SHIFT_END)

    # Gross working time
    gross_work = dt_logout - dt_login

    # Net working time
    net_work = gross_work - TOTAL_BREAK
    if net_work < timedelta():
        net_work = timedelta()

    # ❌ BLOCK LOGOUT IF WORK < 8 HOURS
    if net_work < REQUIRED_WORK:
        remaining = REQUIRED_WORK - net_work
        messages.error(
            request,
            f"You must complete 8 working hours. Remaining: {remaining}"
        )
        return redirect('employee_dashboard')

    # ✅ SAVE ATTENDANCE
    attendance.logout_time = dt_logout.time()
    attendance.total_hours = gross_work
    attendance.break_time = TOTAL_BREAK
    attendance.net_working_hours = net_work
    attendance.status = 'Late' if attendance.late_by and attendance.late_by > timedelta() else 'Present'
    attendance.save()

    # End session
    request.session.flush()
    messages.success(request, "Logout successful. Have a great day!")

    return redirect('employee_login')

# ADD EMPLOYEE (ADMIN / MANAGER)

def add_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)

        if form.is_valid():
            employee = form.save(commit=False)

            # phone is used as password
            employee.set_password(employee.phone)
            employee.save()

            messages.success(
                request,
                "Employee added successfully. Password is phone number."
            )
            return redirect('add_employee')

    else:
        form = EmployeeForm()

    return render(request, 'add_employee.html', {'emp_form': form})


# ATTENDANCE REPORT
@employee_login_required
def attendance_report(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    records = employee.attendance.all()

    return render(request, 'attendance_report.html', {'records': records})


