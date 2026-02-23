from django.contrib import admin
from .models import Department, Employee, Task, Attendance


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'get_username', 'department', 'phone', 'is_active')
    list_filter = ('department', 'is_active')
    search_fields = ('employee_id', 'user__username')
    ordering = ('employee_id',)

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'is_completed', 'assigned_date')
    list_filter = ('is_completed', 'assigned_date')
    search_fields = ('title', 'employee__employee_id')
    list_editable = ('is_completed',)
    ordering = ('-assigned_date',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'date',
        'login_time',
        'logout_time',
        'status',
        'net_working_hours'
    )
    list_filter = ('status', 'date')
    search_fields = ('employee__employee_id',)
    date_hierarchy = 'date'
    readonly_fields = ('net_working_hours',)