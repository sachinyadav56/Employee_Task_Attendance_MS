from django.urls import path
from . import views

urlpatterns = [
    path('', views.employee_login, name='employee_login'),
    path('dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('logout/', views.employee_logout, name='employee_logout'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('my-tasks/', views.assign_task, name='assigned_tasks'),
    path('attendance/', views.attendance_report, name='attendance_report'),
    path('task/update/<int:task_id>/', views.update_task_status, name='update_task_status'),
    path('get-roles/', views.get_roles, name='get_roles'),
    path("break/start/", views.start_break, name="start_break"),
    path("break/end/", views.end_break, name="end_break"),
    path("admin-logout/", views.admin_logout, name="admin_logout"),
]