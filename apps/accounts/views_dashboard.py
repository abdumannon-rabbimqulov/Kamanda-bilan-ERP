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
    from apps.courses.models import Group, Enrollment, Lesson
    from apps.salary.models import Salary
    from apps.attendance.models import Attendance
    from django.utils import timezone
    
    today = timezone.now().date()
    groups = Group.objects.filter(teacher=request.user)
    
    # Bugungi darslar
    today_lessons = Lesson.objects.filter(group__in=groups, date=today).select_related('group').order_by('group__lesson_start_time')
    
    total_students = Enrollment.objects.filter(group__in=groups, status='approved').values('student').distinct().count()
    
    latest_salary = Salary.objects.filter(user=request.user).order_by('-month').first()
    salary_amount = latest_salary.total_amount if latest_salary else 0
    
    total_att = Attendance.objects.filter(group__in=groups).count()
    presents = Attendance.objects.filter(group__in=groups, status='present').count()
    avg_attendance = int((presents / total_att) * 100) if total_att > 0 else 0
    
    groups_with_stats = []
    for g in groups:
        groups_with_stats.append({
            'group': g,
            'students_count': Enrollment.objects.filter(group=g, status='approved').count(),
            'lessons_count': Lesson.objects.filter(group=g).count(),
            'is_new': g.start_date >= today
        })
        
    context = {
        'total_students': total_students,
        'groups_count': groups.count(),
        'salary_amount': salary_amount,
        'avg_attendance': avg_attendance,
        'groups_with_stats': groups_with_stats,
        'today_lessons': today_lessons,
    }
    return render(request, 'dashboard/teacher.html', context)

