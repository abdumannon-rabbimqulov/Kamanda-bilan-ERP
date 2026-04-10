from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='index'),
    path('admin/', admin.site.urls),
    path('auth/', include('apps.accounts.urls', namespace='auth')),
    path('dashboard/', include('apps.accounts.urls_dashboard', namespace='dashboard')),
    path('courses/', include('apps.courses.urls', namespace='courses')),
    path('homework/', include('apps.homework.urls', namespace='homework')),
    path('attendance/', include('apps.attendance.urls', namespace='attendance')),
    path('exams/', include('apps.exams.urls', namespace='exams')),
    path('chat/', include('apps.chat.urls', namespace='chat')),
    path('salary/', include('apps.salary.urls', namespace='salary')),
    path('certificates/', include('apps.certificates.urls', namespace='certificates')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('complaints/', include('apps.complaints.urls', namespace='complaints')),
    path('payments/', include('apps.payments.urls', namespace='payments')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
