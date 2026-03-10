from django.shortcuts import redirect
from django.contrib import messages
from .models import Employee


def employee_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('employee_id'):
            return redirect('employee_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_required(view_func):
    def wrapper(request, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return redirect('employee_login')

        employee = Employee.objects.filter(id=employee_id, is_active=True).first()
        if not employee or not employee.is_manager():
            messages.error(request, "Management access only.")
            return redirect('employee_dashboard')

        return view_func(request, *args, **kwargs)
    return wrapper