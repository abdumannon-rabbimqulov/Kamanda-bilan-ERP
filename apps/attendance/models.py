from django.db import models
from apps.accounts.models import User
from apps.courses.models import Group

class Attendance(models.Model):
    STATUS = [('present','Present'),('absent','Absent'),('late','Late')]
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS)
    marked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='marked_attendances')
    
    class Meta:
        unique_together = ('student','group','date')
