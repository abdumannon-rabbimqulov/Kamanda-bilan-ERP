from django.urls import path
from . import views

app_name = 'chat'
urlpatterns = [
    path('', views.chat_list, name='list'),
    path('direct/<int:user_id>/', views.chat_direct, name='direct'),
    path('group/<int:group_id>/', views.chat_group, name='group'),
    path('message/<int:msg_id>/edit/', views.message_edit, name='message_edit'),
    path('message/<int:msg_id>/delete/', views.message_delete, name='message_delete'),
]
