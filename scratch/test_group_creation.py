import sys
import os

# Add the project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.courses.models import Course, Group, Lesson
from apps.accounts.models import User
from apps.accounts.views_dashboard import generate_lessons

def test_create_group():
    print("Testing group creation...")
    course = Course.objects.first()
    if not course:
        print("No course found!")
        return
    
    teacher = User.objects.filter(role='teacher').first()
    if not teacher:
        print("No teacher found!")
        return
        
    name = f"TestGroup_{datetime.datetime.now().strftime('%H%M%S')}"
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=30)
    
    print(f"Creating group {name} for course {course.title} with teacher {teacher.username}")
    
    try:
        group = Group.objects.create(
            name=name,
            course=course,
            teacher=teacher,
            start_date=start_date,
            end_date=end_date,
            schedule_type='3_days_toq',
            lesson_start_time='10:00',
            lesson_end_time='11:30'
        )
        print(f"Group created successfully: {group.id}")
        
        lesson_count = generate_lessons(group)
        print(f"Lessons generated: {lesson_count}")
        
        lessons_in_db = Lesson.objects.filter(group=group).count()
        print(f"Lessons in DB: {lessons_in_db}")
        
        if lessons_in_db > 0:
            print("SUCCESS: Group and lessons created!")
        else:
            print("FAILURE: No lessons created!")
            
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")

if __name__ == "__main__":
    test_create_group()
