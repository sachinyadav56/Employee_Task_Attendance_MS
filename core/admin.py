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

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'login_time', 'logout_time', 'status')