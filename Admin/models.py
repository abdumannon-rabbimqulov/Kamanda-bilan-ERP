from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('assistant', 'Assistant'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    is_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)

class Course(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Group(models.Model):
    name = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='teaching_groups')
    assistant = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='assisting_groups')
    students = models.ManyToManyField(CustomUser, related_name='enrolled_groups', blank=True)

    def __str__(self):
        return f"{self.name} - {self.course.name}"

class Lesson(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

class Homework(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    file_or_text = models.TextField()
    grade = models.IntegerField(null=True, blank=True)
    is_checked = models.BooleanField(default=False)

class Attendance(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    is_present = models.BooleanField(default=False)

class Payment(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False)
    
    @property
    def teacher_salary(self):
        return float(self.amount) * 0.50

    @property
    def assistant_salary(self):
        return float(self.amount) * 0.20