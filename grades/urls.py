# 📁 grades/urls.py

from django.urls import path
from grades import views

urlpatterns = [
    # 👨‍🎓 درجات الطالب
    path('student/', views.my_grades, name='my_grades'),

    # 📋 كل مواد الدكتور (regular + summer + repeat + carry)
    path('doctor_courses/', views.doctor_courses, name='doctor_courses'),

    # 📝 إدارة درجات مادة معينة
    # ?type=regular (default) | summer | repeat | carry
    path('doctor/<int:course_id>/', views.manage_course_grades, name='doctor_grades'),

    # 📊 إحصائيات
    path('doctor-statistics/', views.doctor_courses_statistics, name='doctor-statistics'),

    # 📤 رفع ملف Excel
    path('doctor/<int:course_id>/upload/', views.import_grades_api, name='import_grades_api'),
]