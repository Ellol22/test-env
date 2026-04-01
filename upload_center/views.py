# upload_center/views.py
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from courses.models import Course
from .models import UploadFile
from .serializers import UploadFileSerializer
from accounts.models import Doctor, Student
from structure.models import CourseRegistration  # ✅ بدل StudentCourse


# =========================================================
# 1️⃣ دكتور يجيب مواده
# =========================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_courses_view(request):
    try:
        doctor = request.user.doctor
    except Doctor.DoesNotExist:
        return Response({"detail": "User is not a doctor."}, status=status.HTTP_403_FORBIDDEN)

    courses = Course.objects.filter(doctor=doctor)
    data = [{"id": c.id, "name": c.name} for c in courses]
    return Response(data)


# =========================================================
# 2️⃣ دكتور يرفع / يجيب / يحذف ملفات مادة
# =========================================================
@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def teacher_upload_file_view(request):
    try:
        doctor = request.user.doctor
    except Exception:
        return Response({"detail": "User is not a doctor."}, status=status.HTTP_403_FORBIDDEN)

    # ─── GET: جلب ملفات مادة ───────────────────────────────
    if request.method == 'GET':
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response({"detail": "Course ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        if course.doctor != doctor:
            return Response({"detail": "You are not allowed to view files for this course."}, status=status.HTTP_403_FORBIDDEN)

        files = UploadFile.objects.filter(course=course).order_by('-uploaded_at')
        data = [
            {
                'id': f.id,
                'file_url': f.file.url,
                'uploaded_at': f.uploaded_at,
                'uploaded_by': f.uploaded_by.username,
            }
            for f in files
        ]
        return Response(data, status=status.HTTP_200_OK)

    # ─── POST: رفع ملف ────────────────────────────────────
    elif request.method == 'POST':
        course_id = request.data.get('course')
        if not course_id:
            return Response({"detail": "Course ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        if course.doctor != doctor:
            return Response({"detail": "You are not allowed to upload to this course."}, status=status.HTTP_403_FORBIDDEN)

        serializer = UploadFileSerializer(data=request.data)
        if serializer.is_valid():
            upload_file = serializer.save(uploaded_by=request.user, course=course)
            return Response({
                'id': upload_file.id,
                'course': {'id': upload_file.course.id, 'name': upload_file.course.name},
                'file_url': upload_file.file.url,
                'uploaded_at': upload_file.uploaded_at,
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ─── DELETE: حذف ملف ──────────────────────────────────
    elif request.method == 'DELETE':
        file_id = request.query_params.get('file_id')
        if not file_id:
            return Response({"detail": "File ID is required to delete."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            file = UploadFile.objects.get(id=file_id)
        except UploadFile.DoesNotExist:
            return Response({"detail": "File not found."}, status=status.HTTP_404_NOT_FOUND)

        if file.course.doctor != doctor:
            return Response({"detail": "You are not allowed to delete this file."}, status=status.HTTP_403_FORBIDDEN)

        file.delete()
        return Response({"detail": "File deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


# =========================================================
# 3️⃣ طالب يجيب الكورسات (المواد) اللي مسجل فيها
# =========================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_courses_view(request):
    if not hasattr(request.user, 'student'):
        return Response({"detail": "User is not a student."}, status=status.HTTP_403_FORBIDDEN)

    student = request.user.student

    # ✅ بدل StudentCourse → CourseRegistration
    registrations = CourseRegistration.objects.filter(
        student=student
    ).select_related('course', 'structure', 'course__structure')

    data = {}

    for reg in registrations:
        course = reg.course

        year = course.structure.get_year_display() if course.structure else ""
        semester = course.get_semester_display()
        subject = course.name
        course_id = course.id

        key = (year, semester, subject, course_id)

        if key not in data:
            data[key] = []

        files = UploadFile.objects.filter(course=course)

        for file in files:
            if file.file and file.file.storage.exists(file.file.name):
                size_kb = str(file.file.size // 1024) + ' KB'
            else:
                size_kb = 'N/A'

            data[key].append({
                "id": file.id,
                "name": file.file.name.split('/')[-1],
                "type": "lecture",
                "size": size_kb,
                "date": file.uploaded_at.strftime("%Y-%m-%d"),
            })

    # بناء الرد
    response_data = {}

    for (year, semester, subject, course_id), files in data.items():
        if year not in response_data:
            response_data[year] = {"year": year, "semesters": {}}

        year_entry = response_data[year]

        if semester not in year_entry["semesters"]:
            year_entry["semesters"][semester] = {"semester": semester, "subjects": {}}

        semester_entry = year_entry["semesters"][semester]

        if subject not in semester_entry["subjects"]:
            semester_entry["subjects"][subject] = {
                "subject": subject,
                "course_id": course_id,
                "files": [],
            }

        semester_entry["subjects"][subject]["files"].extend(files)

    # تحويل لـ list
    final_response = []
    for year_data in response_data.values():
        semesters_list = []
        for semester_data in year_data["semesters"].values():
            semesters_list.append({
                "semester": semester_data["semester"],
                "subjects": list(semester_data["subjects"].values()),
            })
        final_response.append({
            "year": year_data["year"],
            "semesters": semesters_list,
        })

    return Response(final_response)


# =========================================================
# 4️⃣ طالب يجيب ملفات كورس معين
# =========================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_files_view(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return Response({"detail": "User is not a student."}, status=status.HTTP_403_FORBIDDEN)

    course_id = request.query_params.get('course_id')
    if not course_id:
        return Response({"detail": "course_id parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

    # ✅ تحقق من التسجيل عن طريق CourseRegistration
    is_enrolled = CourseRegistration.objects.filter(
        student=student,
        course_id=course_id
    ).exists()

    if not is_enrolled:
        return Response({"detail": "You are not enrolled in this course."}, status=status.HTTP_403_FORBIDDEN)

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

    files = UploadFile.objects.filter(course_id=course_id)
    files_serializer = UploadFileSerializer(files, many=True)

    return Response({
        'course': {'id': course.id, 'name': course.name},
        'files': files_serializer.data,
    })