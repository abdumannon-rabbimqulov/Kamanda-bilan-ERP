from django.urls import path
from . import views

app_name = 'certificates'
urlpatterns = [
    path('issue/', views.issue_certificate, name='issue'),
    path('verify/<str:code>/', views.verify_certificate, name='verify'),
]
