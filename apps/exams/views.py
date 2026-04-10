from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Exam, ExamResult
from apps.courses.models import Group, Enrollment
from apps.accounts.decorators import role_required

@role_required('teacher', 'assistant', 'admin', 'student')
def exam_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    exams = Exam.objects.filter(group=group).order_by('-date')
    
    if request.user.role == 'student':
        results = ExamResult.objects.filter(student=request.user, exam__group=group)
        result_map = {r.exam_id: r for r in results}
        for exam in exams:
            exam.student_result = result_map.get(exam.id)
        
    return render(request, "exams/list.html", {
        'group': group, 
        'exams': exams,
    })

@role_required('teacher', 'assistant')
def add_exam(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        title = request.POST.get('title')
        exam_type = request.POST.get('exam_type')
        date = request.POST.get('date', str(timezone.now().date()))
        max_score = request.POST.get('max_score', 100)
        
        if title and exam_type:
            Exam.objects.create(
                group=group,
                title=title,
                exam_type=exam_type,
                date=date,
                max_score=max_score,
                created_by=request.user
            )
            messages.success(request, "Imtihon muvaffaqiyatli yaratildi")
            return redirect('exams:list', group_id=group.id)
            
    return render(request, "exams/add.html", {'group': group})

@role_required('teacher', 'assistant')
def post_results(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    enrollments = Enrollment.objects.filter(group=exam.group, status='approved').select_related('student')
    
    if request.method == 'POST':
        for enr in enrollments:
            score = request.POST.get(f'score_{enr.student.id}')
            feedback = request.POST.get(f'feedback_{enr.student.id}', '')
            if score:
                ExamResult.objects.update_or_create(
                    exam=exam, student=enr.student,
                    defaults={'score': int(score), 'feedback': feedback}
                )
        messages.success(request, "Imtihon natijalari saqlandi")
        return redirect('exams:list', group_id=exam.group.id)
        
    # Pre-fetch existing results
    existing_results = ExamResult.objects.filter(exam=exam)
    result_map = {r.student_id: r for r in existing_results}
    
    students_with_results = []
    for enr in enrollments:
        students_with_results.append({
            'enrollment': enr,
            'result': result_map.get(enr.student.id)
        })
        
    return render(request, "exams/results.html", {
        'exam': exam,
        'students_with_results': students_with_results
    })