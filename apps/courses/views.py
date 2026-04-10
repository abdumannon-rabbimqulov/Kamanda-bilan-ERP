from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.accounts.decorators import role_required
from .models import Course, Group, Enrollment, Lesson

def course_list(request):
    user = request.user
    all_courses = Course.objects.filter(is_active=True)
    
    if user.is_authenticated and user.role == 'student':
        my_enrollments = Enrollment.objects.filter(student=user, status='approved').select_related('group__course')
        enrolled_ids = my_enrollments.values_list('group__course_id', flat=True)
        other_courses = all_courses.exclude(id__in=enrolled_ids)
    else:
        my_enrollments = None
        other_courses = None

    return render(request, 'courses/course_list.html', {
        'my_enrollments': my_enrollments,
        'other_courses': other_courses,
        'courses': all_courses
    })

def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    is_enrolled = False
    enrollment = None
    
    if request.user.is_authenticated and request.user.role == 'student':
        enrollment = Enrollment.objects.filter(student=request.user, group__course=course, status='approved').select_related('group').first()
        is_enrolled = enrollment is not None
        
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'is_enrolled': is_enrolled,
        'enrollment': enrollment
    })

def enroll_course(request, course_id):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('auth:login')
        course = get_object_or_404(Course, id=course_id)
        if not Group.objects.filter(course=course).exists():
            messages.error(request, "Guruhlar yo'q")
            return redirect('courses:detail', course_id=course.id)
        group = Group.objects.filter(course=course).first()  # simplify picking group for now
        Enrollment.objects.create(student=request.user, group=group)
        messages.success(request, "So'rov yuborildi")
        return redirect('dashboard:student')
    return redirect('courses:detail', course_id=course_id)

@role_required('teacher', 'admin', 'assistant', 'student')
def lesson_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    lessons = Lesson.objects.filter(group=group).order_by('order')
    return render(request, 'courses/lesson_list.html', {'group': group, 'lessons': lessons})

@role_required('teacher', 'admin')
def add_lesson(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        lesson_type = request.POST.get('lesson_type')
        content = request.POST.get('content', '')
        file = request.FILES.get('file')
        if not title:
            return render(request, 'courses/add_lesson.html', {'group': group, 'error': 'Sarlavha majburiy'})
        Lesson.objects.create(group=group, title=title, lesson_type=lesson_type, content=content, file=file)
        messages.success(request, "Dars yaratildi")
        return redirect('courses:lesson_list', group_id=group.id)
    return render(request, 'courses/add_lesson.html', {'group': group})

from django.utils import timezone
from datetime import datetime, timedelta

def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    user_homework = None
    if request.user.is_authenticated and request.user.role == 'student':
        user_homework = Homework.objects.filter(student=request.user, lesson=lesson).first()
    return render(request, 'courses/lesson_detail.html', {'lesson': lesson, 'user_homework': user_homework})

@role_required('teacher', 'admin', 'assistant')
def start_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if lesson.started_at:
        messages.info(request, "Dars allaqachon boshlangan.")
        return redirect('dashboard:teacher')
    
    # Check if lesson is scheduled for today or past
    if lesson.date > timezone.now().date():
        messages.error(request, "Kelajakdagi darsni hozirdan boshlab bo'lmaydi.")
        return redirect('dashboard:teacher')
    
    lesson.started_at = timezone.now()
    lesson.save()
    messages.success(request, f"{lesson.title} muvaffaqiyatli boshlandi.")
    return redirect('dashboard:teacher')
