# 📁 grades/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
import pandas as pd

from grades.models import GradeSheet, StudentGrade
from courses.models import Course
from accounts.models import Student, Doctor
from structure.models import (
    SummerCourseRegistration,
    RepeatCourseRegistration,
    CarryCourse,
)
from grades.serializers import (
    StudentGradeSerializer,
    SummerGradeSerializer,
    RepeatGradeSerializer,
    CarryGradeSerializer,
)


# =========================================================
# 🔧 Helpers
# =========================================================

def is_doctor(user):
    return hasattr(user, 'doctor')

def is_student(user):
    return hasattr(user, 'student')

def get_doctor(user):
    try:
        return user.doctor
    except AttributeError:
        return None


# =========================================================
# 👨‍🎓 درجات الطالب من كل الجداول
# GET /grades/student/
#
# Response:
# {
#   "regular": [...],
#   "summer":  [...],
#   "repeat":  [...],
#   "carry":   [...]
# }
# =========================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_grades(request):
    if not is_student(request.user):
        return Response(
            {"detail": "You do not have permission to view grades."},
            status=status.HTTP_403_FORBIDDEN
        )

    student = request.user.student

    # ── المواد العادية ────────────────────────────────────
    regular_grades = StudentGrade.objects.filter(
        student=student
    ).select_related('grade_sheet__course__structure')
    regular_data = StudentGradeSerializer(regular_grades, many=True).data

    # ── مواد السمر ────────────────────────────────────────
    summer_regs = SummerCourseRegistration.objects.filter(
        student=student
    ).select_related('course', 'student__user')
    summer_data = SummerGradeSerializer(summer_regs, many=True).data

    # ── مواد إعادة السنة ──────────────────────────────────
    repeat_regs = RepeatCourseRegistration.objects.filter(
        student=student
    ).select_related('course', 'student__user')
    repeat_data = RepeatGradeSerializer(repeat_regs, many=True).data

    # ── المواد المترحلة ───────────────────────────────────
    carry_regs = CarryCourse.objects.filter(
        student=student
    ).select_related('course', 'student__user', 'from_structure', 'to_structure')
    carry_data = CarryGradeSerializer(carry_regs, many=True).data

    return Response({
        "regular": regular_data,
        "summer":  summer_data,
        "repeat":  repeat_data,
        "carry":   carry_data,
    })


# =========================================================
# 📋 مواد الدكتور
# GET /grades/doctor_courses/
# =========================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_courses(request):
    doctor = get_doctor(request.user)
    if not doctor:
        return Response(
            {"detail": "You do not have access permission."},
            status=status.HTTP_403_FORBIDDEN
        )

    # ── المواد العادية ────────────────────────────────────
    regular_sheets = GradeSheet.objects.filter(
        doctor=doctor
    ).select_related('course__structure')

    regular = [
        {
            "id":        sheet.course.id,
            "name":      sheet.course.name,
            "type":      "regular",
            "is_summer": sheet.is_summer,
            "structure": (
                f"{sheet.course.structure.get_department_display()} - "
                f"{sheet.course.structure.get_year_display()}"
            ) if sheet.course.structure else None,
        }
        for sheet in regular_sheets
    ]

    # ── مواد السمر (بدون distinct عشان SQLite) ───────────
    seen_summer = set()
    summer = []
    for reg in SummerCourseRegistration.objects.filter(
        course__main_grade_sheet__doctor=doctor
    ).select_related('course'):
        if reg.course_id not in seen_summer:
            seen_summer.add(reg.course_id)
            summer.append({
                "course_id":    reg.course.id,
                "name":         reg.course.name,
                "type":         "summer",
                "is_evaluated": reg.is_evaluated,
            })

    # ── مواد إعادة السنة ──────────────────────────────────
    seen_repeat = set()
    repeat = []
    for reg in RepeatCourseRegistration.objects.filter(
        course__main_grade_sheet__doctor=doctor
    ).select_related('course'):
        if reg.course_id not in seen_repeat:
            seen_repeat.add(reg.course_id)
            repeat.append({
                "course_id":    reg.course.id,
                "name":         reg.course.name,
                "type":         "repeat",
                "is_evaluated": reg.is_evaluated,
            })

    # ── المواد المترحلة ───────────────────────────────────
    seen_carry = set()
    carry = []
    for reg in CarryCourse.objects.filter(
        course__main_grade_sheet__doctor=doctor
    ).select_related('course'):
        if reg.course_id not in seen_carry:
            seen_carry.add(reg.course_id)
            carry.append({
                "course_id":    reg.course.id,
                "name":         reg.course.name,
                "type":         "carry",
                "is_evaluated": reg.is_evaluated,
            })

    return Response({
        "regular": regular,
        "summer":  summer,
        "repeat":  repeat,
        "carry":   carry,
    })


