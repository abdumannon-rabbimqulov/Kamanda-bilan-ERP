import random
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from apps.accounts.models import User

def login_view(request):
    if request.method == 'POST':
        login_input = request.POST.get('login')
        password = request.POST.get('password')
        user = authenticate(request, username=login_input, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard:home')
        return render(request, 'accounts/login.html', {'error': "Login yoki parol xato"})
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('auth:login')

