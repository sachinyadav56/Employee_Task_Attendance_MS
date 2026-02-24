from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta, time, date

from .models import Employee, Task, Attendance, Department
from .forms import UserForm, EmployeeForm, TaskForm


def login_view(request):
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        dept_name = request.POST.get('department')
        role = request.POST.get('role')
        password = request.POST.get('password')

        try:
            department = Department.objects.get(name=dept_name)
            employee = Employee.objects.get( employee_id=emp_id,department=department,  role=role, is_active=True)
        except (Department.DoesNotExist, Employee.DoesNotExist):
            messages.error(request, "Invalid login details")
            return render(request, 'login.html')

        user = authenticate(request, username=employee.user.username, password=password)

        if user:
            login(request, user)

            Attendance.objects.get_or_create(
                employee=employee,
                date=date.today(),
                defaults={
                    'login_time': timezone.localtime(timezone.now()).time(),
                    'status': 'Present'
                }
            )
            return redirect('dashboard')

        messages.error(request, "Invalid password")

    departments = Department.objects.all()
    roles = Employee.ROLE_CHOICES
    return render(request, 'login.html', {'departments': departments,'roles': roles })

@login_required
def dashboard(request):
    employee = request.user.employee
    tasks = employee.tasks.all()
    attendance = employee.attendance.filter(date=date.today()).first()

    return render(request, 'dashboard.html', {
        'employee': employee,
        'tasks': tasks,
        'attendance': attendance
    })


@login_required
def logout_view(request):
    employee = request.user.employee
    attendance = Attendance.objects.filter(
        employee=employee,
        date=date.today()
    ).first()

    if attendance and not attendance.logout_time:
        now = timezone.localtime(timezone.now())
        attendance.logout_time = now.time()

        login_dt = datetime.combine(
            attendance.date,
            attendance.login_time
        )
        logout_dt = datetime.combine(
            attendance.date,
            attendance.logout_time
        )

        total = logout_dt - login_dt

        # ✅ Company rule: fixed break only if work >= 5 hours
        break_time = timedelta()
        if total >= timedelta(hours=5):
            break_time = timedelta(hours=1)

        net_hours = total - break_time
        if net_hours < timedelta():
            net_hours = timedelta()

        attendance.total_hours = total
        attendance.break_time = break_time
        attendance.net_working_hours = net_hours
        attendance.status = 'Present'
        attendance.save()

    logout(request)
    return redirect('login')


@login_required
def add_employee(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        emp_form = EmployeeForm(request.POST)

        if user_form.is_valid() and emp_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()

            employee = emp_form.save(commit=False)
            employee.user = user
            employee.save()

            messages.success(request, "Employee added successfully")
            return redirect('dashboard')
    else:
        user_form = UserForm()
        emp_form = EmployeeForm()

    return render(request, 'add_employee.html', {
        'user_form': user_form,
        'emp_form': emp_form
    })


@login_required
def assign_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Task assigned successfully")
            return redirect('dashboard')
    else:
        form = TaskForm()

    return render(request, 'assign_task.html', {'form': form})

@login_required
def attendance_report(request):
    employee = request.user.employee
    records = employee.attendance.all()
    return render(request, 'attendance_report.html', {'records': records})