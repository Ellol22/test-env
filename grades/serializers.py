# 📁 grades/serializers.py

from rest_framework import serializers
from .models import GradeSheet, StudentGrade
from structure.models import (
    SummerCourseRegistration,
    RepeatCourseRegistration,
    CarryCourse,
)


# =========================================================
# 🧾 StudentGrade Serializer (المواد العادية)
# =========================================================

class StudentGradeSerializer(serializers.ModelSerializer):
    # بيانات المادة
    subjectName    = serializers.CharField(source='grade_sheet.course.name', read_only=True)
    department     = serializers.CharField(source='grade_sheet.course.structure.get_department_display', read_only=True)
    year           = serializers.CharField(source='grade_sheet.course.structure.get_year_display', read_only=True)
    semester       = serializers.CharField(source='grade_sheet.course.structure.get_semester_display', read_only=True)

    # بيانات الطالب
    student_name   = serializers.SerializerMethodField()
    student_id     = serializers.SerializerMethodField()

    # درجات محسوبة (read only)
    progress               = serializers.SerializerMethodField()
    midterm_score_max      = serializers.SerializerMethodField()
    section_exam_score_max = serializers.SerializerMethodField()
    year_work_score_max    = serializers.SerializerMethodField()
    final_exam_score_max   = serializers.SerializerMethodField()
    total_score_max        = serializers.SerializerMethodField()

    class Meta:
        model  = StudentGrade
        fields = [
            'student_name',
            'student_id',
            'subjectName',
            'department',
            'year',
            'semester',
            'midterm_score',
            'midterm_score_max',
            'section_exam_score',
            'section_exam_score_max',
            'year_work_score',
            'year_work_score_max',
            'final_exam_score',
            'final_exam_score_max',
            'total_score',
            'total_score_max',
            'letter_grade',
            'percentage',
            'is_passed',
            'progress',
        ]
        read_only_fields = [
            'student_name', 'student_id',
            'subjectName', 'department', 'year', 'semester',
            'midterm_score_max', 'section_exam_score_max',
            'year_work_score_max', 'final_exam_score_max',
            'total_score', 'total_score_max',
            'letter_grade', 'percentage', 'is_passed', 'progress',
        ]

    def get_student_name(self, obj):
        return obj.student.user.get_full_name() if obj.student and obj.student.user else ""

    def get_student_id(self, obj):
        return obj.student.student_id if obj.student else None

    def get_progress(self, obj):
        return int(obj.percentage) if obj.percentage is not None else 0

    def get_midterm_score_max(self, obj):
        return obj.grade_sheet.midterm_full_score

    def get_section_exam_score_max(self, obj):
        return obj.grade_sheet.section_exam_full_score

    def get_year_work_score_max(self, obj):
        return obj.grade_sheet.year_work_full_score

    def get_final_exam_score_max(self, obj):
        return obj.grade_sheet.final_exam_full_score

    def get_total_score_max(self, obj):
        return obj.grade_sheet.full_score


# =========================================================
# ☀️ SummerCourseRegistration Serializer
# =========================================================

class SummerGradeSerializer(serializers.ModelSerializer):
    student_name          = serializers.SerializerMethodField()
    student_id            = serializers.SerializerMethodField()
    subjectName           = serializers.CharField(source='course.name', read_only=True)
    final_exam_score_max  = serializers.FloatField(source='final_exam_full_score', read_only=True)

    class Meta:
        model  = SummerCourseRegistration
        fields = [
            'id',
            'student_name',
            'student_id',
            'subjectName',
            'final_exam_score_max',
            'student_final_score',   # ← الدكتور بيكتب فيه
            'state',
            'is_evaluated',
        ]
        read_only_fields = [
            'id', 'student_name', 'student_id',
            'subjectName', 'final_exam_score_max',
            'state', 'is_evaluated',
        ]

    def get_student_name(self, obj):
        return obj.student.user.get_full_name() if obj.student and obj.student.user else obj.student.name

    def get_student_id(self, obj):
        return obj.student.student_id if obj.student else None


# =========================================================
# 🔁 RepeatCourseRegistration Serializer
# =========================================================

class RepeatGradeSerializer(serializers.ModelSerializer):
    student_name          = serializers.SerializerMethodField()
    student_id            = serializers.SerializerMethodField()
    subjectName           = serializers.CharField(source='course.name', read_only=True)
    final_exam_score_max  = serializers.FloatField(source='final_exam_full_score', read_only=True)

    class Meta:
        model  = RepeatCourseRegistration
        fields = [
            'id',
            'student_name',
            'student_id',
            'subjectName',
            'retake_attempt_number',
            'final_exam_score_max',
            'student_final_score',   # ← الدكتور بيكتب فيه
            'state',
            'is_evaluated',
        ]
        read_only_fields = [
            'id', 'student_name', 'student_id',
            'subjectName', 'retake_attempt_number',
            'final_exam_score_max',
            'state', 'is_evaluated',
        ]

    def get_student_name(self, obj):
        return obj.student.user.get_full_name() if obj.student and obj.student.user else obj.student.name

    def get_student_id(self, obj):
        return obj.student.student_id if obj.student else None


# =========================================================
# 📦 CarryCourse Serializer
# =========================================================

class CarryGradeSerializer(serializers.ModelSerializer):
    student_name          = serializers.SerializerMethodField()
    student_id            = serializers.SerializerMethodField()
    subjectName           = serializers.CharField(source='course.name', read_only=True)
    final_exam_score_max  = serializers.FloatField(source='final_exam_full_score', read_only=True)
    from_year             = serializers.SerializerMethodField()
    to_year               = serializers.SerializerMethodField()

    class Meta:
        model  = CarryCourse
        fields = [
            'id',
            'student_name',
            'student_id',
            'subjectName',
            'from_year',
            'to_year',
            'final_exam_score_max',
            'student_final_score',   # ← الدكتور بيكتب فيه
            'state',
            'is_evaluated',
        ]
        read_only_fields = [
            'id', 'student_name', 'student_id',
            'subjectName', 'from_year', 'to_year',
            'final_exam_score_max',
            'state', 'is_evaluated',
        ]

    def get_student_name(self, obj):
        return obj.student.user.get_full_name() if obj.student and obj.student.user else obj.student.name

    def get_student_id(self, obj):
        return obj.student.student_id if obj.student else None

    def get_from_year(self, obj):
        return obj.from_structure.get_year_display() if obj.from_structure else None

    def get_to_year(self, obj):
        return obj.to_structure.get_year_display() if obj.to_structure else None