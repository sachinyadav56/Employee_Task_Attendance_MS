from django.urls import path
from . import views

urlpatterns = [
    path('', views.employee_login, name='employee_login'),
    path('dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('logout/', views.employee_logout, name='employee_logout'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('my-tasks/', views.assign_task, name='assign_task'),
    path('attendance/', views.attendance_report, name='attendance_report'),
    path('task/update/<int:task_id>/', views.update_task_status, name='update_task_status'),
]