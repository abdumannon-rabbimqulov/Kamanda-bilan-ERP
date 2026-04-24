from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.accounts.decorators import role_required
from .models import Course, Group, Enrollment, Lesson
from apps.homework.models import Homework

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
    enrollment = Enrollment.objects.filter(student=request.user, group=group).first()
    
    if request.user.role == 'student':
        if enrollment and enrollment.status == 'completed':
            # Bitiruvchilar hamma darslarni ko'ra oladi
            lessons = Lesson.objects.filter(group=group).order_by('order')
        else:
            # Oddiy o'quvchilar faqat boshlangan darslarni ko'radi
            lessons = Lesson.objects.filter(group=group, started_at__isnull=False).order_by('order')
    else:
        lessons = Lesson.objects.filter(group=group).order_by('order')
    
    if request.user.role == 'student':
        from apps.homework.models import Homework
        # O'quvchining ushbu guruhdagi barcha topshirgan vazifalarini olish
        user_homeworks = {h.lesson_id: h for h in Homework.objects.filter(student=request.user, lesson__group=group)}
        for lesson in lessons:
            lesson.user_hw = user_homeworks.get(lesson.id)

    return render(request, 'courses/lesson_list.html', {'group': group, 'lessons': lessons})

@role_required('teacher', 'admin')
def add_lesson(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        lesson_type = request.POST.get('lesson_type')
        content = request.POST.get('content', '')
        homework_task = request.POST.get('homework_task', '')
        file = request.FILES.get('file')
        if not title:
            return render(request, 'courses/add_lesson.html', {'group': group, 'error': 'Sarlavha majburiy'})
        Lesson.objects.create(
            group=group, 
            title=title, 
            lesson_type=lesson_type, 
            content=content, 
            homework_task=homework_task, 
            file=file
        )
        messages.success(request, "Dars muvaffaqiyatli yaratildi")
        return redirect('courses:lesson_list', group_id=group.id)
    return render(request, 'courses/add_lesson.html', {'group': group})

from django.utils import timezone
from datetime import datetime, timedelta

def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    user_homework = None
    enrollment = None
    deadline_passed = False
    edit_disabled = False
    
    if request.user.is_authenticated and request.user.role == 'student':
        user_homework = Homework.objects.filter(student=request.user, lesson=lesson).first()
        enrollment = Enrollment.objects.filter(student=request.user, group=lesson.group).first()
        
        if lesson.started_at:
            days_passed = (timezone.now() - lesson.started_at).days
            if days_passed > 10:
                deadline_passed = True
            if days_passed > 2:
                edit_disabled = True
        
        # Agar vazifa topshirilgan bo'lsa, topshirilgan vaqtdan boshlab 2 kun o'tganini tekshiramiz
        if user_homework:
            hw_days = (timezone.now() - user_homework.submitted_at).days
            if hw_days > 2:
                edit_disabled = True

    return render(request, 'courses/lesson_detail.html', {
        'lesson': lesson, 
        'user_homework': user_homework,
        'enrollment': enrollment,
        'deadline_passed': deadline_passed,
        'edit_disabled': edit_disabled
    })

@role_required('teacher', 'admin', 'assistant')
def start_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if lesson.started_at:
        messages.info(request, "Dars allaqachon boshlangan.")
        return redirect('dashboard:teacher')
    
    if request.method == 'POST':
        now = timezone.localtime()
        # Combine date and time, make it aware
        lesson_start_time = lesson.start_time if lesson.start_time else lesson.group.lesson_start_time
        scheduled_datetime = timezone.make_aware(datetime.combine(lesson.date, lesson_start_time))
        
        if scheduled_datetime > now:
            messages.error(request, f"Darsni faqat dars vaqtida ({lesson_start_time}) boshlash mumkin.")
            return render(request, 'courses/start_lesson.html', {'lesson': lesson})
            
        new_title = request.POST.get('title', '').strip()
        if new_title:
            lesson.title = new_title
            
        lesson.started_at = timezone.now()
        lesson.save()
        messages.success(request, f"'{lesson.title}' darsi muvaffaqiyatli boshlandi.")
        return redirect('dashboard:teacher')
        
    return render(request, 'courses/start_lesson.html', {'lesson': lesson})
@role_required('teacher', 'admin')
def end_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if not lesson.started_at:
        messages.error(request, "Dars hali boshlanmagan.")
        return redirect('dashboard:teacher')
    
    if request.method == 'POST':
        homework_task = request.POST.get('homework_task', '').strip()
        homework_video = request.FILES.get('homework_video')
        homework_image = request.FILES.get('homework_image')
        
        lesson.homework_task = homework_task
        if homework_video:
            lesson.homework_video = homework_video
        if homework_image:
            lesson.homework_image = homework_image
            
        lesson.ended_at = timezone.now()
        lesson.save()
        
        messages.success(request, f"'{lesson.title}' muvaffaqiyatli yakunlandi va vazifa yuborildi.")
        return redirect('dashboard:teacher')

    return render(request, 'courses/end_lesson.html', {'lesson': lesson})


@role_required('admin')
def lesson_reschedule(request, lesson_id):
    """Admin bitta darsni boshqa sana/vaqtga ko'chiradi"""
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if request.method == 'POST':
        new_date = request.POST.get('new_date', '').strip()
        new_start_time = request.POST.get('new_start_time', '').strip()
        new_end_time = request.POST.get('new_end_time', '').strip()

        errors = []
        if not new_date:
            errors.append("Yangi sana majburiy")
        if not new_start_time:
            errors.append("Boshlanish vaqti majburiy")

        if errors:
            return render(request, 'courses/lesson_reschedule.html', {
                'lesson': lesson,
                'errors': errors
            })

        from datetime import date, time
        try:
            lesson.date = date.fromisoformat(new_date)
        except ValueError:
            return render(request, 'courses/lesson_reschedule.html', {
                'lesson': lesson,
                'errors': ["Sana formati noto'g'ri (YYYY-MM-DD)"]
            })

        if new_start_time:
            try:
                h, m = new_start_time.split(':')
                lesson.start_time = time(int(h), int(m))
            except Exception:
                pass

        if new_end_time:
            try:
                h, m = new_end_time.split(':')
                lesson.end_time = time(int(h), int(m))
            except Exception:
                pass

        lesson.save(update_fields=['date', 'start_time', 'end_time'])

        messages.success(
            request,
            f"'{lesson.title}' darsi {new_date} sanasiga {new_start_time} vaqtiga ko'chirildi."
        )
        return redirect('courses:lesson_list', group_id=lesson.group_id)

    return render(request, 'courses/lesson_reschedule.html', {'lesson': lesson})
