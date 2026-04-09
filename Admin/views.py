import random
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .models import CustomUser, Course, Group

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')

        if not (username and email and password and role):
            return render(request, 'register.html', {'error': "Barcha maydonlarni to'ldiring."})
        
        if CustomUser.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': "Bu username allaqachon band."})
            
        if CustomUser.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': "Bu email orqali ro'yxatdan o'tilgan."})

        # Xavfsiz 6 xonali OTP kod yaratish
        otp_code = str(random.randint(100000, 999999))
        
        user = CustomUser.objects.create_user(
            username=username, 
            email=email, 
            password=password, 
            role=role, 
            is_active=False,
            otp_code=otp_code
        )
        
        try:
            send_mail(
                subject='LMS Tasdiqlash Kodi',
                message=f'Xush kelibsiz! Sizning tasdiqlash kodingiz: {otp_code}',
                from_email='admin@lms-platform.uz',
                recipient_list=[email],
                fail_silently=False,
            )
            request.session['verification_email'] = email
            return redirect('verify_email')
        except Exception as e:
            return render(request, 'register.html', {'error': "Email jo'natishda xatolik yuz berdi."})

    return render(request, 'register.html')


def verify_email_view(request):
    email = request.session.get('verification_email')
    
    if not email:
        return redirect('register')
        
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            user = CustomUser.objects.get(email=email, otp_code=code)
            
            user.is_active = True
            user.is_verified = True
            user.otp_code = None
            user.save()
            
            login(request, user)
            del request.session['verification_email']
            
            return redirect('dashboard')
        except CustomUser.DoesNotExist:
            return render(request, 'verify_email.html', {'error': 'Tasdiqlash kodi xato!'})
            
    return render(request, 'verify_email.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('dashboard')
            else:
                request.session['verification_email'] = user.email
                if user.otp_code is None:
                    user.otp_code = str(random.randint(100000, 999999))
                    user.save()
                return redirect('verify_email')
        else:
            return render(request, 'login.html', {'error': 'Username yoki parol xato.'})
            
    return render(request, 'login.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard_view(request):
    user = request.user
    context = {'user': user}
    
    if user.role == 'student':
        context['groups'] = user.enrolled_groups.all()
    elif user.role == 'teacher':
        context['groups'] = user.teaching_groups.all()
    elif user.role == 'assistant':
        context['groups'] = user.assisting_groups.all()
    elif user.role == 'admin':
        context['stats'] = {
            'students_count': CustomUser.objects.filter(role='student').count(),
            'teachers_count': CustomUser.objects.filter(role='teacher').count(),
            'courses_count': Course.objects.count()
        }
    
    return render(request, 'dashboard.html', context)
