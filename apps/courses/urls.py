from django.urls import path
from . import views

app_name = 'courses'
urlpatterns = [
    path('', views.course_list, name='list'),
    path('<int:course_id>/', views.course_detail, name='detail'),
    path('<int:course_id>/enroll/', views.enroll_course, name='enroll'),
    path('<int:group_id>/lessons/', views.lesson_list, name='lesson_list'),
    path('<int:group_id>/lessons/add/', views.add_lesson, name='add_lesson'),
    path('lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('lesson/<int:lesson_id>/start/', views.start_lesson, name='start_lesson'),
]
