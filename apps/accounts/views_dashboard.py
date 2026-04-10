from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F
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
from apps.courses.models import Lesson, Group, Course, Enrollment
import datetime

def generate_lessons(group, startDate=None, lessonCountStart=None):
    """Auto-generates 30 days of lessons based on schedule type"""
    current_date = startDate or group.start_date
    lessons_created = lessonCountStart or 0
    days_to_check = 30
    
    if group.schedule_type in ['3_days_toq', '3_days']:
        target_days = [0, 2, 4] # Mon, Wed, Fri
    elif group.schedule_type == '3_days_juft':
        target_days = [1, 3, 5] # Tue, Thu, Sat
    elif group.schedule_type == '5_days':
        target_days = [0, 1, 2, 3, 4]
    else: # daily
        target_days = [0, 1, 2, 3, 4, 5, 6]

    for i in range(days_to_check + 1):
        target_date = current_date + datetime.timedelta(days=i)
        if target_date > group.end_date and not startDate: # Only cap by end_date if it's initial generation
             break
        
        # If startDate is provided, we just want 30 days regardless of end_date (extension mode)
        # But if i == 0 and startDate == last lesson date, skip it to avoid duplicates
        if startDate and i == 0: continue

        if target_date.weekday() in target_days:
            lessons_created += 1
            Lesson.objects.create(
                group=group,
                title=f"{lessons_created}-dars. {group.course.title}",
                date=target_date,
                order=lessons_created
            )
    return lessons_created

