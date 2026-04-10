import os
import django
import random
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User
from apps.courses.models import Course, Group, Enrollment, Lesson
from apps.attendance.models import Attendance
from apps.homework.models import Homework
from apps.salary.models import Salary
from apps.payments.models import Payment
from apps.exams.models import Exam, ExamResult
from apps.complaints.models import Complaint
from apps.certificates.models import Certificate
from decimal import Decimal

def seed():
    print("Pre-cleaning database...")
    User.objects.exclude(username='admin').delete()
    Course.objects.all().delete()
    
    print("Generating users...")
    teachers = []
    for i in range(1, 6):
        u = User.objects.create_user(username=f'teacher{i}', email=f'teacher{i}@lms.uz', password='1', role='teacher')
        u.first_name = random.choice(["Ali", "Bahodir", "Jamshid", "Sardor", "Rustam"])
        u.last_name = random.choice(["Karimov", "Toshmatov", "Eshmatov", "Azizov", "Jalilov"])
        u.save()
        teachers.append(u)

    students = []
    for i in range(1, 31):
        u = User.objects.create_user(username=f'student{i}', email=f'student{i}@lms.uz', password='1', role='student')
        u.first_name = random.choice(["Hasan", "Husan", "Fozil", "Dilshod", "Alisher", "Azamat", "Zafar", "Murod", "Odil"])
        u.last_name = random.choice(["Qodirov", "Olimov", "Rahimov", "Sobirov", "Mominov", "Yusupov", "Axmedov"])
        u.save()
        students.append(u)
        
    assistants = []
    for i in range(1, 4):
        u = User.objects.create_user(username=f'assistant{i}', email=f'assistant{i}@lms.uz', password='1', role='assistant')
        u.first_name = "Yordamchi"
        u.save()
        assistants.append(u)

    print("Generating courses and groups...")
    now = timezone.now()
    two_months_ago = now - timedelta(days=60)
    
    courses_data = [
        ("Python Backend", "Professional Python", 1500000, "Dasturlash"),
        ("Frontend React", "HTML/CSS/JS", 1200000, "Dasturlash"),
        ("SMM darslari", "Marketing", 800000, "Marketing")
    ]
    
    groups = []
    for title, desc, price, cat in courses_data:
        t = random.choice(teachers)
        c = Course.objects.create(title=title, description=desc, price=price, category=cat, teacher=t)
        
        # Create a group that started 60 days ago
        g = Group.objects.create(name=f"{c.title} - G1 (Eski)", course=c, teacher=c.teacher, assistant=random.choice(assistants), max_students=15, start_date=two_months_ago.date(), end_date=(two_months_ago + timedelta(days=90)).date())
        groups.append(g)

    print("Enrolling students & generating payments...")
    import uuid
    for g in groups:
        enrolled = random.sample(students, k=10)
        for st in enrolled:
            # 60 days ago enrollment
            enroll_date = two_months_ago + timedelta(days=random.randint(0, 5))
            enr = Enrollment.objects.create(student=st, group=g, status='approved', amount_paid=Decimal(str(random.randint(500, int(g.course.price)))))
            # Add a payment
            p = Payment.objects.create(enrollment=enr, amount=Decimal(str(g.course.price / 2)), method='card', transaction_id=str(uuid.uuid4())[:20], status='success')
            Payment.objects.filter(id=p.id).update(paid_at=enroll_date)

    print("Generating 60 days of historical activity (Lessons, Attendance, Homework, Exams)...")
    for g in groups:
        enrolled_students = User.objects.filter(enrollment__group=g)
        
        # Generate 20 lessons over the last 60 days (roughly 2 lessons per week)
        for i in range(1, 21):
            lesson_date = two_months_ago + timedelta(days=i*3)
            if lesson_date > now: break
            
            l = Lesson.objects.create(group=g, title=f"Dars {i}: Mavzu yuzasidan amaliyot", lesson_type='video', content="Batafsil tushuntirish va kod yozish.", order=i)
            # Override creation date if needed by update() (lesson doesn't strictly have a date field, but we generate attendance matching this date)
            
            # Attendance for this lesson date
            for st in enrolled_students:
                Attendance.objects.create(student=st, group=g, date=lesson_date.date(), status=random.choice(['present', 'present', 'present', 'present', 'absent']), marked_by=g.teacher)
                
                # 80% do homework
                if random.random() < 0.8:
                    hw = Homework.objects.create(lesson=l, student=st, file="dummy_hw.txt", grade=random.randint(70, 100), feedback="Yaxshi natija!", status='checked', checked_by=g.assistant)
                    Homework.objects.filter(id=hw.id).update(submitted_at=lesson_date + timedelta(days=1))
        
        # Monthly Exam (30 days ago)
        exam_date = two_months_ago + timedelta(days=30)
        exam = Exam.objects.create(group=g, title="1-Oylik Imtihon", max_score=100, date=exam_date.date(), created_by=g.teacher)
        for st in enrolled_students:
            ExamResult.objects.create(exam=exam, student=st, score=random.randint(60, 100), feedback="Yaxshi o'zlashtirish")

    print("Generating Salaries for last month...")
    last_month_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    for t in teachers:
        Salary.objects.create(user=t, month=last_month_date.date(), students_count=50, percent=50, base_amount=Decimal('3000000.00'), total_amount=Decimal('5000000.00'), is_paid=True, paid_at=now)
    for a in assistants:
        Salary.objects.create(user=a, month=last_month_date.date(), students_count=50, percent=20, base_amount=Decimal('1500000.00'), total_amount=Decimal('2000000.00'), is_paid=True, paid_at=now)

    print("Generating Complaints...")
    for st in students[:3]:
        comp = Complaint.objects.create(student=st, title="Xona haqida", body="Dars xonasida havo almashinuvi yaxshi emas", status='resolved')
        Complaint.objects.filter(id=comp.id).update(created_at=now - timedelta(days=15))

    print("2 Oylik tarix yaratildi! 🚀")

if __name__ == '__main__':
    seed()
