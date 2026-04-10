from django.db import models
from apps.accounts.models import User
from apps.courses.models import Group

class Message(models.Model):
    TYPES = [('direct','Direct'),('group','Group')]
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='received_messages')
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    content = models.TextField()
    msg_type = models.CharField(max_length=10, choices=TYPES, default='direct')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