@login_required
@role_required('student')
def student_dashboard(request):
    from apps.notifications.models import Notification
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    
    enrollments = Enrollment.objects.filter(student=request.user)
    
    from apps.certificates.models import Certificate
    certificates = Certificate.objects.filter(student=request.user)
    
    active_enrollment = enrollments.filter(status='approved').first()
    
    # Check for unpaid enrollments to focus on payments
    unpaid_enrollment = enrollments.filter(status='approved', amount_paid__lt=F('group__course__price')).exists()
    
    context = {
        'enrollments': enrollments,
        'certificates': certificates,
        'active_enrollment': active_enrollment,
        'has_unpaid': unpaid_enrollment,
        'unread_notifications': unread_notifications,
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
    from apps.notifications.models import Notification
    from django.utils import timezone
    from datetime import datetime, timedelta
    
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
    
    # Barcha guruhlaridagi talabalar ro'yxati (takrorlanmas)
    my_students = User.objects.filter(id__in=Enrollment.objects.filter(group__in=groups, status='approved').values('student_id'))
    
    # Bugunlik davomat holati
    today_attendances = Attendance.objects.filter(group__in=groups, date=today).select_related('student', 'group')
    
    groups_with_stats = []
    for g in groups:
        total_lessons = Lesson.objects.filter(group=g).count()
        completed_lessons = Lesson.objects.filter(group=g, date__lt=today).count()
        progress = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0
        
        groups_with_stats.append({
            'group': g,
            'students_count': Enrollment.objects.filter(group=g, status='approved').count(),
            'lessons_count': total_lessons,
            'completed_lessons': completed_lessons,
            'progress': progress,
            'is_new': g.start_date >= today
        })
        
    # --- 10 daqiqa oldin dars eslatmasi mantiqi ---
    now = timezone.now()
    for g in groups:
        # Guruhning dars boshlanish vaqtini bugungi sana bilan birlashtiramiz
        lesson_start = datetime.combine(now.date(), g.lesson_start_time)
        lesson_start = timezone.make_aware(lesson_start)
        
        time_diff = lesson_start - now
        # Agar dars boshlanishiga 0 dan 10 daqiqagacha vaqt qolgan bo'lsa
        if timedelta(minutes=0) < time_diff <= timedelta(minutes=10):
            notif_title = f"Dars boshlanishiga 10 daqiqa qoldi: {g.name}"
            # Shu dars uchun bugun hali xabar yuborilmagan bo'lsa yaratish
            if not Notification.objects.filter(user=request.user, title=notif_title, created_at__date=now.date()).exists():
                Notification.objects.create(
                    user=request.user,
                    title=notif_title,
                    body=f"Sizning '{g.name}' guruhingizdagi darsingiz {g.lesson_start_time.strftime('%H:%M')} da boshlanadi. Iltimos, tayyorgarlik ko'ring.",
                    notif_type='lesson_reminder'
                )
    
    # O'qilmagan xabarlarni olish
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
        
    context = {
        'total_students': total_students,
        'groups_count': groups.count(),
        'salary_amount': salary_amount,
        'avg_attendance': avg_attendance,
        'groups_with_stats': groups_with_stats,
        'today_lessons': today_lessons,
        'my_students': my_students,
        'today_attendances': today_attendances,
        'unread_notifications': unread_notifications,
    }
    return render(request, 'dashboard/teacher.html', context)

@login_required
@role_required('assistant')
def assistant_dashboard(request):
    from apps.courses.models import Group, Enrollment, Lesson
    from apps.salary.models import Salary
    from apps.attendance.models import Attendance
    from apps.homework.models import Homework
    from apps.exams.models import Exam
    from apps.chat.models import Message
    from django.utils import timezone
    from django.db.models import Q
    
    from apps.notifications.models import Notification
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    
    groups = Group.objects.filter(assistant=request.user)
    total_students = Enrollment.objects.filter(group__in=groups, status='approved').values('student').distinct().count()
    
    latest_salary = Salary.objects.filter(user=request.user).order_by('-month').first()
    salary_amount = latest_salary.total_amount if latest_salary else 0
    
    today = timezone.now().date()
    
    # --- Advanced Stats for Maximal Assistant ---
    # Pending Homeworks (Only submitted ones for my groups)
    pending_homeworks = Homework.objects.filter(lesson__group__in=groups, status='submitted').order_by('-submitted_at')
    pending_hw_count = pending_homeworks.count()
    
    # Recent/Upcoming Exams (for my groups)
    upcoming_exams = Exam.objects.filter(group__in=groups).order_by('-date')[:5]
    
    # Unread Chats (Direct to me or in my groups)
    unread_chats_count = Message.objects.filter(
        Q(receiver=request.user, msg_type='direct') | Q(group__in=groups, msg_type='group'),
        is_read=False
    ).exclude(sender=request.user).count()

    groups_with_stats = []
    for g in groups:
        total_lessons = Lesson.objects.filter(group=g).count()
        completed_lessons = Lesson.objects.filter(group=g, date__lt=today).count()
        progress = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0
        
        groups_with_stats.append({
            'group': g,
            'students_count': Enrollment.objects.filter(group=g, status='approved').count(),
            'lessons_count': total_lessons,
            'completed_lessons': completed_lessons,
            'progress': progress,
        })
        
    context = {
        'total_students': total_students,
        'groups_count': groups.count(),
        'salary_amount': salary_amount,
        'groups_with_stats': groups_with_stats,
        'unread_notifications': unread_notifications,
        'pending_hw_count': pending_hw_count,
        'pending_homeworks': pending_homeworks[:5],
        'upcoming_exams': upcoming_exams,
        'unread_chats_count': unread_chats_count,
    }
    return render(request, 'dashboard/assistant.html', context)


from django.contrib import messages
from apps.accounts.models import User

@login_required
@role_required('admin')
def admin_dashboard(request):
    from apps.courses.models import Enrollment, Group
    from django.db.models import Sum, ProtectedError
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
            schedule_type = request.POST.get('schedule_type', '3_days_toq')
            start_time = request.POST.get('lesson_start_time', '10:00')
            end_time = request.POST.get('lesson_end_time', '11:30')
            
            try:
                from apps.courses.models import Course
                course = Course.objects.get(id=course_id)
                teacher = User.objects.get(id=teacher_id)
                assistant = User.objects.get(id=assistant_id) if assistant_id else None
                
                group = Group.objects.create(
                    name=name, course=course, teacher=teacher, assistant=assistant,
                    start_date=start_date, end_date=end_date,
                    schedule_type=schedule_type, 
                    lesson_start_time=start_time,
                    lesson_end_time=end_time
                )
                
                # Auto generate lessons
                generate_lessons(group)
                
                messages.success(request, f"'{name}' guruhi ochildi va darslar avtomatik yaratildi!")
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
                    messages.warning(request, f"Bu user '{group.name}' guruhida bor!")
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
    from apps.notifications.models import Notification
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    
    from apps.salary.models import Salary
    from apps.courses.models import Course, Group, Enrollment
    
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
        'unread_notifications': unread_notifications,
    }
    return render(request, 'dashboard/admin.html', context)


