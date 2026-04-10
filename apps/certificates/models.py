from django.db import models
import uuid
from apps.accounts.models import User
from apps.courses.models import Course

class Certificate(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='certificates/')
    qr_code = models.ImageField(upload_to='qr_codes/')
    verification_code = models.UUIDField(default=uuid.uuid4, unique=True)
