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
