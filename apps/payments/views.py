from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.accounts.decorators import role_required
from apps.accounts.models import User
from apps.courses.models import Enrollment, Group
from apps.notifications.models import Notification
from .models import Payment
from apps.salary.models import Salary
from decimal import Decimal
import uuid


def send_notification(user, title, body, notif_type='payment_reminder'):
    Notification.objects.create(user=user, title=title, body=body, notif_type=notif_type)


# ─────────────────────────────────────────────
# ADMIN: To'lovlar Boshqaruv Paneli
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def payments_dashboard(request):
    from django.db.models import Sum

    # All enrollments with payment info
    enrollments = Enrollment.objects.select_related('student', 'group__course').order_by('-enrolled_at')

    # Stats
    # Get total collected from actual payment records (excluding internal salary transfers)
    total_collected = Payment.objects.filter(status='success').exclude(method='salary_transfer').aggregate(total=Sum('amount'))['total'] or 0
    
    total_expected = sum(e.group.course.price for e in enrollments if e.status == 'approved')
    total_debt = max(total_expected - total_collected, 0)
    debtors_count = sum(1 for e in enrollments if e.status == 'approved' and e.amount_paid < e.group.course.price)

    # Center Balance (Net Profit): Total Collected - Total Salary Paid
    from apps.salary.models import Salary
    total_salaries_paid = Salary.objects.filter(is_paid=True).aggregate(total=Sum('total_amount'))['total'] or 0
    center_balance = total_collected - total_salaries_paid



    # Salary payments sent
    salary_payments = Payment.objects.filter(method='salary_transfer').select_related('enrollment').order_by('-paid_at')[:20]

    return render(request, 'payments/dashboard.html', {
        'enrollments': enrollments,
        'total_collected': total_collected,
        'total_expected': total_expected,
        'total_debt': total_debt,
        'debtors_count': debtors_count,
        'salary_payments': salary_payments,
        'center_balance': center_balance,
        'total_paid': total_salaries_paid,
    })


# ─────────────────────────────────────────────
# ADMIN: O'quvchidan to'lov qabul qilish
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def record_student_payment(request):
    if request.method == 'POST':
        enrollment_id = request.POST.get('enrollment_id')
        amount_str = request.POST.get('amount', '0').replace(' ', '').replace(',', '')

        try:
            amount = Decimal(amount_str)
        except Exception:
            messages.error(request, "Noto'g'ri summa kiritildi.")
            return redirect('payments:dashboard')

        enr = get_object_or_404(Enrollment, id=enrollment_id)
        group = enr.group
        course_price = group.course.price
        method = request.POST.get('method', 'cash')

        enr.amount_paid = Decimal(str(enr.amount_paid)) + amount
        enr.save()

        # Create payment record
        Payment.objects.create(
            enrollment=enr,
            amount=amount,
            method=method,
            transaction_id=str(uuid.uuid4()),
            status='success'
        )

        # ── Foiz bo'yicha avtomatik maosh taqsimlash ──
        teacher_pct = group.teacher_percent       # masalan 40
        assistant_pct = group.assistant_percent   # masalan 15
        # center_pct = 100 - teacher_pct - assistant_pct

        teacher_share = (amount * Decimal(teacher_pct)) / Decimal(100)
        assistant_share = (amount * Decimal(assistant_pct)) / Decimal(100) if group.assistant else Decimal('0')

        # Teacher salary update
        from apps.salary.models import Salary
        from django.utils import timezone
        today = timezone.now().date().replace(day=1)
        t_sal, _ = Salary.objects.get_or_create(
            user=group.teacher, month=today,
            defaults={'students_count': 0, 'percent': teacher_pct, 'base_amount': 0, 'total_amount': 0}
        )
        t_sal.total_amount = Decimal(str(t_sal.total_amount)) + teacher_share
        t_sal.base_amount  = Decimal(str(t_sal.base_amount)) + teacher_share
        t_sal.students_count = Enrollment.objects.filter(group__teacher=group.teacher, status='approved').count()
        t_sal.save()

        # Assistant salary update
        if group.assistant and assistant_share > 0:
            a_sal, _ = Salary.objects.get_or_create(
                user=group.assistant, month=today,
                defaults={'students_count': 0, 'percent': assistant_pct, 'base_amount': 0, 'total_amount': 0}
            )
            a_sal.total_amount = Decimal(str(a_sal.total_amount)) + assistant_share
            a_sal.base_amount  = Decimal(str(a_sal.base_amount)) + assistant_share
            a_sal.students_count = Enrollment.objects.filter(group__assistant=group.assistant, status='approved').count()
            a_sal.save()

        # Notifications
        remaining = course_price - enr.amount_paid
        if remaining <= 0:
            send_notification(enr.student, "To'lov tasdiqlandi ✅",
                f"{group.course.title} kursi uchun to'lov to'liq amalga oshirildi!")
        else:
            send_notification(enr.student, "Qisman to'lov qabul qilindi",
                f"{group.course.title} uchun {float(amount):,.0f} UZS qabul qilindi. Qolgan: {float(remaining):,.0f} UZS")

        messages.success(request, f"{enr.student.get_full_name() or enr.student.username}: {float(amount):,.0f} UZS qabul qilindi. O'qituvchi: +{float(teacher_share):,.0f} UZS")
        return redirect('payments:dashboard')

    return redirect('payments:dashboard')


