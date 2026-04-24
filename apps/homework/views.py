from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Homework
from apps.courses.models import Lesson, Group
from apps.accounts.decorators import role_required

@role_required('student')
def submit_homework(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Kurs tugallanganligini tekshirish
    from apps.courses.models import Enrollment
    enrollment = Enrollment.objects.filter(student=request.user, group=lesson.group).first()
    if enrollment and enrollment.status == 'completed':
        messages.error(request, 'Kurs yakunlangan. Vazifa yuborish imkoniyati yopiq.')
        return redirect('courses:lesson_detail', lesson_id=lesson.id)

    # 10 kunlik muddatni tekshirish (Hard deadline)
    from django.utils import timezone
    if lesson.started_at:
        days_passed = (timezone.now() - lesson.started_at).days
        if days_passed > 10:
            messages.error(request, 'Vazifa topshirish muddati (10 kun) tugagan.')
            return redirect('courses:lesson_detail', lesson_id=lesson.id)
        
        # 2 kunlik bonus va tahrirlash muddati
        is_bonus_eligible = days_passed <= 2
    else:
        # Dars hali rasman boshlanmagan bo'lsa (lekin student ko'rayotgan bo'lsa)
        is_bonus_eligible = True

    if request.method == 'POST':
        file = request.FILES.get('file')
        github_link = request.POST.get('github_link', '').strip()
        comment = request.POST.get('comment', '').strip()
        
        if not any([file, github_link, comment]):
            messages.error(request, 'Hech bo\'lmaganda bitta ma\'lumot (fayl, link yoki izoh) yuborish kerak')
            return redirect('courses:lesson_detail', lesson_id=lesson.id)
        
        # Tahrirlash cheklovini tekshirish (agar oldin topshirilgan bo'lsa)
        existing_hw = Homework.objects.filter(lesson=lesson, student=request.user).first()
        if existing_hw:
            hw_days = (timezone.now() - existing_hw.submitted_at).days
            if hw_days > 2:
                messages.error(request, 'Vazifani topshirganingizdan keyin 2 kun o\'tib bo\'ldi. Endi tahrirlab bo\'lmaydi.')
                return redirect('courses:lesson_detail', lesson_id=lesson.id)

        # Check if already submitted
        Homework.objects.update_or_create(
            lesson=lesson, student=request.user,
            defaults={
                'file': file if file else None,
                'github_link': github_link if github_link else None,
                'comment': comment,
                'status': 'submitted',
                'is_bonus_eligible': is_bonus_eligible
            }
        )
        messages.success(request, 'Vazifa muvaffaqiyatli yuborildi')
        return redirect('courses:lesson_detail', lesson_id=lesson.id)
    return redirect('courses:lesson_detail', lesson_id=lesson_id)

@role_required('assistant', 'teacher', 'student')
def homework_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    user = request.user
    
    if user.role == 'student':
        # Fetch only started lessons for the group
        lessons = Lesson.objects.filter(group=group, started_at__isnull=False).order_by('order')
        # Fetch student submissions for these lessons
        my_homeworks = Homework.objects.filter(student=user, lesson__group=group)
        hw_map = {hw.lesson_id: hw for hw in my_homeworks}
        
        # Attach homework to lesson objects for easy template access
        for lesson in lessons:
            lesson.homework = hw_map.get(lesson.id)
        
        return render(request, 'homework/list.html', {
            'group': group,
            'lessons': lessons,
            'is_student': True
        })
    else:
        # Teacher/Assistant view: Show all student submissions
        submissions = Homework.objects.filter(lesson__group=group).select_related('student', 'lesson').order_by('-submitted_at')
        return render(request, 'homework/list.html', {
            'group': group,
            'submissions': submissions,
            'is_student': False
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
            
            # Rewards Logic
            grade_val = hw.grade
            xp = grade_val * 2
            coins = grade_val // 10
            
            if hw.is_bonus_eligible:
                xp = int(xp * 1.5)
                coins = int(coins * 1.5)
                # Extra bonus for high score in time
                if grade_val >= 90:
                    coins += 10
            
            hw.xp_awarded = xp
            hw.coins_awarded = coins
            hw.save()
            
            # Update User total
            student = hw.student
            student.xp += xp
            student.coins += coins
            student.save()
            
            messages.success(request, f"{hw.student.username} vazifasi baholandi. +{xp} XP, +{coins} Coin berildi.")
        return redirect('homework:list', group_id=hw.lesson.group.id)
    return render(request, 'homework/grade.html', {'hw': hw})
