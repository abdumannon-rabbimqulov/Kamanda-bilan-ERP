from django.urls import path
from . import views

app_name = 'attendance'
urlpatterns = [
    path('<int:group_id>/', views.attendance_list, name='list'),
    path('<int:group_id>/mark/', views.mark_attendance, name='mark'),
]
