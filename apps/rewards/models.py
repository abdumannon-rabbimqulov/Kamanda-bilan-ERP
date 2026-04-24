from django.db import models
from apps.accounts.models import User

class RewardItem(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='rewards/')
    coin_price = models.IntegerField(default=0)
    stock_quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Redemption(models.Model):
    STATUS = [
        ('pending', 'Kutilmoqda'),
        ('delivered', 'Yetkazildi'),
        ('cancelled', 'Bekor qilindi')
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='redemptions')
    item = models.ForeignKey(RewardItem, on_delete=models.CASCADE)
    coins_spent = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.item.name}"
