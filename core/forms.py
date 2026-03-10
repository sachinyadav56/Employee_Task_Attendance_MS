from django import forms
from django.contrib.auth.models import User
from .models import (
    Employee, Task, Department,
    Announcement, Meeting, ITReport
)


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'password', 'first_name', 'last_name', 'email']


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['employee_id', 'department', 'role', 'phone', 'is_active']


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['employee', 'title', 'description']


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name']


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'message', 'priority', 'department', 'is_for_all', 'expiry_date', 'is_active']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }


class MeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = [
            'title', 'agenda', 'date', 'start_time', 'end_time',
            'mode', 'meeting_link', 'location', 'department', 'participants', 'status'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'participants': forms.SelectMultiple(attrs={'size': 8}),
        }


class ITReportForm(forms.ModelForm):
    class Meta:
        model = ITReport
        fields = ['title', 'issue_type', 'description', 'priority']