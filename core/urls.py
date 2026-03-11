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
    path("announcements/", views.announcement_list, name="announcement_list"),
    path("meetings/", views.meeting_list, name="meeting_list"),


    # Employee IT reports
    path("it-report/submit/", views.submit_it_report, name="submit_it_report"),
    path("my-it-reports/", views.my_it_reports, name="my_it_reports"),


    # Management panel
    path("management/dashboard/", views.management_dashboard, name="management_dashboard"),
    path("management/announcements/", views.announcement_list, name="announcement_list"),
    path("management/announcements/add/", views.add_announcement, name="add_announcement"),
    path("management/meetings/", views.meeting_list, name="meeting_list"),
    path("management/meetings/add/", views.add_meeting, name="add_meeting"),
    path("management/it-reports/", views.management_it_reports, name="management_it_reports"),
    path("management/it-reports/<int:report_id>/update/", views.update_it_report_status, name="update_it_report_status"),
]