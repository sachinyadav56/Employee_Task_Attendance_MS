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
        emp_id = request.POST.get('employee_id').strip()
        department = request.POST.get('department')
        role = request.POST.get('role') 
        password = request.POST.get('password').strip()

        try:
            employee = Employee.objects.get(
                employee_id=emp_id,
                department__name=department,
                role=role,
                is_active=True
            )
        except Employee.DoesNotExist:
            messages.error(request, "Invalid Credentials: ID, Department, or Role mismatch.")
            return redirect('employee_login')

        if not employee.check_password(password):
            messages.error(request, "Invalid password")
            return redirect('employee_login')

        request.session['employee_id'] = employee.id

        # Create Attendance Record immediately upon login
        Attendance.objects.get_or_create(
            employee=employee,
            date=date.today(),
            defaults={
                'login_time': timezone.localtime(timezone.now()).time(),
                'status': 'Present'
            }
        )
        return redirect('employee_dashboard')

    departments = Department.objects.all()
    return render(request, 'login.html', {'departments': departments})



# EMPLOYEE DASHBOARD ✅ FIXED

@employee_login_required
def employee_dashboard(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    
    # FIX: Fetch today's attendance so it shows on the dashboard
    attendance = Attendance.objects.filter(
        employee=employee, 
        date=date.today()
    ).first()

    # Fetch tasks for the dashboard list
    tasks = Task.objects.filter(employee=employee).order_by('-assigned_date')

    return render(request, 'dashboard.html', {
        'employee': employee,
        'tasks': tasks,
        'attendance': attendance  # Added this
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


# =========================
# EMPLOYEE LOGOUT
# =========================
@employee_login_required
def employee_logout(request):
    employee = Employee.objects.get(id=request.session['employee_id'])

    attendance = Attendance.objects.filter(
        employee=employee,
        date=date.today()
    ).first()

    if attendance and not attendance.logout_time:
        now = timezone.localtime(timezone.now())
        attendance.logout_time = now.time()

        login_dt = datetime.combine(attendance.date, attendance.login_time)
        logout_dt = datetime.combine(attendance.date, attendance.logout_time)

        total = logout_dt - login_dt

        break_time = timedelta()
        if total >= timedelta(hours=5):
            break_time = timedelta(hours=1)

        net_hours = total - break_time
        if net_hours < timedelta():
            net_hours = timedelta()

        attendance.total_hours = str(total).split('.')[0] # Format as string
        attendance.break_time = str(break_time).split('.')[0]
        attendance.net_working_hours = str(net_hours).split('.')[0]
        attendance.status = 'Present'
        attendance.save()

    request.session.flush()
    return redirect('employee_login')

# =========================
# ADD EMPLOYEE (ADMIN / MANAGER)
# =========================
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

# =========================
# ATTENDANCE REPORT
# =========================
@employee_login_required
def attendance_report(request):
    employee = Employee.objects.get(id=request.session['employee_id'])
    records = employee.attendance.all()

    return render(request, 'attendance_report.html', {'records': records})