@login_required
@role_required('assistant')
def assistant_dashboard(request):
    from apps.courses.models import Group, Enrollment
    from apps.salary.models import Salary
    from apps.attendance.models import Attendance
    from django.utils import timezone
    
    groups = Group.objects.filter(assistant=request.user)
    total_students = Enrollment.objects.filter(group__in=groups, status='approved').values('student').distinct().count()
    
    latest_salary = Salary.objects.filter(user=request.user).order_by('-month').first()
    salary_amount = latest_salary.total_amount if latest_salary else 0
    
    groups_with_stats = []
    for g in groups:
        groups_with_stats.append({
            'group': g,
            'students_count': Enrollment.objects.filter(group=g, status='approved').count(),
            'lessons_count': Lesson.objects.filter(group=g).count(),
        })
        
    context = {
        'total_students': total_students,
        'groups_count': groups.count(),
        'salary_amount': salary_amount,
        'groups_with_stats': groups_with_stats,
    }
    return render(request, 'dashboard/assistant.html', context)


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
                
        # Handle Course Creation
        elif 'create_course' in request.POST:
            title = request.POST.get('title')
            description = request.POST.get('description', '')
            price = request.POST.get('price', 0)
            category = request.POST.get('category', 'IT')
            teacher_id = request.POST.get('teacher_id')
            thumbnail = request.FILES.get('thumbnail')
            
            try:
                teacher = User.objects.get(id=teacher_id, role='teacher')
                from apps.courses.models import Course
                Course.objects.create(
                    title=title,
                    description=description,
                    price=price,
                    category=category,
                    teacher=teacher,
                    thumbnail=thumbnail
                )
                messages.success(request, f"'{title}' kursi muvaffaqiyatli qo'shildi!")
            except Exception as e:
                messages.error(request, f"Xatolik: {str(e)}")
            return redirect('dashboard:admin')

        # Handle Group Creation
        elif 'create_group' in request.POST:
            name = request.POST.get('name')
            course_id = request.POST.get('course_id')
            teacher_id = request.POST.get('teacher_id')
            assistant_id = request.POST.get('assistant_id')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            schedule_type = request.POST.get('schedule_type', '3_days')
            start_time = request.POST.get('lesson_start_time', '10:00')
            
            try:
                from apps.courses.models import Course
                course = Course.objects.get(id=course_id)
                teacher = User.objects.get(id=teacher_id)
                assistant = User.objects.get(id=assistant_id) if assistant_id else None
                
                Group.objects.create(
                    name=name, course=course, teacher=teacher, assistant=assistant,
                    start_date=start_date, end_date=end_date,
                    schedule_type=schedule_type, lesson_start_time=start_time
                )
                messages.success(request, f"'{name}' guruhi muvaffaqiyatli ochildi va darslar avtomatik yaratildi!")
                return redirect('dashboard:admin')
            except Exception as e:
                messages.error(request, f"Xatolik: {str(e)}")
                return redirect('dashboard:admin')

            return redirect('dashboard:admin')

        # Handle Manual Student to Group Assignment
        elif 'assign_student_to_group' in request.POST:
            student_id = request.POST.get('student_id')
            group_id = request.POST.get('group_id')
            
            try:
                from apps.notifications.models import Notification
                from django.core.mail import send_mail
                from apps.courses.models import Group, Enrollment
                from config.settings import DEFAULT_FROM_EMAIL
                
                student = get_object_or_404(User, id=student_id, role='student')
                group = get_object_or_404(Group, id=group_id)
                
                # Check for existing
                if Enrollment.objects.filter(student=student, group=group).exists():
                    messages.warning(request, f"{student.first_name} allaqachon '{group.name}' guruhida mavjud!")
                else:
                    enr = Enrollment.objects.create(
                        student=student, 
                        group=group, 
                        status='approved',
                        approved_by=request.user
                    )
                    
                    # 1. Internal Notification
                    Notification.objects.create(
                        user=student,
                        title="Guruhga qo'shildingiz ✅",
                        body=f"Siz admin tomonidan '{group.name}' guruhiga qo'shildingiz. Iltimos, birinchi oy uchun {group.course.price:,.0f} UZS to'lovni amalga oshiring.",
                        notif_type='payment_reminder'
                    )
                    
                    # 2. Email Notification
                    try:
                        subject = "LMS Platform: Guruhga qo'shilish tasdiqlandi"
                        message = (
                            f"Salom {student.first_name or student.username},\n\n"
                            f"Siz muvaffaqiyatli ravishda '{group.name}' ({group.course.title}) guruhiga qo'shildingiz.\n\n"
                            f"Kurs oylik to'lovi: {group.course.price:,.0f} UZS.\n"
                            "Iltimos, darslar boshlanishidan oldin to'lovni amalga oshiring.\n\n"
                            "Hurmat bilan,\nAdmin jamoasi"
                        )
                        send_mail(subject, message, DEFAULT_FROM_EMAIL, [student.email], fail_silently=True)
                    except Exception as e:
                        print(f"Email yuborishda xatolik: {e}")

                    messages.success(request, f"{student.get_full_name() or student.username} muvaffaqiyatli '{group.name}' guruhiga qo'shildi!")
            except Exception as e:
                messages.error(request, f"Xatolik: {str(e)}")
            return redirect('dashboard:admin')

    # Metrics
    total_students = User.objects.filter(role='student').count()
    
    # Financial Stats (Consistent with centers balance)
    from apps.payments.models import Payment
    from apps.salary.models import Salary
    from apps.courses.models import Course # Ensure course is available for context if needed
    
    gross_total = Payment.objects.filter(status='success').exclude(method='salary_transfer').aggregate(total=Sum('amount'))['total'] or 0
    total_paid = Salary.objects.filter(is_paid=True).aggregate(total=Sum('total_amount'))['total'] or 0
    center_balance = gross_total - total_paid

    active_groups = Group.objects.filter(is_active=True).count()
    pending_enrollments_all = Enrollment.objects.filter(status='pending').order_by('-enrolled_at')
    pending_count = pending_enrollments_all.count()
    
    # Expose users as well if needed in a modal
    from django.db.models import Exists, OuterRef
    from apps.courses.models import Enrollment
    
    users = User.objects.exclude(id=request.user.id).annotate(
        has_approved_group=Exists(
            Enrollment.objects.filter(student=OuterRef('pk'), status='approved')
        )
    ).order_by('-date_joined')
    teachers_only = User.objects.filter(role='teacher', is_active=True)
    assistants_only = User.objects.filter(role='assistant', is_active=True)
    all_courses = Course.objects.filter(is_active=True)
    
    # Expose all groups for the 'Guruhlar' tab
    groups_list = Group.objects.all().select_related('course', 'teacher', 'assistant').order_by('-start_date')
    
    context = {
        'users': users,
        'teachers_only': teachers_only,
        'assistants_only': assistants_only,
        'all_courses': all_courses,
        'groups_list': groups_list,
        'total_students': total_students,
        'total_revenue': gross_total,
        'center_balance': center_balance,
        'total_paid': total_paid,
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
