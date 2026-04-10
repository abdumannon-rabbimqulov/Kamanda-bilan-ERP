from django.urls import path
from . import views

app_name = 'salary'
urlpatterns = [
    path('', views.salary_list, name='list'),
    path('calculate/', views.calculate_monthly_salary, name='calculate'),
    path('export/<str:month>/', views.export_salary_pdf, name='export_pdf'),
]
