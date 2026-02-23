from django import forms
from django.contrib.auth.models import User
from .models import Employee, Task, Department


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'password', 'first_name', 'last_name', 'email']


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['employee_id', 'department', 'phone']


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['employee', 'title', 'description']


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name']