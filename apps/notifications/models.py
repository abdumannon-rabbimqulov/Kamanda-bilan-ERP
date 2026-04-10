from django.db import models
from apps.accounts.models import User

class Notification(models.Model):
    TYPES = [('lesson_added','Lesson'),('test_started','Test'),
             ('payment_reminder','Payment'),('announcement','Announcement')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    body = models.TextField()
    notif_type = models.CharField(max_length=30, choices=TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
