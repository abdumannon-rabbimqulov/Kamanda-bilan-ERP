from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Attendance
from apps.courses.models import Group, Enrollment
from apps.accounts.decorators import role_required

@role_required('teacher', 'assistant', 'admin')
def attendance_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    enrollments = Enrollment.objects.filter(group=group, status='approved').select_related('student')
    
    # 1. Lesson Date-wise Records (for the history table)
    records = Attendance.objects.filter(group=group).order_by('-date')
    dates = Attendance.objects.filter(group=group).values_list('date', flat=True).distinct().order_by('-date')
    
    attendance_data = []
    for d in dates:
        counts = {
            'present': records.filter(date=d, status='present').count(),
            'absent': records.filter(date=d, status='absent').count(),
            'late': records.filter(date=d, status='late').count(),
        }
        attendance_data.append({
            'date': d,
            'counts': counts
        })

    # 2. Student-wise Statistics (for the summary table)
    student_stats = []
    total_dates = dates.count()
    for enr in enrollments:
        student = enr.student
        s_records = Attendance.objects.filter(group=group, student=student)
        p_count = s_records.filter(status='present').count()
        a_count = s_records.filter(status='absent').count()
        l_count = s_records.filter(status='late').count()
        
        # Percentage calculation (Present + Late count as presence)
        total_p = p_count + l_count
        percent = int((total_p / total_dates) * 100) if total_dates > 0 else 0
        
        student_stats.append({
            'student': student,
            'present': p_count,
            'absent': a_count,
            'late': l_count,
            'total': total_dates,
            'percent': percent,
        })

    return render(request, 'attendance/list.html', {
        'group': group, 
        'attendance_data': attendance_data,
        'student_stats': student_stats
    })

@role_required('teacher', 'assistant')
def mark_attendance(request, group_id):
    from apps.courses.models import Lesson
    group = get_object_or_404(Group, id=group_id)
    enrollments = Enrollment.objects.filter(group=group, status='approved').select_related('student')
    
    # Selecting date (already read-only for teachers in UI)
    date_str = request.GET.get('date', str(timezone.now().date()))
    today = timezone.now().date()
    
    # ══ MAXIMAL SECURITY: Teacher can only mark if lesson started TODAY ══
    if request.user.role in ['teacher', 'assistant']:
        # If trying to mark for a date other than today, block it
        if date_str != str(today):
            messages.error(request, "Ustozlar faqat bugungi dars uchun davomat qila oladilar.")
            return redirect('attendance:list', group_id=group.id)
            
        # Check if any lesson for this group was started today
        lesson_started = Lesson.objects.filter(group=group, date=today, started_at__isnull=False).exists()
        if not lesson_started:
            messages.error(request, "Davomat qilishdan oldin darsni boshlashingiz kerak.")
            return redirect('dashboard:teacher')

    if request.method == 'POST':
        date_str = request.POST.get('date', str(timezone.now().date()))
        for enrollment in enrollments:
            status = request.POST.get(f'status_{enrollment.student.id}')
            if status:
                Attendance.objects.update_or_create(
                    student=enrollment.student, group=group, date=date_str,
                    defaults={'status': status, 'marked_by': request.user}
                )
        messages.success(request, f"{date_str} sanasidagi davomat saqlandi")
        return redirect('attendance:list', group_id=group.id)
        
    # Pre-fetch existing statuses for this date
    existing_records = Attendance.objects.filter(group=group, date=date_str)
    status_map = {r.student_id: r.status for r in existing_records}
    
    students_with_status = []
    for enr in enrollments:
        students_with_status.append({
            'enrollment': enr,
            'current_status': status_map.get(enr.student.id, 'present') # Default to present
        })
    
    return render(request, 'attendance/mark.html', {
        'group': group, 
        'date_str': date_str,
        'students_with_status': students_with_status
    })
