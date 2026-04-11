from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max, Value
from django.db.models.functions import Coalesce, Greatest
import datetime
from django.contrib import messages

from apps.courses.models import Group, Enrollment
from apps.accounts.models import User
from .models import Message

def get_chat_context(user):
    """Helper to get sidebar groups and contacts based on user role"""
    # Previously limited, now everyone can message everyone
    if user.role == 'student':
        groups = Group.objects.filter(enrollment__student=user, enrollment__status='approved')
    elif user.role == 'teacher':
        groups = Group.objects.filter(teacher=user)
    elif user.role == 'assistant':
        groups = Group.objects.filter(assistant=user)
    else: # Admin
        groups = Group.objects.all()
    # Smart sorting for contacts: people you messaged recently appear first
    epoch = datetime.datetime(1900, 1, 1)
    contacts = User.objects.exclude(id=user.id).annotate(
        last_sent=Max('sent_messages__created_at', filter=Q(sent_messages__receiver=user)),
        last_received=Max('received_messages__created_at', filter=Q(received_messages__sender=user))
    ).annotate(
        latest_activity=Greatest(
            Coalesce('last_sent', Value(epoch)),
            Coalesce('last_received', Value(epoch))
        )
    ).order_by('-latest_activity', 'role', 'first_name', 'username')

    return groups, contacts

@login_required
def chat_list(request):
    groups, contacts = get_chat_context(request.user)
    return render(request, 'chat/room.html', {
        'groups': groups,
        'contacts': contacts,
        'mode': 'list'
    })

@login_required
def chat_direct(request, user_id):
    me = request.user
    other = get_object_or_404(User, id=user_id)
    
    # History
    history = Message.objects.filter(
        Q(sender=me, receiver=other) | Q(sender=other, receiver=me),
        msg_type='direct'
    ).order_by('created_at')
    
    # Mark as read
    Message.objects.filter(sender=other, receiver=me, is_read=False).update(is_read=True)
    
    groups, contacts = get_chat_context(me)

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
    
    # Security check
    can_access = False
    if me.role == 'admin': can_access = True
    elif me.role == 'teacher' and group.teacher == me: can_access = True
    elif me.role == 'assistant' and group.assistant == me: can_access = True
    elif me.role == 'student' and Enrollment.objects.filter(group=group, student=me, status='approved').exists(): can_access = True
    
    if not can_access:
        messages.error(request, "Kirish cheklangan.")
        return redirect('chat:list')

    history = Message.objects.filter(group=group, msg_type='group').order_by('created_at')
    
    # Mark group messages as read (excluding those sent by self)
    Message.objects.filter(group=group, is_read=False).exclude(sender=me).update(is_read=True)
    
    groups, contacts = get_chat_context(me)

    return render(request, 'chat/room.html', {
        'groups': groups,
        'contacts': contacts,
        'chat_group': group,
        'history': history,
        'mode': 'group'
    })
