from django.db import models
from apps.accounts.models import User

class Salary(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    month = models.DateField()
    students_count = models.IntegerField()
    percent = models.IntegerField()  # 50 for teacher, 20 for assistant
    base_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
