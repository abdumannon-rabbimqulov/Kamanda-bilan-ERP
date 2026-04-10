from django.urls import path
from . import views

app_name = 'exams'
urlpatterns = [
    path('<int:group_id>/', views.exam_list, name='list'),
    path('<int:group_id>/add/', views.add_exam, name='add'),
    path('<int:exam_id>/results/', views.post_results, name='post_results'),
]
