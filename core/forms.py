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
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter announcement title'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write announcement details'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_for_all': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class MeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = [
            'title', 'agenda', 'date', 'start_time', 'end_time',
            'mode', 'meeting_link', 'location', 'department', 'participants', 'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'agenda': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'mode': forms.Select(attrs={'class': 'form-select'}),
            'meeting_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://meet.google.com/...'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Conference Room / Office'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'participants': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 8}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class ITReportForm(forms.ModelForm):
    class Meta:
        model = ITReport
        fields = ['title', 'issue_type', 'description', 'priority']