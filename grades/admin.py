# 📁 grades/admin.py

from django.contrib import admin
from .models import GradeSheet, StudentGrade


# =========================================================
# 📘 GradeSheet Admin
# =========================================================
@admin.register(GradeSheet)
class GradeSheetAdmin(admin.ModelAdmin):
    list_display = (
        'course_name',
        'doctor_name',
        'is_summer_display',
        'full_score',
        'final_exam_full_score',
        'midterm_full_score',
        'section_exam_full_score',
        'year_work_full_score',
    )

    list_filter = (
        'is_summer',
        'course__structure__department',
        'course__structure__year',
    )

    search_fields = (
        'course__name',
        'doctor__name',
    )

    fieldsets = (
        ('📘 بيانات المادة', {
            'fields': ('course', 'doctor', 'is_summer'),
        }),
        ('🎯 توزيع الدرجات', {
            'fields': (
                'full_score',
                'final_exam_full_score',
                'midterm_full_score',
                'section_exam_full_score',
                'year_work_full_score',
            )
        }),
    )

    # ======================
    # ✅ دوال عرض مخصصة
    # ======================
    def course_name(self, obj):
        return obj.course.name
    course_name.short_description = "المادة"

    def doctor_name(self, obj):
        return obj.doctor.name if obj.doctor else "-"
    doctor_name.short_description = "الدكتور"

    def is_summer_display(self, obj):
        return "☀️ سمر كورس" if obj.is_summer else "📘 عادي"
    is_summer_display.short_description = "النوع"


# =========================================================
# 👨‍🎓 StudentGrade Admin
# =========================================================
@admin.register(StudentGrade)
class StudentGradeAdmin(admin.ModelAdmin):
    list_display = (
        'student_name',
        'course_name',
        'structure_display',
        'midterm_score',
        'section_exam_score',
        'year_work_score',
        'final_exam_score',
        'total_score',
        'percentage',
        'letter_grade',
        'is_passed_display',
    )

    list_filter = (
        'is_passed',
        'grade_sheet__is_summer',
        'grade_sheet__course__structure__department',
        'grade_sheet__course__structure__year',
    )

    search_fields = (
        'student__name',
        'grade_sheet__course__name',
    )

    readonly_fields = (
        'total_score',
        'percentage',
        'letter_grade',
        'is_passed',
    )

    fieldsets = (
        ('📋 بيانات أساسية', {
            'fields': ('grade_sheet', 'student', 'student_structure', 'course_registration'),
        }),
        ('🧮 الدرجات', {
            'fields': (
                'midterm_score',
                'section_exam_score',
                'year_work_score',
                'final_exam_score',
            )
        }),
        ('🏁 النتائج النهائية (تحسب تلقائيًا)', {
            'fields': (
                'total_score',
                'percentage',
                'letter_grade',
                'is_passed',
            )
        }),
    )

    # ======================
    # ✅ دوال عرض مخصصة
    # ======================
    def student_name(self, obj):
        return obj.student.name if obj.student else "-"
    student_name.short_description = "الطالب"

    def course_name(self, obj):
        if obj.grade_sheet and obj.grade_sheet.course:
            return obj.grade_sheet.course.name
        return "-"
    course_name.short_description = "المادة"

    def structure_display(self, obj):
        s = obj.student_structure
        if not s:
            return "-"
        return f"{s.department} - {s.get_year_display()}"
    structure_display.short_description = "الفرقة / القسم"

    def is_passed_display(self, obj):
        return "✅ ناجح" if obj.is_passed else "❌ راسب"
    is_passed_display.short_description = "النتيجة"

    # ======================
    # 💾 حفظ النموذج
    # ======================
    def save_model(self, request, obj, form, change):
        """
        نحفظ الدرجات ونعيد حساب التقدير تلقائيًا بعد التعديل.
        """
        super().save_model(request, obj, form, change)
        obj.save()  # يعيد حساب total_score و letter_grade و is_passed تلقائيًا
