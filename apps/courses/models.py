from django.db import models
from apps.accounts.models import User

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    thumbnail = models.ImageField(upload_to='courses/')
    teacher = models.ForeignKey(User, on_delete=models.PROTECT, related_name='courses')
    category = models.CharField(max_length=100)
    success_rate = models.FloatField(default=0)
    students_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Group(models.Model):
    SCHEDULE_TYPES = [
        ('3_days_toq','Haftada 3 kun (Toq kunlar)'),
        ('3_days_juft','Haftada 3 kun (Juft kunlar)'),
        ('5_days','Haftada 5 kun'),
        ('daily','Har kuni')
    ]
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    teacher = models.ForeignKey(User, on_delete=models.PROTECT, related_name='groups_taught')
    assistant = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='groups_assisted')
    max_students = models.IntegerField(default=20)
    start_date = models.DateField()
    end_date = models.DateField()
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPES, default='3_days_toq')
    lesson_start_time = models.TimeField(default="10:00")
    lesson_end_time = models.TimeField(default="11:30")
    is_active = models.BooleanField(default=True)
    teacher_percent = models.IntegerField(default=40)
    assistant_percent = models.IntegerField(default=15)

class Enrollment(models.Model):
    STATUS = [('pending','Pending'),('approved','Approved'),('rejected','Rejected')]
    student = models.ForeignKey(User, on_delete=models.PROTECT)
    group = models.ForeignKey(Group, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_enrollments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def remaining_debt(self):
        return self.group.course.price - self.amount_paid

    @property
    def remaining_debt_abs(self):
        return abs(self.remaining_debt)

    @property
    def balance_status(self):

        debt = self.remaining_debt
        if debt > 0: return 'debt'
        if debt < 0: return 'excess'
        return 'paid'


class Lesson(models.Model):
    TYPES = [('video','Video'),('pdf','PDF'),('text','Matn')]
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    lesson_type = models.CharField(max_length=10, choices=TYPES, default='text')
    file = models.FileField(upload_to='lessons/', blank=True, null=True)
    content = models.TextField(blank=True)
    date = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
