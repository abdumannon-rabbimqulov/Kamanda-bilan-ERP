from django.urls import path
from . import views

app_name = 'payments'
urlpatterns = [
    path('', views.payments_dashboard, name='dashboard'),
    path('record/', views.record_student_payment, name='record'),
    path('send-salary/', views.send_salary_payment, name='send_salary'),
    path('notify-debtors/', views.notify_debtors, name='notify_debtors'),
    path('student/pay/', views.student_make_payment, name='student_pay'),
]