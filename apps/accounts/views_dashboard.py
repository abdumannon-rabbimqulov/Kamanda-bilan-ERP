from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.accounts.decorators import role_required
from apps.courses.models import Course, Enrollment

@login_required
def dashboard_home(request):
    user = request.user
    if user.role == 'student': return redirect('dashboard:student')
    elif user.role == 'teacher': return redirect('dashboard:teacher')
    elif user.role == 'assistant': return redirect('dashboard:assistant')
    elif user.role == 'admin': return redirect('dashboard:admin')
    return redirect('auth:login')

from apps.homework.models import Homework
from apps.attendance.models import Attendance
from apps.exams.models import Exam, ExamResult
from apps.courses.models import Lesson

@login_required
@role_required('student')
def student_dashboard(request):
    enrollments = Enrollment.objects.filter(student=request.user)
    
    from apps.certificates.models import Certificate
    certificates = Certificate.objects.filter(student=request.user)
    
    active_enrollment = enrollments.filter(status='approved').first()
    
    context = {
        'enrollments': enrollments,
        'certificates': certificates,
        'active_enrollment': active_enrollment
    }
    
    if active_enrollment:
        g = active_enrollment.group
        total_lessons = Lesson.objects.filter(group=g).count()
        completed_lessons = Attendance.objects.filter(student=request.user, group=g, status='present').count()
        
        # Avoid division by zero
        progress = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0
        
        total_homeworks = total_lessons
        completed_homeworks = Homework.objects.filter(student=request.user, lesson__group=g).count()
        
        total_exams = Exam.objects.filter(group=g).count()
        completed_exams = ExamResult.objects.filter(student=request.user, exam__group=g).count()
        
        recent_lessons = Lesson.objects.filter(group=g).order_by('-order')[:2]
        
        context.update({
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'progress': progress,
            'total_homeworks': total_homeworks,
            'completed_homeworks': completed_homeworks,
            'total_exams': total_exams,
            'completed_exams': completed_exams,
            'recent_lessons': recent_lessons
        })
        
    return render(request, 'dashboard/student.html', context)

@login_required
@role_required('teacher')
def teacher_dashboard(request):
    from apps.courses.models import Group, Enrollment
    from apps.salary.models import Salary
    from apps.attendance.models import Attendance
    from django.utils import timezone
    
    groups = Group.objects.filter(teacher=request.user)
    total_students = Enrollment.objects.filter(group__in=groups, status='approved').values('student').distinct().count()
    
    latest_salary = Salary.objects.filter(user=request.user).order_by('-month').first()
    salary_amount = f"{float(latest_salary.total_amount) / 1000000:.1f}M" if latest_salary else "0.0M"
    
    total_att = Attendance.objects.filter(group__in=groups).count()
    presents = Attendance.objects.filter(group__in=groups, status='present').count()
    avg_attendance = int((presents / total_att) * 100) if total_att > 0 else 0
    
    groups_with_stats = []
    for g in groups:
        groups_with_stats.append({
            'group': g,
            'students_count': Enrollment.objects.filter(group=g, status='approved').count(),
            'lessons_count': Lesson.objects.filter(group=g).count(),
            'is_new': g.start_date >= timezone.now().date()
        })
        
    active_group = groups.first()
    active_group_students = [e.student for e in Enrollment.objects.filter(group=active_group, status='approved')] if active_group else []
    
    if request.method == 'POST' and active_group:
        for st in active_group_students:
            status = request.POST.get(f'attendance_{st.id}', 'present')
            Attendance.objects.update_or_create(
                student=st, 
                group=active_group, 
                date=timezone.now().date(), 
                defaults={'status': status, 'marked_by': request.user}
            )
        from django.contrib import messages
        messages.success(request, f"{active_group.name} guruhi uchun bugungi davomat saqlandi!")
        return redirect('dashboard:teacher')

    context = {
        'total_students': total_students,
        'groups_count': groups.count(),
        'salary_amount': salary_amount,
        'avg_attendance': avg_attendance,
        'groups_with_stats': groups_with_stats,
        'active_group': active_group,
        'active_group_students': active_group_students
    }
    return render(request, 'dashboard/teacher.html', context)

@login_required
@role_required('assistant')
def assistant_dashboard(request):
    return render(request, 'dashboard/assistant.html')

from django.contrib import messages
from apps.accounts.models import User

