from django.urls import path
from . import views

app_name = 'exams'
urlpatterns = [
    path('<int:group_id>/', views.exam_list, name='list'),
    path('add/', views.add_exam, name='add_exam'),
    path('<int:exam_id>/results/', views.post_results, name='results'),
]
