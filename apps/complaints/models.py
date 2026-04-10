from django.db import models
from apps.accounts.models import User

class Complaint(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='open',
                              choices=[('open','Open'),('resolved','Resolved')])
