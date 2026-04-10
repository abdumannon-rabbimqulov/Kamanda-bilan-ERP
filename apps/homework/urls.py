from django.urls import path
from . import views

app_name = 'homework'
urlpatterns = [
    path('group/<int:group_id>/', views.homework_list, name='list'),
    path('<int:lesson_id>/submit/', views.submit_homework, name='submit'),
    path('<int:hw_id>/grade/', views.grade_homework, name='grade'),
]
