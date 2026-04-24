from django.db import models
from apps.accounts.models import User
from apps.courses.models import Lesson

class Homework(models.Model):
    STATUS = [('submitted','Submitted'),('checked','Checked'),('returned','Returned')]
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='homeworks')
    file = models.FileField(upload_to='homeworks/', null=True, blank=True)
    github_link = models.URLField(null=True, blank=True)
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    checked_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='checked_homeworks')
    status = models.CharField(max_length=20, choices=STATUS, default='submitted')
    is_bonus_eligible = models.BooleanField(default=True)
    xp_awarded = models.IntegerField(default=0)
    coins_awarded = models.IntegerField(default=0)
