# 📁 dashboard/views.py

import json

from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response

from accounts.models import Student, Doctor, DoctorRole
from .models import Dash, Announcement, Notifications
from .serializers import (
    StudentSerializer,
    DoctorSerializer,
    AnnouncementSerializer,
    NotificationSerializer,
)


# =========================================================
# 👤 Personal Info
# GET  /dashboard/pers-info/  → بيانات الطالب أو الدكتور
# POST /dashboard/pers-info/  → رفع صورة
# =========================================================

@csrf_exempt
@api_view(['GET', 'POST', 'OPTIONS'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, JSONParser])
def personal_info(request):
    if request.method == 'OPTIONS':
        response = Response(status=204)
        response["Access-Control-Allow-Origin"]  = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response["Access-Control-Max-Age"]       = "86400"
        return response

    try:
        user = request.user
        profile_type     = None
        profile_instance = None

        try:
            profile_instance = Student.objects.get(user=user)
            profile_type = 'student'
        except Student.DoesNotExist:
            pass

        if profile_instance is None:
            try:
                profile_instance = Doctor.objects.get(user=user)
                profile_type = 'doctor'
            except Doctor.DoesNotExist:
                pass

        if profile_instance is None:
            return Response({'error': 'Profile not found'}, status=404)

        # ── GET ──────────────────────────────────────────
        if request.method == 'GET':
            if profile_type == 'student':
                student    = profile_instance
                serializer = StudentSerializer(student)
                data = {
                    'photo':      serializer.data.get('image'),
                    'name':       serializer.data.get('name'),
                    'studentId':  serializer.data.get('national_id'),
                    'department': (
                        student.current_structure.get_department_display()
                        if student.current_structure else None
                    ),
                    'email': serializer.data.get('email'),
                    'phone': serializer.data.get('mobile'),
                }
            else:
                serializer = DoctorSerializer(profile_instance)
                data = {
                    'photo':       serializer.data.get('image'),
                    'name':        serializer.data.get('name'),
                    'national_id': serializer.data.get('national_id'),
                    'departments': serializer.data.get('departments', []),
                    'email':       serializer.data.get('email'),
                    'phone':       serializer.data.get('mobile'),
                    'courses':     serializer.data.get('courses', []),
                }
            return Response(data)

        # ── POST (رفع صورة) ───────────────────────────────
        elif request.method == 'POST':
            if profile_type == 'student':
                dash, _ = Dash.objects.get_or_create(student=profile_instance)
            else:
                dash, _ = Dash.objects.get_or_create(doctor=profile_instance)

            uploaded_image = request.FILES.get('photo') or request.FILES.get('image')
            if not uploaded_image:
                return Response({'error': 'No image provided'}, status=400)

            if dash.image and dash.image.name:
                dash.image.delete(save=False)

            dash.image = uploaded_image
            dash.save()
            return Response({'message': 'Image uploaded successfully'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({'error': 'An unexpected error occurred'}, status=500)


# =========================================================
# 📢 Announcements
# GET    /dashboard/announcements/       → كل الإعلانات (الكل يشوف)
# GET    /dashboard/announcements/<id>/  → إعلان واحد
# POST   /dashboard/announcements/       → إنشاء (دكاترة فقط، مش معيد)
# PUT    /dashboard/announcements/<id>/  → تعديل (صاحب الإعلان بس)
# DELETE /dashboard/announcements/<id>/  → حذف (صاحب الإعلان بس)
# =========================================================

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def announcement_api(request, id=None):

    # ── GET (متاح للكل) ───────────────────────────────────
    if request.method == 'GET':
        if id is not None:
            announcement = get_object_or_404(Announcement, id=id)
            return Response(AnnouncementSerializer(announcement).data)
        announcements = Announcement.objects.all().order_by('-created_at')
        return Response(AnnouncementSerializer(announcements, many=True).data)

    # ── باقي الـ methods للدكاترة فقط ────────────────────
    try:
        doctor = request.user.doctor
    except AttributeError:
        return Response({"detail": "Only doctors can perform this action."}, status=403)

    if doctor.role == DoctorRole.TEACHING_ASSISTANT:
        return Response({"detail": "Teaching assistants can only view announcements."}, status=403)

    # ── POST (إنشاء) ──────────────────────────────────────
    if request.method == 'POST':
        data = request.data.copy() if isinstance(request.data, dict) else json.loads(request.data)
        serializer = AnnouncementSerializer(data=data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    # ── PUT (تعديل — صاحب الإعلان بس) ────────────────────
    elif request.method == 'PUT':
        if not id:
            return Response({"detail": "ID is required for update."}, status=400)
        # get_object_or_404 بيتأكد إن الإعلان ده بتاع اليوزر ده بالظبط
        announcement = get_object_or_404(Announcement, id=id, created_by=request.user)
        data = request.data.copy() if isinstance(request.data, dict) else json.loads(request.data)
        serializer = AnnouncementSerializer(announcement, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    # ── DELETE (حذف — صاحب الإعلان بس) ───────────────────
    elif request.method == 'DELETE':
        if not id:
            return Response({"detail": "ID is required for deletion."}, status=400)
        announcement = get_object_or_404(Announcement, id=id, created_by=request.user)
        announcement.delete()
        return Response({'message': 'Deleted successfully.'})


# =========================================================
# 🔔 Notifications — Doctor
# GET    /dashboard/notification/       → كل نوتفكيشناته
# GET    /dashboard/notification/<id>/  → نوتفكيشن واحدة
# POST   /dashboard/notification/       → إرسال نوتفكيشن
# PUT    /dashboard/notification/<id>/  → تعديل
# DELETE /dashboard/notification/<id>/  → حذف
# =========================================================

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def send_notification(request, id=None):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return Response({'detail': 'Current user is not a Doctor.'}, status=403)

    # ── GET ───────────────────────────────────────────────
    if request.method == 'GET':
        if id is not None:
            notification = get_object_or_404(Notifications, id=id, sender=doctor)
            return Response(NotificationSerializer(notification).data)
        notifications = Notifications.objects.filter(sender=doctor).order_by('-created_at')
        return Response(NotificationSerializer(notifications, many=True).data)

    # ── POST ──────────────────────────────────────────────
    if request.method == 'POST':
        data = request.data.copy() if isinstance(request.data, dict) else json.loads(request.data)
        data.pop('sender', None)

        course_id = data.get('course_id')
        if not course_id:
            return Response({'detail': 'course_id is required.'}, status=400)

        # تأكد إن المادة دي بتاعت الدكتور ده عن طريق GradeSheet
        from grades.models import GradeSheet
        from courses.models import Course
        try:
            course = Course.objects.get(id=course_id)
            if not GradeSheet.objects.filter(course=course, doctor=doctor).exists():
                return Response(
                    {'detail': 'You are not authorized to send notifications for this course.'},
                    status=403
                )
        except Course.DoesNotExist:
            return Response({'detail': 'Course not found.'}, status=400)

        serializer = NotificationSerializer(data=data)
        if serializer.is_valid():
            serializer.save(sender=doctor)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    # ── PUT ───────────────────────────────────────────────
    if request.method == 'PUT':
        if not id:
            return Response({'detail': 'Notification ID required in URL.'}, status=400)
        notification = get_object_or_404(Notifications, id=id, sender=doctor)
        data = request.data.copy() if isinstance(request.data, dict) else json.loads(request.data)
        data.pop('sender', None)

        # تأكد من الـ authorization لو بدّل المادة
        from grades.models import GradeSheet
        from courses.models import Course
        course_id = data.get('course_id', notification.course.id)
        try:
            course = Course.objects.get(id=course_id)
            if not GradeSheet.objects.filter(course=course, doctor=doctor).exists():
                return Response(
                    {'detail': 'You are not authorized to send notifications for this course.'},
                    status=403
                )
        except Course.DoesNotExist:
            return Response({'detail': 'Invalid course ID.'}, status=400)

        serializer = NotificationSerializer(notification, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    # ── DELETE ────────────────────────────────────────────
    if request.method == 'DELETE':
        if not id:
            return Response({'detail': 'Notification ID required in URL.'}, status=400)
        notification = get_object_or_404(Notifications, id=id, sender=doctor)
        notification.delete()
        return Response({'detail': 'Notification deleted successfully.'})


# =========================================================
# 🔔 Notifications — Student
# GET /dashboard/notification/student/
#
# بيجيب النوتفكيشنات بتاعت كل المواد اللي الطالب مسجل فيها:
#   - CourseRegistration      (المواد العادية)
#   - SummerCourseRegistration
#   - RepeatCourseRegistration
#   - CarryCourse
# =========================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_notifications(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'detail': 'Current user is not a student.'}, status=403)

    from structure.models import (
        CourseRegistration,
        SummerCourseRegistration,
        RepeatCourseRegistration,
        CarryCourse,
    )

    # جمع كل الـ course IDs من كل الجداول
    regular_ids = CourseRegistration.objects.filter(
        student=student
    ).values_list('course_id', flat=True)

    summer_ids = SummerCourseRegistration.objects.filter(
        student=student
    ).values_list('course_id', flat=True)

    repeat_ids = RepeatCourseRegistration.objects.filter(
        student=student
    ).values_list('course_id', flat=True)

    carry_ids = CarryCourse.objects.filter(
        student=student
    ).values_list('course_id', flat=True)

    # دمج كل الـ IDs في set واحد (بدون تكرار)
    all_course_ids = set(regular_ids) | set(summer_ids) | set(repeat_ids) | set(carry_ids)

    # جيب النوتفكيشنات المرتبطة بأي مادة من دول
    notifications = Notifications.objects.filter(
        course_id__in=all_course_ids
    ).order_by('-created_at')

    return Response(NotificationSerializer(notifications, many=True).data)