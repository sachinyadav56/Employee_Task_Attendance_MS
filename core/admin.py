from django.contrib import admin
from django.contrib.auth.hashers import make_password
from django.utils.html import format_html
from django.utils import timezone
from django.contrib.admin.sites import AdminSite
from datetime import timedelta

from .models import Department, Employee, Task, Attendance, Role, BreakSession


def create_daily_absent_records():
    today = timezone.localdate()

    # Skip Saturday and Sunday
    if today.weekday() in (5, 6):
        return

    active_employees = Employee.objects.filter(is_active=True)

    for employee in active_employees:
        Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                "status": "Absent",
                "login_time": None,
                "logout_time": None,
                "late_by": timedelta(),
                "total_hours": timedelta(),
                "break_time": timedelta(),
                "net_working_hours": timedelta(),
                "is_on_break": False,
                "break_started_at": None,
            }
        )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'department')
    list_filter = ('department',)
    search_fields = ('name',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'department', 'role', 'phone', 'is_active')
    list_filter = ('department', 'role', 'is_active')
    search_fields = ('employee_id', 'phone')

    def save_model(self, request, obj, form, change):
        if obj.password and not obj.password.startswith('pbkdf2_sha256$'):
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'is_completed', 'assigned_date')


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


@admin.register(BreakSession)
class BreakSessionAdmin(admin.ModelAdmin):
    list_display = ("attendance", "start_at", "end_at", "duration")
    list_filter = ("start_at", "end_at")
    search_fields = ("attendance__employee__employee_id",)


_old_each_context = AdminSite.each_context

def _new_each_context(self, request):
    create_daily_absent_records()  # ✅ important

    ctx = _old_each_context(self, request)
    today = timezone.localdate()

    ctx["today_date"] = today.isoformat()
    ctx["card_total_employees"] = Employee.objects.filter(is_active=True).count()
    ctx["card_present_today"] = Attendance.objects.filter(date=today, status="Present").count()
    ctx["card_tasks_completed_today"] = Task.objects.filter(
        assigned_date=today,
        is_completed=True
    ).count()
    ctx["card_absent_today"] = Attendance.objects.filter(date=today, status="Absent").count()
    return ctx

AdminSite.each_context = _new_each_context
