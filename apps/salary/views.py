from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.accounts.decorators import role_required
from .models import Salary
from apps.accounts.models import User
from apps.courses.models import Course, Group, Enrollment
from apps.attendance.models import Attendance
from datetime import datetime
from decimal import Decimal
import calendar

@login_required
def salary_list(request):
    from django.db.models import Sum
    from datetime import datetime
    
    user = request.user
    salaries = Salary.objects.all().order_by('-month', 'user__username')
    
    month_filter = request.GET.get('month')
    
    if month_filter and len(month_filter) == 7 and '-' in month_filter:
        date_query = f"{month_filter}-01"
        salaries = salaries.filter(month=date_query)
        try:
            latest_month = datetime.strptime(date_query, '%Y-%m-%d').date()
        except ValueError:
            latest_month = None
    else:
        # Default to latest month if not specified
        latest_month = salaries.first().month if salaries.exists() else None
        if latest_month:
            salaries = salaries.filter(month=latest_month)
    
    # Filter by user if not admin
    if user.role != 'admin':
        salaries = salaries.filter(user=user)
        # Calculate totals for teacher/assistant
        pending_balance = Salary.objects.filter(user=user, is_paid=False).aggregate(total=Sum('total_amount'))['total'] or 0
        history_total = Salary.objects.filter(user=user, is_paid=True).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # ══ ENHANCEMENT: Calculate breakdown for each salary record ══
        from apps.courses.models import Group, Enrollment
        import calendar
        
        for s in salaries:
            breakdown = []
            month_start = s.month
            last_day = calendar.monthrange(month_start.year, month_start.month)[1]
            month_end = month_start.replace(day=last_day)
            
            # Find groups active for THIS user in THIS month
            filter_kwargs = {
                'start_date__lte': month_end,
                'end_date__gte': month_start,
            }
            if s.user.role == 'teacher':
                filter_kwargs['teacher'] = s.user
            else:
                filter_kwargs['assistant'] = s.user
                
            active_groups = Group.objects.filter(**filter_kwargs)
            for g in active_groups:
                count = Enrollment.objects.filter(group=g, status='approved').count()
                if count > 0:
                    revenue = g.course.price * Decimal(str(count))
                    # Determine percent based on role
                    pct = g.teacher_percent if s.user.role == 'teacher' else g.assistant_percent
                    amount = (revenue * Decimal(str(pct))) / Decimal('100')
                    breakdown.append({
                        'group_name': g.name,
                        'student_count': count,
                        'course_price': g.course.price,
                        'percent': pct,
                        'amount': amount
                    })
            s.breakdown = breakdown
    else:
        pending_balance = 0
        history_total = 0
        
    context = {
        'salaries': salaries,
        'latest_month': latest_month,
        'filtered_month': month_filter,
        'pending_balance': pending_balance,
        'history_total': history_total,
    }

    # Admin-only stats
    if user.role == 'admin':
        from apps.payments.models import Payment
        gross_total = Payment.objects.filter(status='success').exclude(method='salary_transfer').aggregate(total=Sum('amount'))['total'] or 0
        total_salaries_paid = Salary.objects.filter(is_paid=True).aggregate(total=Sum('total_amount'))['total'] or 0
        center_balance = gross_total - total_salaries_paid
        
        if latest_month:
            monthly_revenue = Payment.objects.filter(
                status='success', 
                paid_at__year=latest_month.year, 
                paid_at__month=latest_month.month
            ).exclude(method='salary_transfer').aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_expense = Salary.objects.filter(
                is_paid=True, 
                paid_at__year=latest_month.year, 
                paid_at__month=latest_month.month
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            monthly_profit = monthly_revenue - monthly_expense
        else:
            monthly_revenue = monthly_expense = monthly_profit = 0

        context.update({
            'gross_total': gross_total,
            'total_paid': total_salaries_paid,
            'center_balance': center_balance,
            'monthly_revenue': monthly_revenue,
            'monthly_expense': monthly_expense,
            'monthly_profit': monthly_profit,
        })

    return render(request, 'salary/list.html', context)

@role_required('admin')
def calculate_monthly_salary(request):
    if request.method == 'POST':
        month_str = request.POST.get('month')
        if not month_str:
            messages.error(request, 'Oyni tanlang')
            return redirect('salary:list')
        
        month = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
        
        # Calculate month end for overlap check
        last_day = calendar.monthrange(month.year, month.month)[1]
        month_end = month.replace(day=last_day)
        
        # ─── Step 1: Calculate Teacher Salaries ───
        teachers = User.objects.filter(role='teacher')
        for teacher in teachers:
            total_students = 0
            total_base = Decimal('0')
            total_salary = Decimal('0')
            teacher_pct = 0
            
            # Use overlap check: group must have been active during this month
            active_groups = Group.objects.filter(
                teacher=teacher,
                start_date__lte=month_end,
                end_date__gte=month
            )
            
            for g in active_groups:
                # Check for "Proof of Work" - at least one attendance record in this month
                if not Attendance.objects.filter(group=g, date__year=month.year, date__month=month.month).exists():
                    continue
                    
                count = Enrollment.objects.filter(group=g, status='approved').count()
                total_students += count
                group_revenue = g.course.price * Decimal(str(count))
                total_base += group_revenue
                total_salary += (group_revenue * Decimal(g.teacher_percent)) / Decimal('100')
                teacher_pct = g.teacher_percent
            
            # Clean up existing record for this month/user if it exists but is no longer active
            if total_students == 0 and total_salary == 0:
                Salary.objects.filter(user=teacher, month=month, is_paid=False).delete()
            else:
                Salary.objects.update_or_create(
                    user=teacher, month=month,
                    defaults={
                        'students_count': total_students,
                        'percent': teacher_pct,
                        'base_amount': total_base,
                        'total_amount': total_salary
                    }
                )
        
        # ─── Step 2: Calculate Assistant Salaries ───
        assistants = User.objects.filter(role='assistant')
        for assistant in assistants:
            total_students = 0
            total_base = Decimal('0')
            total_salary = Decimal('0')
            assistant_pct = 0
            
            # Use overlap check
            active_groups = Group.objects.filter(
                assistant=assistant,
                start_date__lte=month_end,
                end_date__gte=month
            )
            
            for g in active_groups:
                # Check for "Proof of Work"
                if not Attendance.objects.filter(group=g, date__year=month.year, date__month=month.month).exists():
                    continue
                    
                count = Enrollment.objects.filter(group=g, status='approved').count()
                total_students += count
                group_revenue = g.course.price * Decimal(str(count))
                total_base += group_revenue
                total_salary += (group_revenue * Decimal(g.assistant_percent)) / Decimal('100')
                assistant_pct = g.assistant_percent
                
            if total_students == 0 and total_salary == 0:
                Salary.objects.filter(user=assistant, month=month, is_paid=False).delete()
            else:
                Salary.objects.update_or_create(
                    user=assistant, month=month,
                    defaults={
                        'students_count': total_students,
                        'percent': assistant_pct,
                        'base_amount': total_base,
                        'total_amount': total_salary
                    }
                )
        
        messages.success(request, f"{month.strftime('%Y-%m')} uchun maoshlar avtomatik (guruh foizlari asosida) hisoblandi.")
        from django.urls import reverse
        return redirect(f"{reverse('salary:list')}?month={month_str}")
    return redirect('salary:list')


@role_required('admin')
def export_salary_pdf(request, month):
    try:
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from django.http import HttpResponse

        if month == "None":
            return HttpResponse("Oy ko'rsatilmadi", status=400)

        if len(month) == 7 and '-' in month:
            date_query = f"{month}-01"
        else:
            date_query = month
            
        salaries = Salary.objects.filter(month=date_query).select_related('user')
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="salary_{month}.pdf"'
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        
        elements = []
        
        styles = getSampleStyleSheet()
        title = Paragraph(f"<b>LMS Moliya Hisoboti</b> - {month}", styles['Heading1'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        data = [['Ism / Email', 'Rol', 'Talabalar', 'Summa UZS']]
        
        for s in salaries:
            name = s.user.get_full_name() if s.user.last_name else s.user.username
            data.append([
                name,
                s.user.role.upper(),
                str(s.students_count),
                f"{float(s.total_amount):,.0f}"
            ])
            
        t = Table(data, colWidths=[200, 100, 80, 120])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#095e45')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('TOPPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f9fafb')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d1d5db')),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('BOTTOMPADDING', (0,1), (-1,-1), 8),
            ('TOPPADDING', (0,1), (-1,-1), 8),
        ]))
        
        elements.append(t)
        doc.build(elements)
        
        pdf = buffer.getvalue()
        buffer.close()
        
        response.write(pdf)
        return response
    except Exception as e:
        import traceback
        from django.http import HttpResponse
        return HttpResponse(f"<pre>Error generating PDF: {str(e)}\n\n{traceback.format_exc()}</pre>", status=500)
