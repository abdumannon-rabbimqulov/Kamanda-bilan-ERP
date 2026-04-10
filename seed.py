import os
import django
import random
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User
from apps.courses.models import Course, Group, Enrollment
from apps.payments.models import Payment
from apps.salary.models import Salary
from apps.chat.models import Message

print("Tozalash boshlandi...")
# Keep admin, delete others
User.objects.exclude(role='admin').delete()
Course.objects.all().delete()
Group.objects.all().delete()
Enrollment.objects.all().delete()
Payment.objects.all().delete()
Salary.objects.all().delete()
Message.objects.all().delete()
print("Tozalash tugadi!")

print("Yangi ma'lumotlar qo'shilmoqda...")

# Create 5 Teachers
teachers = []
for i in range(1, 6):
    u = User.objects.create_user(
        username=f"teacher{i}@lms.uz",
        email=f"teacher{i}@lms.uz",
        password="1",
        first_name=f"Ustoz-{i}",
        last_name="IT",
        role="teacher",
        is_active=True
    )
    teachers.append(u)

# Create 5 Assistants
assistants = []
for i in range(1, 6):
    u = User.objects.create_user(
        username=f"assistant{i}@lms.uz",
        email=f"assistant{i}@lms.uz",
        password="1",
        first_name=f"Yordamchi-{i}",
        last_name="IT",
        role="assistant",
        is_active=True
    )
    assistants.append(u)

# Create 30 Students
students = []
for i in range(1, 31):
    u = User.objects.create_user(
        username=f"student{i}@lms.uz",
        email=f"student{i}@lms.uz",
        password="1",
        first_name=f"O'quvchi-{i}",
        last_name="Test",
        role="student",
        is_active=True
    )
    students.append(u)

# Create 10 IT Courses
course_names = ["Python Dasturlash", "Frontend React", "Backend Node.js", "Java Spring", "Go Microservices", "Data Science", "C# .NET", "Flutter Mobile", "Android Kotlin", "Swift iOS"]
courses = []
for idx, name in enumerate(course_names):
    c = Course.objects.create(
        title=name,
        description=f"{name} sohasi bo'yicha kuchli mutaxassis bo'ling.",
        duration_months=random.randint(3, 8),
        price=Decimal(str(random.choice([400000, 500000, 600000, 800000, 1000000]))),
        is_active=True
    )
    courses.append(c)

# Create Groups for courses
groups = []
start_date = timezone.now().date()
end_date = start_date + timedelta(days=90)

for idx, c in enumerate(courses):
    t = random.choice(teachers)
    a = random.choice(assistants)
    g = Group.objects.create(
        name=f"Guruh {c.title[:3]}-{idx+1}",
        course=c,
        teacher=t,
        assistant=a,
        start_date=start_date,
        end_date=end_date,
        teacher_percent=40,
        assistant_percent=10,
        schedule_type=random.choice(['3_days', '5_days', 'daily']),
        lesson_start_time='14:00'
    )
    groups.append(g)

# 30 Students Enroll in Random Groups
# Hamma qarz (amount_paid=0)
for idx, s in enumerate(students):
    # each student gets 1 or 2 groups
    selected_groups = random.sample(groups, random.randint(1, 2))
    for g in selected_groups:
        Enrollment.objects.create(
            student=s,
            group=g,
            status='approved',
            enrolled_at=timezone.now(),
            amount_paid=Decimal('0') # NO PAYMENTS
        )

print("Ma'lumotlar bazasi to'liq yangilandi! Center Balance = 0, Hamma qarzdor!")