@login_required
@role_required('admin', 'teacher')
def group_preview(request, group_id):
    from apps.courses.models import Group, Enrollment, Lesson
    from django.shortcuts import get_object_or_404

    group = get_object_or_404(Group.objects.select_related('course', 'teacher', 'assistant'), id=group_id)
    enrollments = Enrollment.objects.filter(group=group).select_related('student').order_by('status')
    lessons = Lesson.objects.filter(group=group).order_by('date', 'order')

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
        'lessons': lessons,
        'center_pct': 100 - group.teacher_percent - group.assistant_percent,
    }

    if request.user.role == 'admin':
        context.update({
            'teachers_only': User.objects.filter(role='teacher'),
            'assistants_only': User.objects.filter(role='assistant'),
            'SCHEDULE_TYPES': Group.SCHEDULE_TYPES
        })

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
        try:
            user.delete()
            messages.success(request, f"{name} tizimdan o'chirildi.")
        except ProtectedError:
            messages.error(request, f"Xatolik: {name} o'chira olmaysiz. Chunki unga bog'langan faol guruhlar, maoshlar yoki boshqa ma'lumotlar mavjud. Avval ularni boshqa o'qituvchiga o'tkazing yoki o'chiring.")
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
# ─────────────────────────────────────────────
# ADMIN: Guruhni tahrirlash
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def update_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        group.name = request.POST.get('name', group.name)
        group.teacher_id = request.POST.get('teacher_id', group.teacher_id)
        group.assistant_id = request.POST.get('assistant_id', group.assistant_id) or None
        group.lesson_start_time = request.POST.get('lesson_start_time', group.lesson_start_time)
        group.lesson_end_time = request.POST.get('lesson_end_time', group.lesson_end_time)
        group.schedule_type = request.POST.get('schedule_type', group.schedule_type)
        group.is_active = request.POST.get('is_active') == '1'
        group.save()
        messages.success(request, f"'{group.name}' guruhi tahrirlandi.")
    return redirect('dashboard:admin')

# ─────────────────────────────────────────────
# ADMIN: Guruhni o'chirish
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def delete_group(request, group_id):
    from django.db.models import ProtectedError
    group = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        try:
            group.delete()
            messages.success(request, f"'{group.name}' guruhi o'chirildi.")
        except ProtectedError:
            messages.error(request, f"Xatolik: '{group.name}' guruhini o'chira olmaysiz. Chunki bu guruhda ro'yxatdan o'tgan talabalar yoki mavjud darslar bor. Avval talabalarni boshqa guruhga o'tkazing.")
    return redirect('dashboard:admin')

# ─────────────────────────────────────────────
# ADMIN: Jadvalni 1 oyga uzaytirish
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def extend_lessons(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        last_lesson = Lesson.objects.filter(group=group).order_by('-date').first()
        if last_lesson:
            generate_lessons(group, startDate=last_lesson.date, lessonCountStart=last_lesson.order)
            messages.success(request, f"'{group.name}' jadvali yana 1 oyga uzaytirildi.")
        else:
            generate_lessons(group)
            messages.success(request, f"'{group.name}' jadvali yangidan yaratildi.")
    return redirect('dashboard:admin')

# ─────────────────────────────────────────────
# ADMIN: Darsni yangilash (Fors-major)
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def update_lesson(request, lesson_id):
    from django.http import JsonResponse
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.method == 'POST':
        new_date = request.POST.get('date')
        new_title = request.POST.get('title')
        if new_date:
            lesson.date = new_date
        if new_title:
            lesson.title = new_title
        lesson.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': f"Dars yangilandi: {lesson.title}"})
            
        messages.success(request, f"Dars jadvali yangilandi: {lesson.title}")
    return redirect('dashboard:admin')
