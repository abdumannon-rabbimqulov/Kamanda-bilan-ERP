from django.db import models
from apps.courses.models import Enrollment

class Payment(models.Model):
    STATUS = [('pending','Pending'),('success','Success'),('failed','Failed')]
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=10, choices=STATUS, default='pending')
