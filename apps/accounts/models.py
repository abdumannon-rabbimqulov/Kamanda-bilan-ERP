from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLES = [('student','Student'),('teacher','Teacher'),
             ('assistant','Assistant'),('admin','Admin')]
    role = models.CharField(max_length=20, choices=ROLES)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    bio = models.TextField(blank=True)
    xp = models.IntegerField(default=0)
    coins = models.IntegerField(default=0)
    level = models.IntegerField(default=0)

    def add_xp(self, amount):
        self.xp += int(amount)
        # Har 250 XP da yangi bosqich
        new_level = self.xp // 250
        if new_level > 10:
            new_level = 10
            
        if new_level > self.level:
            # Bosqich ko'tarildi - mukofotlarni beramiz
            for lv in range(self.level + 1, new_level + 1):
                # 1-bosqich: 70 coin, keyingilari +30 dan, max 220
                coin_reward = 70 + (lv - 1) * 30
                if coin_reward > 220:
                    coin_reward = 220
                self.coins += coin_reward
            self.level = new_level
        self.save()

    @property
    def level_progress(self):
        if self.level >= 10: return 100
        return ((self.xp % 250) / 250) * 100

class OTPCode(models.Model):
    PURPOSES = [('register','Register'),('reset','Password Reset')]
    email = models.EmailField()
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    def is_expired(self):
        return (timezone.now() - self.created_at).seconds > 600
