from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('assign-task/', views.assign_task, name='assign_task'),
    path('attendance-report/', views.attendance_report, name='attendance_report'),
]