from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages

from apps.courses.models import Group, Enrollment
from apps.accounts.models import User
from .models import Message

@login_required
def chat_list(request):
    user = request.user
    if user.role == 'student':
        groups = Group.objects.filter(enrollment__student=user, enrollment__status='approved')
        contacts = User.objects.filter(role__in=['teacher', 'admin', 'assistant']).distinct()
    elif user.role == 'teacher':
        groups = Group.objects.filter(teacher=user)
        contacts = User.objects.exclude(id=user.id)
    elif user.role == 'assistant':
        groups = Group.objects.filter(assistant=user)
        contacts = User.objects.exclude(id=user.id)
    else: # Admin
        groups = Group.objects.all()
        contacts = User.objects.exclude(id=user.id)
        
    return render(request, 'chat/room.html', {
        'groups': groups,
        'contacts': contacts,
        'mode': 'list'
    })

@login_required
def chat_direct(request, user_id):
    me = request.user
    other = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(sender=me, receiver=other, content=content, msg_type='direct')
            return redirect('chat:direct', user_id=other.id)

    # History
    history = Message.objects.filter(
        Q(sender=me, receiver=other) | Q(sender=other, receiver=me),
        msg_type='direct'
    ).order_by('created_at')
    
    # Context same as list + detail
    if me.role == 'student':
        groups = Group.objects.filter(enrollment__student=me, enrollment__status='approved')
        contacts = User.objects.filter(role__in=['teacher', 'admin', 'assistant']).distinct()
    elif me.role == 'teacher':
        groups = Group.objects.filter(teacher=me)
        contacts = User.objects.exclude(id=me.id)
    else:
        groups = Group.objects.all()
        contacts = User.objects.exclude(id=me.id)

    return render(request, 'chat/room.html', {
        'groups': groups,
        'contacts': contacts,
        'chat_partner': other,
        'history': history,
        'mode': 'direct'
    })

@login_required
def chat_group(request, group_id):
    me = request.user
    group = get_object_or_404(Group, id=group_id)
    
    # Security check - ensure user is in group
    can_access = False
    if me.role == 'admin': can_access = True
    elif me.role == 'teacher' and group.teacher == me: can_access = True
    elif me.role == 'assistant' and group.assistant == me: can_access = True
    elif me.role == 'student' and Enrollment.objects.filter(group=group, student=me, status='approved').exists(): can_access = True
    
    if not can_access:
        messages.error(request, "Ushbu guruh chatiga kirishga ruxsatingiz yo'q.")
        return redirect('chat:index')

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(sender=me, group=group, content=content, msg_type='group')
            return redirect('chat:group', group_id=group.id)

    history = Message.objects.filter(group=group, msg_type='group').order_by('created_at')

    # Sidebar context
    if me.role == 'student':
        groups = Group.objects.filter(enrollment__student=me, enrollment__status='approved')
        contacts = User.objects.filter(role__in=['teacher', 'admin', 'assistant']).distinct()
    elif me.role == 'teacher':
        groups = Group.objects.filter(teacher=me)
        contacts = User.objects.exclude(id=me.id)
    else:
        groups = Group.objects.all()
        contacts = User.objects.exclude(id=me.id)

    return render(request, 'chat/room.html', {
        'groups': groups,
        'contacts': contacts,
        'chat_group': group,
        'history': history,
        'mode': 'group'
    })
