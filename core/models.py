from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Employee(models.Model):

    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('MANAGER', 'Manager'),
        ('EMPLOYEE', 'Employee'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee_id} - {self.user.username} ({self.role})"

# class Employee(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     employee_id = models.CharField(max_length=20, unique=True)
#     department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
#     phone = models.CharField(max_length=20)
#     is_active = models.BooleanField(default=True)

#     def __str__(self):
#         return f"{self.employee_id} - {self.user.username}"


class Task(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField()
    is_completed = models.BooleanField(default=False)
    assigned_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.title


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField(auto_now_add=True)
    login_time = models.TimeField(null=True, blank=True)
    logout_time = models.TimeField(null=True, blank=True)
    total_hours = models.DurationField(null=True, blank=True)
    break_time = models.DurationField(default=timedelta(minutes=0))
    net_working_hours = models.DurationField(null=True, blank=True)

    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent')
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Absent')

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.date}"