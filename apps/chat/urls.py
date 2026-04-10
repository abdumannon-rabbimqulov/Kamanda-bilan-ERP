from django.urls import path
from . import views

app_name = 'chat'
urlpatterns = [
    path('', views.chat_list, name='index'),
    path('user/<int:user_id>/', views.chat_direct, name='direct'),
    path('group/<int:group_id>/', views.chat_group, name='group'),
]
