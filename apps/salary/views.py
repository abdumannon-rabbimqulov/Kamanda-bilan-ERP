from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.accounts.decorators import role_required
from .models import Salary
from apps.accounts.models import User
from apps.courses.models import Course, Group, Enrollment
from datetime import datetime
from decimal import Decimal

@login_required
def salary_list(request):
    from django.db.models import Sum
    from datetime import datetime
    
    user = request.user
    salaries = Salary.objects.all().order_by('-month')
    
    # Filter by user if not admin
    if user.role != 'admin':
        salaries = salaries.filter(user=user)
        
    month_filter = request.GET.get('month')
    
    if month_filter and len(month_filter) == 7 and '-' in month_filter:
        date_query = f"{month_filter}-01"
        salaries = salaries.filter(month=date_query)
        try:
            latest_month = datetime.strptime(date_query, '%Y-%m-%d').date()
        except ValueError:
            latest_month = None
    else:
        latest_month = salaries.first().month if salaries.exists() else None
    
    context = {
        'salaries': salaries,
        'latest_month': latest_month,
        'filtered_month': month_filter,
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
        
        # ─── Step 1: Calculate Teacher Salaries ───
        teachers = User.objects.filter(role='teacher')
        for teacher in teachers:
            total_students = 0
            total_base = Decimal('0')
            total_salary = Decimal('0')
            teacher_pct = 0 # Will take from groups, assuming same for teacher usually but we calculate per group
            
            # Find all groups for this teacher
            groups = Group.objects.filter(teacher=teacher)
            for g in groups:
                count = Enrollment.objects.filter(group=g, status='approved').count()
                total_students += count
                # Expected revenue for this group
                group_revenue = g.course.price * Decimal(str(count))
                total_base += group_revenue
                # Share for this group
                total_salary += (group_revenue * Decimal(g.teacher_percent)) / Decimal('100')
                teacher_pct = g.teacher_percent # Just for display in the model
            
            if total_students > 0 or total_salary > 0:
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
            
            groups = Group.objects.filter(assistant=assistant)
            for g in groups:
                count = Enrollment.objects.filter(group=g, status='approved').count()
                total_students += count
                group_revenue = g.course.price * Decimal(str(count))
                total_base += group_revenue
                total_salary += (group_revenue * Decimal(g.assistant_percent)) / Decimal('100')
                assistant_pct = g.assistant_percent
                
            if total_students > 0 or total_salary > 0:
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
