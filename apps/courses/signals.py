from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Group, Lesson
from datetime import timedelta

@receiver(post_save, sender=Group)
def create_group_lessons(sender, instance, created, **kwargs):
    if created:
        start_date = instance.start_date
        end_date = instance.end_date
        curr_date = start_date
        
        # Mapping schedule types to weekday numbers (Monday=0, Sunday=6)
        if instance.schedule_type == '3_days':
            allowed_weekdays = [0, 2, 4] # Mon, Wed, Fri
        elif instance.schedule_type == '5_days':
            allowed_weekdays = [0, 1, 2, 3, 4] # Mon-Fri
        else: # daily
            allowed_weekdays = [0, 1, 2, 3, 4, 5] # Mon-Sat
            
        order = 1
        while curr_date <= end_date:
            if curr_date.weekday() in allowed_weekdays:
                Lesson.objects.create(
                    group=instance,
                    title=f"{order}-dars",
                    date=curr_date,
                    order=order,
                    lesson_type='text'
                )
                order += 1
            curr_date += timedelta(days=1)
