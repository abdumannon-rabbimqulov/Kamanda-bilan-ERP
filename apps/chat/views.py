from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.courses.models import Group, Enrollment
from apps.accounts.models import User

@login_required
def chat_room(request, room_name):
    user = request.user
    if user.role == 'student':
        groups = Group.objects.filter(enrollment__student=user, enrollment__status='approved')
        direct_users = User.objects.filter(role__in=['teacher', 'admin'])
    elif user.role == 'teacher':
        groups = Group.objects.filter(teacher=user)
        direct_users = User.objects.exclude(id=user.id)
    else:
        groups = Group.objects.all()
        direct_users = User.objects.exclude(id=user.id)
        
    return render(request, 'chat/room.html', {
        'room_name': room_name,
        'groups': groups,
        'direct_users': direct_users[:10]  # Just 10 for layout
    })