@login_required
@role_required('admin')
def admin_dashboard(request):
    from apps.courses.models import Enrollment, Group
    from django.db.models import Sum
    from datetime import date
    import datetime

    if request.method == 'POST':
        # Handle User Creation
        if 'create_user' in request.POST:
            email = request.POST.get('email', '').strip()
            role = request.POST.get('role', 'student')
            password = request.POST.get('password', '')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, "Bu email allaqachon mavjud!")
            elif not email or not password:
                messages.error(request, "Email va parol kiritish majburiy!")
            else:
                User.objects.create_user(username=email, email=email, password=password, role=role, is_active=True)
                messages.success(request, f"Yangi foydalanuvchi ({role}) qo'shildi!")
                return redirect('dashboard:admin')
                
        # Handle Enrollment Approval
        elif 'enrollment_action' in request.POST:
            action = request.POST.get('enrollment_action')
            enrollment_id = request.POST.get('enrollment_id')
            enr = Enrollment.objects.filter(id=enrollment_id).first()
            if enr:
                if action == 'approve':
                    enr.status = 'approved'
                    enr.approved_by = request.user
                    enr.save()
                    messages.success(request, "Ro'yxatdan o'tish tasdiqlandi!")
                elif action == 'reject':
                    enr.status = 'rejected'
                    enr.save()
                    messages.success(request, "Ro'yxatdan o'tish rad etildi!")
            return redirect('dashboard:admin')

    # Metrics
    total_students = User.objects.filter(role='student').count()
    
    # Calculate revenue this month
    today = date.today()
    revenue_agg = Enrollment.objects.filter(status='approved', enrolled_at__year=today.year, enrolled_at__month=today.month).aggregate(total=Sum('amount_paid'))
    revenue_val = float(revenue_agg['total'] or 0)
    total_revenue_str = f"{revenue_val / 1000000:.1f}M"
    
    active_groups = Group.objects.filter(is_active=True).count()
    pending_enrollments_all = Enrollment.objects.filter(status='pending').order_by('-enrolled_at')
    pending_count = pending_enrollments_all.count()
    
    # Expose users as well if needed in a modal
    users = User.objects.exclude(id=request.user.id).order_by('-date_joined')
    
    # Expose all groups for the 'Guruhlar' tab
    groups_list = Group.objects.all().select_related('course', 'teacher', 'assistant').order_by('-start_date')
    
    context = {
        'users': users,
        'groups_list': groups_list,
        'total_students': total_students,
        'total_revenue': total_revenue_str,
        'active_groups': active_groups,
        'pending_count': pending_count,
        'recent_enrollments': pending_enrollments_all[:5],
    }
    return render(request, 'dashboard/admin.html', context)


@login_required
@role_required('admin')
def group_preview(request, group_id):
    from apps.courses.models import Group, Enrollment
    from django.shortcuts import get_object_or_404

    group = get_object_or_404(Group.objects.select_related('course', 'teacher', 'assistant'), id=group_id)
    enrollments = Enrollment.objects.filter(group=group).select_related('student').order_by('status')

    students_data = []
    for enr in enrollments:
        course_price = group.course.price
        amount_paid = enr.amount_paid
        is_debtor = amount_paid < course_price
        students_data.append({
            'enrollment': enr,
            'student': enr.student,
            'amount_paid': amount_paid,
            'course_price': course_price,
            'is_debtor': is_debtor,
            'debt': course_price - amount_paid,
        })

    context = {
        'group': group,
        'students_data': students_data,
        'center_pct': 100 - group.teacher_percent - group.assistant_percent,
    }
    return render(request, 'dashboard/fragments/group_preview.html', context)


@login_required
@role_required('admin')
def user_preview(request, user_id):
    from apps.courses.models import Group, Enrollment
    from django.shortcuts import get_object_or_404

    user = get_object_or_404(User, id=user_id)

    enrollments = []
    taught_groups = []
    assisted_groups = []

    if user.role == 'student':
        raw_enrollments = Enrollment.objects.filter(student=user).select_related('group__course')
        for enr in raw_enrollments:
            course_price = enr.group.course.price
            amount_paid = enr.amount_paid
            enrollments.append({
                'enrollment': enr,
                'group': enr.group,
                'course': enr.group.course,
                'amount_paid': amount_paid,
                'is_debtor': amount_paid < course_price,
                'debt': course_price - amount_paid,
            })
    elif user.role == 'teacher':
        taught_groups = Group.objects.filter(teacher=user).select_related('course')
    elif user.role == 'assistant':
        assisted_groups = Group.objects.filter(assistant=user).select_related('course')

    context = {
        'profile': user,
        'enrollments': enrollments,
        'taught_groups': taught_groups,
        'assisted_groups': assisted_groups,
        'all_groups': Group.objects.select_related('course').all(),
    }
    return render(request, 'dashboard/fragments/user_preview.html', context)


