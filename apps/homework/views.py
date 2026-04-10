from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Homework
from apps.courses.models import Lesson, Group
from apps.accounts.decorators import role_required

@role_required('student')
def submit_homework(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Fayl yuklash majburiy')
            return redirect('courses:lesson_detail', lesson_id=lesson.id)
        
        # Check if already submitted
        Homework.objects.update_or_create(
            lesson=lesson, student=request.user,
            defaults={'file': file, 'status': 'submitted'}
        )
        messages.success(request, 'Vazifa muvaffaqiyatli yuborildi')
        return redirect('courses:lesson_detail', lesson_id=lesson.id)
    return redirect('courses:lesson_detail', lesson_id=lesson_id)

@role_required('assistant', 'teacher')
def homework_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    submissions = Homework.objects.filter(lesson__group=group).order_by('-submitted_at')
    return render(request, 'homework/list.html', {
        'group': group,
        'submissions': submissions
    })

@role_required('assistant', 'teacher')
def grade_homework(request, hw_id):
    hw = get_object_or_404(Homework, id=hw_id)
    if request.method == 'POST':
        grade = request.POST.get('grade')
        feedback = request.POST.get('feedback', '')
        if grade:
            hw.grade = int(grade)
            hw.feedback = feedback
            hw.status = 'checked'
            hw.checked_by = request.user
            hw.save()
            messages.success(request, f"{hw.student.username} vazifasi baholandi")
        return redirect('homework:list', group_id=hw.lesson.group.id)
    return render(request, 'homework/grade.html', {'hw': hw})
