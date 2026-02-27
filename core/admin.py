from django.contrib import admin
from django.contrib.auth.hashers import make_password
from .models import Department, Employee, Task, Attendance

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Using 'department' (the field name) shows the __str__ value (the Name)
    list_display = ('employee_id', 'department', 'role', 'phone', 'is_active')
    list_filter = ('department', 'role', 'is_active')
    search_fields = ('employee_id', 'phone')

    def save_model(self, request, obj, form, change):
        # Automatically hash the password if it's saved as plain text
        if obj.password and not obj.password.startswith('pbkdf2_sha256$'):
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'is_completed', 'assigned_date')

from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import localtime
from .models import Department, Employee, Task, Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = (
        'employee_id',
        'date',
        'formatted_login',
        'formatted_logout',
        'colored_status',
        'formatted_late',
        'formatted_break',
        'formatted_net_work',
    )

    list_filter = ('status', 'date', 'employee')
    search_fields = ('employee__employee_id',)
    date_hierarchy = 'date'
    ordering = ('-date',)

    # -----------------------------
    # CUSTOM COLUMNS
    # -----------------------------

    def employee_id(self, obj):
        return obj.employee.employee_id
    employee_id.short_description = "Employee ID"

    def formatted_login(self, obj):
        if obj.login_time:
            return obj.login_time.strftime("%I:%M %p")
        return "-"
    formatted_login.short_description = "Login"

    def formatted_logout(self, obj):
        if obj.logout_time:
            return obj.logout_time.strftime("%I:%M %p")
        return "-"
    formatted_logout.short_description = "Logout"

    def colored_status(self, obj):
        color = "green" if obj.status == "Present" else "red"
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color,
            obj.status
        )
    colored_status.short_description = "Status"

    def formatted_late(self, obj):
        if obj.late_by:
            total_seconds = int(obj.late_by.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"
    formatted_late.short_description = "Late By"

    def formatted_break(self, obj):
        if obj.break_time:
            total_seconds = int(obj.break_time.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"
    formatted_break.short_description = "Break Time"

    def formatted_net_work(self, obj):
        if obj.net_working_hours:
            total_seconds = int(obj.net_working_hours.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"
    formatted_net_work.short_description = "Net Working"