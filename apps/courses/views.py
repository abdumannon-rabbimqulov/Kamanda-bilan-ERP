from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.accounts.decorators import role_required
from .models import Course, Group, Enrollment, Lesson

def course_list(request):
    courses = Course.objects.filter(is_active=True)
    return render(request, 'courses/course_list.html', {'courses': courses})

def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    return render(request, 'courses/course_detail.html', {'course': course})

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

def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    return render(request, 'courses/lesson_detail.html', {'lesson': lesson})
