from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Group, Lesson
from datetime import timedelta

# @receiver(post_save, sender=Group)
# def create_group_lessons(sender, instance, created, **kwargs):
#     if created:
#         start_date = instance.start_date
#         ...
# (Logic moved to views_dashboard.py to handle more schedule types)
