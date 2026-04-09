import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from Admin.models import CustomUser, Course, Group, Lesson, Payment
from django.utils import timezone
from decimal import Decimal

# Administrator
admin, _ = CustomUser.objects.get_or_create(username='admin', defaults={
    'email': 'admin@lms.uz',
    'role': 'admin',
    'is_staff': True,
    'is_superuser': True,
    'is_active': True,
    'is_verified': True
})
admin.set_password('123')
admin.save()

# Ustoz
teacher, _ = CustomUser.objects.get_or_create(username='ustoz', defaults={
    'email': 'teacher@lms.uz',
    'role': 'teacher',
    'is_active': True,
    'is_verified': True
})
teacher.set_password('123')
teacher.save()

# Assistant
assistant, _ = CustomUser.objects.get_or_create(username='assistant_bobur', defaults={
    'email': 'assistant@lms.uz',
    'role': 'assistant',
    'is_active': True,
    'is_verified': True
})
assistant.set_password('123')
assistant.save()

# O'quvchi
student, _ = CustomUser.objects.get_or_create(username='talaba1', defaults={
    'email': 'student@lms.uz',
    'role': 'student',
    'is_active': True,
    'is_verified': True
})
student.set_password('123')
student.save()

# Kurs
course1, _ = Course.objects.get_or_create(name='Python Fullstack 2026', defaults={
    'description': 'Noldan boshlab kuchli dasturchi bo\'lamiz!',
    'price': Decimal('500000.00')
})

course2, _ = Course.objects.get_or_create(name='Ingliz Tili (IELTS 7.0)', defaults={
    'description': 'IELTS uchun jadallashtirilgan kurs',
    'price': Decimal('350000.00')
})

# Guruh
group1, _ = Group.objects.get_or_create(name='P-132', course=course1, teacher=teacher, assistant=assistant)
group1.students.add(student)

group2, _ = Group.objects.get_or_create(name='ENG-89', course=course2, teacher=teacher)
group2.students.add(student)

# Dars
Lesson.objects.get_or_create(group=group1, title='Kirish. Django Arxitekturasi', content='Django MTV.')
Lesson.objects.get_or_create(group=group1, title='Modellar va Relational DB', content='OneToMany, ManyToMany.')

print("Ma'lumotlar muvaffaqiyatli bazaga yozildi. Login: admin/123, ustoz/123, talaba1/123")