# =========================================================
# 📝 إدارة درجات مادة معينة
# GET  /grades/doctor/<course_id>/?type=regular|summer|repeat|carry
# PATCH /grades/doctor/<course_id>/?type=regular|summer|repeat|carry
# =========================================================

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def manage_course_grades(request, course_id):
    doctor = get_doctor(request.user)
    if not doctor:
        return Response(
            {"detail": "Only doctors are allowed to access this endpoint."},
            status=status.HTTP_403_FORBIDDEN
        )

    course_type = request.query_params.get('type', 'regular')

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        grade_sheet = GradeSheet.objects.get(course=course)
    except GradeSheet.DoesNotExist:
        return Response({"detail": "No grade sheet for this course."}, status=status.HTTP_404_NOT_FOUND)

    if grade_sheet.doctor != doctor:
        return Response(
            {"detail": "Course not assigned to you."},
            status=status.HTTP_403_FORBIDDEN
        )

    # ── regular ───────────────────────────────────────────
    if course_type == 'regular':
        if request.method == 'GET':
            grades = StudentGrade.objects.filter(
                grade_sheet=grade_sheet
            ).select_related('student__user')
            return Response({
                'grade_sheet': {
                    'full_score':              grade_sheet.full_score,
                    'final_exam_full_score':   grade_sheet.final_exam_full_score,
                    'midterm_full_score':      grade_sheet.midterm_full_score,
                    'section_exam_full_score': grade_sheet.section_exam_full_score,
                    'year_work_full_score':    grade_sheet.year_work_full_score,
                },
                'student_grades': StudentGradeSerializer(grades, many=True).data,
            })

        elif request.method == 'PATCH':
            data = request.data
            if data.get('update_gradesheet'):
                for field in ['full_score', 'final_exam_full_score', 'midterm_full_score',
                               'section_exam_full_score', 'year_work_full_score']:
                    if field in data:
                        setattr(grade_sheet, field, data[field])
                try:
                    grade_sheet.save()
                    return Response({"detail": "Grade sheet updated successfully."})
                except ValidationError as e:
                    return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            student_id = data.get('student_id')
            if not student_id:
                return Response(
                    {"detail": "Field 'student_id' is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                student = Student.objects.get(student_id=student_id)
            except Student.DoesNotExist:
                return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

            grade, _ = StudentGrade.objects.get_or_create(grade_sheet=grade_sheet, student=student)
            serializer = StudentGradeSerializer(grade, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ── summer ────────────────────────────────────────────
    elif course_type == 'summer':
        regs = SummerCourseRegistration.objects.filter(
            course=course
        ).select_related('student__user')

        if request.method == 'GET':
            return Response({
                'final_exam_full_score': grade_sheet.final_exam_full_score,
                'student_grades': SummerGradeSerializer(regs, many=True).data,
            })

        elif request.method == 'PATCH':
            reg_id = request.data.get('registration_id')
            if not reg_id:
                return Response(
                    {"detail": "Field 'registration_id' is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                reg = regs.get(id=reg_id)
            except SummerCourseRegistration.DoesNotExist:
                return Response({"detail": "Registration not found."}, status=status.HTTP_404_NOT_FOUND)

            serializer = SummerGradeSerializer(reg, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ── repeat ────────────────────────────────────────────
    elif course_type == 'repeat':
        regs = RepeatCourseRegistration.objects.filter(
            course=course
        ).select_related('student__user')

        if request.method == 'GET':
            return Response({
                'final_exam_full_score': grade_sheet.final_exam_full_score,
                'student_grades': RepeatGradeSerializer(regs, many=True).data,
            })

        elif request.method == 'PATCH':
            reg_id = request.data.get('registration_id')
            if not reg_id:
                return Response(
                    {"detail": "Field 'registration_id' is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                reg = regs.get(id=reg_id)
            except RepeatCourseRegistration.DoesNotExist:
                return Response({"detail": "Registration not found."}, status=status.HTTP_404_NOT_FOUND)

            serializer = RepeatGradeSerializer(reg, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ── carry ─────────────────────────────────────────────
    elif course_type == 'carry':
        regs = CarryCourse.objects.filter(
            course=course
        ).select_related('student__user', 'from_structure', 'to_structure')

        if request.method == 'GET':
            return Response({
                'final_exam_full_score': grade_sheet.final_exam_full_score,
                'student_grades': CarryGradeSerializer(regs, many=True).data,
            })

        elif request.method == 'PATCH':
            reg_id = request.data.get('registration_id')
            if not reg_id:
                return Response(
                    {"detail": "Field 'registration_id' is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                reg = regs.get(id=reg_id)
            except CarryCourse.DoesNotExist:
                return Response({"detail": "Registration not found."}, status=status.HTTP_404_NOT_FOUND)

            serializer = CarryGradeSerializer(reg, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    else:
        return Response(
            {"detail": "Invalid type. Use: regular | summer | repeat | carry"},
            status=status.HTTP_400_BAD_REQUEST
        )


# =========================================================
# 📊 إحصائيات مواد الدكتور
# GET /grades/doctor-statistics/
# =========================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_courses_statistics(request):
    doctor = get_doctor(request.user)
    if not doctor:
        return Response({'detail': 'أنت مش دكتور'}, status=status.HTTP_403_FORBIDDEN)

    statistics = []
    sheets = GradeSheet.objects.filter(doctor=doctor).select_related('course__structure')

    for sheet in sheets:
        course = sheet.course
        struct = course.structure
        grades = sheet.student_grades.all()

        statistics.append({
            "course_id":   course.id,
            "course_name": course.name,
            "structure": (
                f"{struct.get_department_display()} - {struct.get_year_display()}"
                if struct else None
            ),
            "passed": grades.filter(is_passed=True).count(),
            "failed": grades.filter(is_passed=False).count(),
            "total":  grades.count(),
        })

    return Response(statistics)


# =========================================================
# 📤 رفع درجات بملف Excel لكل الجداول
# POST /grades/doctor/<course_id>/upload/?type=regular|summer|repeat|carry
#
# أعمدة الإكسل:
#   regular → ID, Name, Midterm, SectionExam, YearWork, FinalExam
#   summer  → ID, Name, FinalExam
#   repeat  → ID, Name, FinalExam
#   carry   → ID, Name, FinalExam
# =========================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_grades_api(request, course_id):
    doctor = get_doctor(request.user)
    if not doctor:
        return Response({'detail': 'أنت مش دكتور'}, status=status.HTTP_403_FORBIDDEN)

    excel_file = request.FILES.get('file')
    if not excel_file:
        return Response({'detail': 'ملف الإكسل مطلوب'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        grade_sheet = GradeSheet.objects.get(course_id=course_id)
    except GradeSheet.DoesNotExist:
        return Response({'detail': 'GradeSheet غير موجود'}, status=status.HTTP_404_NOT_FOUND)

    if grade_sheet.doctor != doctor:
        return Response(
            {'detail': 'مش مصرح لك ترفع الدرجات على المادة دي'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        return Response(
            {'detail': f'خطأ في قراءة ملف الإكسل: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    course_type = request.query_params.get('type', 'regular')

    def parse_score(val):
        if pd.isna(val):
            return 0
        if isinstance(val, str) and '/' in val:
            return float(val.split('/')[0])
        try:
            return float(val)
        except Exception:
            return 0

    def find_student(row, idx, errors):
        sid = row.get('ID')
        if pd.notna(sid) and str(sid) != 'N/A':
            try:
                return Student.objects.get(student_id=str(sid).strip())
            except Student.DoesNotExist:
                pass
        name = row.get('Name')
        if pd.notna(name):
            qs = Student.objects.filter(name__iexact=str(name).strip())
            if qs.exists():
                return qs.first()
        errors.append(f"الصف {idx + 1}: لم يتم العثور على الطالب")
        return None

    updated = 0
    errors  = []

    # ── regular ───────────────────────────────────────────
    if course_type == 'regular':
        for idx, row in df.iterrows():
            student = find_student(row, idx, errors)
            if not student:
                continue
            grade, _ = StudentGrade.objects.get_or_create(
                grade_sheet=grade_sheet,
                student=student
            )
            grade.midterm_score      = parse_score(row.get('Midterm'))
            grade.section_exam_score = parse_score(row.get('SectionExam'))
            grade.year_work_score    = parse_score(row.get('YearWork'))
            grade.final_exam_score   = parse_score(row.get('FinalExam'))
            grade.save()
            updated += 1

    # ── summer ────────────────────────────────────────────
    elif course_type == 'summer':
        for idx, row in df.iterrows():
            student = find_student(row, idx, errors)
            if not student:
                continue
            try:
                reg = SummerCourseRegistration.objects.get(
                    student=student,
                    course_id=course_id
                )
            except SummerCourseRegistration.DoesNotExist:
                errors.append(
                    f"الصف {idx + 1}: الطالب {student.name} مش مسجل في السمر للمادة دي"
                )
                continue
            reg.student_final_score = parse_score(row.get('FinalExam'))
            reg.save()
            updated += 1

    # ── repeat ────────────────────────────────────────────
    elif course_type == 'repeat':
        for idx, row in df.iterrows():
            student = find_student(row, idx, errors)
            if not student:
                continue
            # بياخد أعلى attempt
            reg = RepeatCourseRegistration.objects.filter(
                student=student,
                course_id=course_id
            ).order_by('-retake_attempt_number').first()
            if not reg:
                errors.append(
                    f"الصف {idx + 1}: الطالب {student.name} مش عنده إعادة للمادة دي"
                )
                continue
            reg.student_final_score = parse_score(row.get('FinalExam'))
            reg.save()
            updated += 1

    # ── carry ─────────────────────────────────────────────
    elif course_type == 'carry':
        for idx, row in df.iterrows():
            student = find_student(row, idx, errors)
            if not student:
                continue
            reg = CarryCourse.objects.filter(
                student=student,
                course_id=course_id
            ).first()
            if not reg:
                errors.append(
                    f"الصف {idx + 1}: الطالب {student.name} مش عنده carry للمادة دي"
                )
                continue
            reg.student_final_score = parse_score(row.get('FinalExam'))
            reg.save()
            updated += 1

    else:
        return Response(
            {"detail": "Invalid type. Use: regular | summer | repeat | carry"},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response({'updated_students': updated, 'errors': errors})