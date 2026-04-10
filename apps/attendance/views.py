from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Attendance
from apps.courses.models import Group, Enrollment
from apps.accounts.decorators import role_required

@role_required('teacher', 'assistant', 'admin')
def attendance_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    attendances = Attendance.objects.filter(group=group).order_by('-date')
    return render(request, 'attendance/list.html', {'group': group, 'attendances': attendances})

@role_required('teacher', 'assistant')
def mark_attendance(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    enrollments = Enrollment.objects.filter(group=group, status='approved')
    if request.method == 'POST':
        date_str = request.POST.get('date', str(timezone.now().date()))
        for enrollment in enrollments:
            status = request.POST.get(f'status_{enrollment.student.id}')
            if status:
                Attendance.objects.update_or_create(
                    student=enrollment.student, group=group, date=date_str,
                    defaults={'status': status, 'marked_by': request.user}
                )
        messages.success(request, 'Davomat saqlandi')
        return redirect('attendance:list', group_id=group.id)
    return render(request, 'attendance/mark.html', {'group': group, 'enrollments': enrollments})
