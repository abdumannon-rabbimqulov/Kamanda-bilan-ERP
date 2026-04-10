from django.db import models
from apps.accounts.models import User
from apps.courses.models import Group

class Exam(models.Model):
    TYPES = [('weekly','Haftalik'),('monthly','Oylik'),('final','Final')]
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    exam_type = models.CharField(max_length=10, choices=TYPES)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    max_score = models.IntegerField(default=100)

class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField()
    feedback = models.TextField(blank=True)
