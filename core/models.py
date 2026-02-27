from django.db import models
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password

ROLE_CHOICES = (
    ('ADMIN', 'Admin'),
    ('MANAGER', 'Manager'),
    ('EMPLOYEE', 'Employee'),
)

# Department Model

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

# Role Model (Department-wise)

class Role(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='roles')

    def __str__(self):
        return f"{self.name} ({self.department.name})"



# Employee Model

class Employee(models.Model):
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    # new field
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True)

    phone = models.CharField(max_length=20)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    # set password using phone number
    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    # check password
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.employee_id


# Task Model

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


# Attendance Model

class Attendance(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendance'
    )
    date = models.DateField()
    login_time = models.TimeField(null=True, blank=True)
    logout_time = models.TimeField(null=True, blank=True)

    # Time calculations
    total_hours = models.DurationField(null=True, blank=True)
    break_time = models.DurationField(default=timedelta())
    net_working_hours = models.DurationField(null=True, blank=True)

    # Late calculation
    late_by = models.DurationField(null=True, blank=True)

    # ✅ Track fixed breaks (so they are added only once)
    break1_added = models.BooleanField(default=False)  # 11:15 – 11:30
    break2_added = models.BooleanField(default=False)  # 1:00 – 1:30
    break3_added = models.BooleanField(default=False)  # 4:15 – 4:30

    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Late', 'Late'),
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