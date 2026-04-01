# 📁 dashboard/urls.py

from django.urls import path
from .views import (
    personal_info,
    announcement_api,
    send_notification,
    student_notifications,
)

urlpatterns = [
    # 👤 Personal Info
    path('pers-info/', personal_info, name='pers-info'),

    # 📢 Announcements
    path('announcements/', announcement_api, name='announcements'),
    path('announcements/<int:id>/', announcement_api, name='announcement-detail'),

    # 🔔 Notifications — Doctor
    path('notification/', send_notification, name='notification-list'),
    path('notification/<int:id>/', send_notification, name='notification-detail'),

    # 🔔 Notifications — Student
    path('notification/student/', student_notifications, name='student-notifications'),
]
# /grades/doctor_courses/   اقولهم يجيبو المواد من الاند بوينت دي عشان الدكتور يبعت نوتفيكيشن