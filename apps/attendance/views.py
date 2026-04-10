from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Attendance
from apps.courses.models import Group, Enrollment
from apps.accounts.decorators import role_required

@role_required('teacher', 'assistant', 'admin')
def attendance_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    # Group by date for a nicer UI list
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

    return render(request, 'attendance/list.html', {
        'group': group, 
        'attendance_data': attendance_data
    })

@role_required('teacher', 'assistant')
def mark_attendance(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    enrollments = Enrollment.objects.filter(group=group, status='approved').select_related('student')
    
    # Selected date
    date_str = request.GET.get('date', str(timezone.now().date()))
    
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
