from django.db import models
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

ROLE_CHOICES = (
    ('ADMIN', 'Admin'),
    ('MANAGER', 'Manager'),
    ('EMPLOYEE', 'Employee'),
)

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='roles')

    def __str__(self):
        return self.name


class Employee(models.Model):
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True)

    phone = models.CharField(max_length=20)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def is_manager(self):
        return self.role and self.role.name.strip().lower() == "manager"

    def __str__(self):
        return self.employee_id


class Task(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    is_completed = models.BooleanField(default=False)
    assigned_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.title


class Attendance(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendance'
    )
    date = models.DateField()
    login_time = models.TimeField(null=True, blank=True)
    logout_time = models.TimeField(null=True, blank=True)

    total_hours = models.DurationField(null=True, blank=True)
    break_time = models.DurationField(default=timedelta())
    net_working_hours = models.DurationField(null=True, blank=True)
    late_by = models.DurationField(null=True, blank=True)

    break1_added = models.BooleanField(default=False)
    break2_added = models.BooleanField(default=False)
    break3_added = models.BooleanField(default=False)

    is_on_break = models.BooleanField(default=False)
    break_started_at = models.DateTimeField(null=True, blank=True)

    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='Absent'
    )

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.date}"


class BreakSession(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name="break_sessions")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(default=timedelta())

    class Meta:
        ordering = ["-start_at"]

    def close(self):
        if self.end_at is None:
            self.end_at = timezone.now()
        if self.end_at < self.start_at:
            self.end_at = self.start_at
        self.duration = self.end_at - self.start_at
        self.save(update_fields=["end_at", "duration"])

    def __str__(self):
        return f"Break({self.attendance_id}) {self.start_at} - {self.end_at}"


# -----------------------------
# NEW: ANNOUNCEMENT
# -----------------------------
class Announcement(models.Model):
    PRIORITY_CHOICES = [
        ("Normal", "Normal"),
        ("Important", "Important"),
        ("Urgent", "Urgent"),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Normal")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    is_for_all = models.BooleanField(default=True)
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_announcements")
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# -----------------------------
# NEW: MEETING
# -----------------------------
class Meeting(models.Model):
    MODE_CHOICES = [
        ("Online", "Online"),
        ("Offline", "Offline"),
    ]

    STATUS_CHOICES = [
        ("Scheduled", "Scheduled"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=200)
    agenda = models.TextField()
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="Offline")
    meeting_link = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    participants = models.ManyToManyField(Employee, blank=True, related_name="meetings")
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_meetings")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Scheduled")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.title} - {self.date}"


# -----------------------------
# NEW: IT REPORT / TICKET
# -----------------------------
class ITReport(models.Model):
    ISSUE_TYPE_CHOICES = [
        ("Software", "Software"),
        ("Hardware", "Hardware"),
        ("Login", "Login"),
        ("Network", "Network"),
        ("Other", "Other"),
    ]

    PRIORITY_CHOICES = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
    ]

    STATUS_CHOICES = [
        ("Open", "Open"),
        ("In Progress", "In Progress"),
        ("Resolved", "Resolved"),
        ("Closed", "Closed"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="it_reports")
    title = models.CharField(max_length=200)
    issue_type = models.CharField(max_length=50, choices=ISSUE_TYPE_CHOICES)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Open")
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_it_reports")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.employee.employee_id}"