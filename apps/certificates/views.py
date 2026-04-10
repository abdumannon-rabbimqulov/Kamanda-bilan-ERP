from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.accounts.decorators import role_required
from .utils import generate_certificate
from apps.accounts.models import User
from apps.courses.models import Course

@role_required('admin')
def issue_certificate(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        course_id = request.POST.get('course_id')
        student = get_object_or_404(User, id=student_id)
        course = get_object_or_404(Course, id=course_id)
        generate_certificate(student, course)
        messages.success(request, 'Sertifikat yaratildi, uni hozir yuklab olsangiz bo\'ladi.')
        return redirect('dashboard:admin')
    students = User.objects.filter(role='student')
    courses = Course.objects.filter(is_active=True)
    return render(request, 'certificates/issue.html', {'students': students, 'courses': courses})

def verify_certificate(request, code):
    from apps.certificates.models import Certificate
    cert = get_object_or_404(Certificate, verification_code=code)
    
    # We deduce admin from the system (mock or first admin)
    admin_user = User.objects.filter(role='admin').first()
    
    return render(request, 'certificates/verify.html', {'cert': cert, 'admin': admin_user})