# ─────────────────────────────────────────────
# ADMIN: Foydalanuvchini tahrirlash
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def update_user(request, user_id):
    from django.shortcuts import get_object_or_404
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name).strip()
        user.last_name  = request.POST.get('last_name', user.last_name).strip()
        user.phone      = request.POST.get('phone', user.phone).strip()
        user.role       = request.POST.get('role', user.role)
        user.is_active  = request.POST.get('is_active') == '1'

        new_email = request.POST.get('email', '').strip()
        if new_email and new_email != user.email:
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                messages.error(request, 'Bu email boshqa foydalanuvchiga tegishli!')
                return redirect('dashboard:admin')
            user.email    = new_email
            user.username = new_email

        new_pass = request.POST.get('password', '').strip()
        if new_pass:
            user.set_password(new_pass)

        user.save()
        messages.success(request, f"{user.get_full_name() or user.username} ma'lumotlari yangilandi.")
    return redirect('dashboard:admin')


# ─────────────────────────────────────────────
# ADMIN: Foydalanuvchini o'chirish
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def delete_user(request, user_id):
    from django.shortcuts import get_object_or_404
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        if user.role == 'admin':
            messages.error(request, "Admin hisobini o'chirib bo'lmaydi!")
            return redirect('dashboard:admin')
        name = user.get_full_name() or user.username
        user.delete()
        messages.success(request, f"{name} tizimdan o'chirildi.")
    return redirect('dashboard:admin')


# ─────────────────────────────────────────────
# ADMIN: Talabani guruhdan chiqarish
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def remove_from_group(request, enrollment_id):
    from apps.courses.models import Enrollment
    from django.shortcuts import get_object_or_404
    enr = get_object_or_404(Enrollment, id=enrollment_id)

    if request.method == 'POST':
        student_name = enr.student.get_full_name() or enr.student.username
        group_name   = enr.group.name
        enr.delete()
        messages.success(request, f"{student_name} {group_name} guruhidan chiqarildi.")
    return redirect('dashboard:admin')


# ─────────────────────────────────────────────
# ADMIN: Talabaning guruhini o'zgartirish
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def change_student_group(request, enrollment_id):
    from apps.courses.models import Enrollment, Group
    from django.shortcuts import get_object_or_404
    enr = get_object_or_404(Enrollment, id=enrollment_id)

    if request.method == 'POST':
        new_group_id = request.POST.get('group_id', '').strip()
        if new_group_id:
            try:
                new_group = Group.objects.get(id=new_group_id)
                old_name = enr.group.name
                enr.group = new_group
                enr.save()
                messages.success(request, f"{enr.student.get_full_name() or enr.student.username}: {old_name} → {new_group.name} guruhiga ko'chirildi.")
            except Group.DoesNotExist:
                messages.error(request, "Guruh topilmadi.")
    return redirect('dashboard:admin')


# ─────────────────────────────────────────────
# ADMIN: Guruh foizlarini yangilash
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def update_group_percent(request, group_id):
    from apps.courses.models import Group
    from django.shortcuts import get_object_or_404
    group = get_object_or_404(Group, id=group_id)

    if request.method == 'POST':
        try:
            t_pct = int(request.POST.get('teacher_percent', group.teacher_percent))
            a_pct = int(request.POST.get('assistant_percent', group.assistant_percent))
            if t_pct < 0 or a_pct < 0 or (t_pct + a_pct) > 100:
                messages.error(request, "Foizlar noto'g'ri: ularning yig'indisi 100 dan oshmasligi kerak.")
                return redirect('dashboard:admin')
            group.teacher_percent    = t_pct
            group.assistant_percent  = a_pct
            group.save()
            center_pct = 100 - t_pct - a_pct
            messages.success(request, f"{group.name}: Ustoz {t_pct}%, Yordamchi {a_pct}%, Markaz {center_pct}% foizlari yangilandi.")
        except ValueError:
            messages.error(request, "Foizlar butun son bo'lishi kerak.")
    return redirect('dashboard:admin')