# ─────────────────────────────────────────────
# ADMIN: Ustoz/Yordamchiga oylik yuborish
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def send_salary_payment(request):
    if request.method == 'POST':
        salary_id = request.POST.get('salary_id')
        from apps.salary.models import Salary
        from django.utils import timezone
        salary = get_object_or_404(Salary, id=salary_id)

        # Check Center Balance
        from django.db.models import Sum
        total_collected = Payment.objects.filter(status='success').exclude(method='salary_transfer').aggregate(total=Sum('amount'))['total'] or 0
        total_salaries_paid = Salary.objects.filter(is_paid=True).aggregate(total=Sum('total_amount'))['total'] or 0
        center_balance = total_collected - total_salaries_paid

        if center_balance < salary.total_amount:
            messages.error(request, "Xatolik: Markaz balansi ushbu maoshni to'lash uchun yetarli emas!")
            return redirect('salary:list')

        # Mark as paid
        salary.is_paid = True
        salary.paid_at = timezone.now()
        salary.save()

        # Create payment record for audit trail
        first_enr = Enrollment.objects.filter(group__teacher=salary.user).first() or Enrollment.objects.filter(group__assistant=salary.user).first()
        if first_enr:
            Payment.objects.create(
                enrollment=first_enr,
                amount=salary.total_amount,
                method='salary_transfer',
                transaction_id=f"SALARY-{salary.id}-{uuid.uuid4().hex[:8]}",
                status='success'
            )

        send_notification(
            salary.user,
            "Oylik maoshingiz to'landi 💰",
            f"{salary.month.strftime('%Y-%m')} oyi uchun {float(salary.total_amount):,.0f} UZS maoshingiz to'landi.",
        )

        messages.success(request, f"{salary.user.get_full_name() or salary.user.username} ga {float(salary.total_amount):,.0f} UZS oylik yuborildi.")
        return redirect('salary:list')

    return redirect('salary:list')


# ─────────────────────────────────────────────
# ADMIN: Barcha Qarzdorlarga Bildirishnoma
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def notify_debtors(request):
    if request.method == 'POST':
        enrollments = Enrollment.objects.filter(status='approved').select_related('student', 'group__course')
        count = 0
        for enr in enrollments:
            if enr.amount_paid < enr.group.course.price:
                debt = enr.group.course.price - enr.amount_paid
                send_notification(
                    enr.student,
                    "⚠️ To'lov eslatmasi — Qarzdorsiz!",
                    f"{enr.group.course.title} kursi uchun {float(debt):,.0f} UZS qarz mavjud. Iltimos, imkon qadar tezroq to'lang.",
                )
                count += 1
        messages.success(request, f"{count} ta qarzdor o'quvchiga bildirishnoma yuborildi.")
        return redirect('payments:dashboard')

    return redirect('payments:dashboard')


# ─────────────────────────────────────────────
# STUDENT: O'z profilidan to'lov qilish
# ─────────────────────────────────────────────
@login_required
@role_required('student')
def student_make_payment(request):
    if request.method == 'POST':
        enrollment_id = request.POST.get('enrollment_id')
        amount_str = request.POST.get('amount', '0').replace(' ', '').replace(',', '')

        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError
        except Exception:
            messages.error(request, "Noto'g'ri summa.")
            return redirect('dashboard:student')

        enr = get_object_or_404(Enrollment, id=enrollment_id, student=request.user)
        course_price = enr.group.course.price

        # Simulate online payment (in real project: Click/Payme API)
        enr.amount_paid = Decimal(str(enr.amount_paid)) + amount
        enr.save()

        Payment.objects.create(
            enrollment=enr,
            amount=amount,
            method='online',
            transaction_id=str(uuid.uuid4()),
            status='success'
        )

        debt = enr.remaining_debt
        if debt <= 0:
            if debt < 0:
                msg_body = f"{enr.group.course.title} uchun to'lov qabul qilindi. Sizda {float(abs(debt)):,.0f} UZS haqdorlik (ortiqcha to'lov) mavjud."
                title = "Haqdorlik balansi ✅"
            else:
                msg_body = f"{enr.group.course.title} kursi uchun to'lovni to'liq amalga oshirdingiz. Tabriklaymiz!"
                title = "To'lov muvaffaqiyatli ✅"
        else:
            msg_body = f"To'lovingiz qabul qilindi. Kurs uchun qolgan qarz: {float(debt):,.0f} UZS."
            title = "Qisman to'lov amalga oshirildi"

        send_notification(request.user, title, msg_body)
        messages.success(request, f"{float(amount):,.0f} UZS to'lov muvaffaqiyatli amalga oshirildi!")
        return redirect('dashboard:student')

    return redirect('dashboard:student')
