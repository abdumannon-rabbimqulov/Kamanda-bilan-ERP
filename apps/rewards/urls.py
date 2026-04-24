from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('shop/', views.shop_list, name='shop'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('redeem/<int:item_id>/', views.redeem_item, name='redeem'),
    path('admin-panel/', views.admin_reward_list, name='admin_list'),
    path('edit/<int:pk>/', views.edit_reward, name='edit'),
    path('delete/<int:pk>/', views.delete_reward, name='delete'),
    path('status/<int:redemption_id>/', views.update_redemption_status, name='update_status'),
]
