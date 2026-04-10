from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Homework
from apps.courses.models import Lesson
from apps.accounts.decorators import role_required

@role_required('student')
def submit_homework(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Fayl yuklash majburiy')
            return redirect('courses:lesson_detail', lesson_id=lesson.id)
        Homework.objects.create(lesson=lesson, student=request.user, file=file)
        messages.success(request, 'Vazifa yuborildi')
        return redirect('courses:lesson_detail', lesson_id=lesson.id)
    return redirect('courses:lesson_detail', lesson_id=lesson_id)

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
            messages.success(request, "Baho qo'yildi")
        return redirect('dashboard:assistant') # simple redirect
    return render(request, 'homework/grade.html', {'hw': hw})
