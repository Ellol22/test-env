from django.contrib import admin
from .models import Graduation, DroppedOut, DroppedOutCourse

# =========================================================
# 🔹 Graduation Admin (زي ما هو)
# =========================================================
@admin.register(Graduation)
class GraduationAdmin(admin.ModelAdmin):
    list_display = ('student', 'graduated_at')
    readonly_fields = ('student', 'graduated_at', 'display_grades', 'display_structures')

    def display_grades(self, obj):
        grades = obj.student.studentgrade_set.all()
        return ", ".join([f"{g.grade_sheet.course.name} ({g.letter_grade})" for g in grades])
    display_grades.short_description = "Grades"

    def display_structures(self, obj):
        return ", ".join([str(s) for s in obj.structures.all()])
    display_structures.short_description = "Structures"


# =========================================================
# 🔹 Inlines لكل نوع course
# =========================================================
class RegularCourseInline(admin.TabularInline):
    model = DroppedOutCourse
    extra = 0
    can_delete = False
    verbose_name = "Regular Course"
    verbose_name_plural = "Regular Courses"

    fields = (
        'course_name',
        'course_type',
        'midterm_score',
        'midterm_full_score',
        'section_exam_score',
        'section_exam_full_score',
        'year_work_score',
        'year_work_full_score',
        'final_exam_score',
        'final_exam_full_score',
        'total_score',
        'percentage',
        'letter_grade',
        'is_passed',
    )

    readonly_fields = fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(course_type='regular')

    # الدرجات الكاملة لكل مكون من GradeSheet
    def midterm_full_score(self, obj):
        grade = obj.dropped.student.studentgrade_set.filter(course_registration__course__name=obj.course_name).first()
        return grade.grade_sheet.midterm_full_score if grade else None

    def section_exam_full_score(self, obj):
        grade = obj.dropped.student.studentgrade_set.filter(course_registration__course__name=obj.course_name).first()
        return grade.grade_sheet.section_exam_full_score if grade else None

    def year_work_full_score(self, obj):
        grade = obj.dropped.student.studentgrade_set.filter(course_registration__course__name=obj.course_name).first()
        return grade.grade_sheet.year_work_full_score if grade else None


class SummerCourseInline(admin.TabularInline):
    model = DroppedOutCourse
    extra = 0
    can_delete = False
    verbose_name = "Summer Course"
    verbose_name_plural = "Summer Courses"

    fields = (
        'course_name',
        'course_type',
        'final_exam_score',
        'final_exam_full_score',
    )
    readonly_fields = fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(course_type='summer')


class RepeatCourseInline(admin.TabularInline):
    model = DroppedOutCourse
    extra = 0
    can_delete = False
    verbose_name = "Repeat Course"
    verbose_name_plural = "Repeat Courses"

    fields = (
        'course_name',
        'course_type',
        'final_exam_score',
        'final_exam_full_score',
    )
    readonly_fields = fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(course_type='repeat')


class CarryCourseInline(admin.TabularInline):
    model = DroppedOutCourse
    extra = 0
    can_delete = False
    verbose_name = "Carry Course"
    verbose_name_plural = "Carry Courses"

    fields = (
        'course_name',
        'course_type',
        'final_exam_score',
        'final_exam_full_score',
    )
    readonly_fields = fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(course_type='carry')


# =========================================================
# 🔹 DroppedOut Admin
# =========================================================
@admin.register(DroppedOut)
class DroppedOutAdmin(admin.ModelAdmin):
    list_display = ('student', 'dropped_at')
    search_fields = (
        'student__name',
        'student__student_id',
        'student__national_id',
    )
    list_filter = ('dropped_at',)

    readonly_fields = ('student', 'dropped_at')

    inlines = [
        RegularCourseInline,
        SummerCourseInline,
        RepeatCourseInline,
        CarryCourseInline,
    ]

    # ⛔ نمنع أي تعديل يدوي على الأرشيف
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True
