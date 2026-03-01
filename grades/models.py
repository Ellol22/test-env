# 📁 grades/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import Student, Doctor
from courses.models import Course
from structure.models import (
    StudentStructure,
    CourseRegistration,
)

# =========================================================
# 📘 الشيت الأساسي للمادة (GradeSheet)
# =========================================================

class GradeSheet(models.Model):
    course = models.OneToOneField(
        Course,
        on_delete=models.CASCADE,
        related_name="main_grade_sheet"
    )
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    full_score = models.FloatField(default=100)

    # تقسيم الدرجات (للكورسات العادية فقط)
    final_exam_full_score = models.FloatField(default=50)
    midterm_full_score = models.FloatField(default=20)
    section_exam_full_score = models.FloatField(default=15)
    year_work_full_score = models.FloatField(default=15)

    # هل المادة دي سمر كورس؟
    is_summer = models.BooleanField(default=False)

    def clean(self):
        total_components = (
            self.final_exam_full_score +
            self.midterm_full_score +
            self.section_exam_full_score +
            self.year_work_full_score
        )
        if not self.is_summer and total_components > self.full_score:
            raise ValidationError(
                f"مجموع مكونات الدرجات ({total_components}) لا يمكن أن يتجاوز الدرجة النهائية ({self.full_score})"
            )

    def __str__(self):
        season = "☀️ Summer" if self.is_summer else "📘 Regular"
        return f"{season} - {self.course.name} ({self.doctor or 'No Doctor'})"


# =========================================================
# 🧾 درجات الطالب (StudentGrade)
# =========================================================

class StudentGrade(models.Model):
    grade_sheet = models.ForeignKey(
        GradeSheet,
        on_delete=models.CASCADE,
        related_name='student_grades'
    )
    student_structure = models.ForeignKey(
        StudentStructure,
        on_delete=models.CASCADE
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE
    )
    course_registration = models.ForeignKey(
        CourseRegistration,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="grades"
    )

    # درجات المكونات (لو سمر كورس بيستخدم final فقط)
    midterm_score = models.FloatField(default=0)
    section_exam_score = models.FloatField(default=0)
    final_exam_score = models.FloatField(default=0)
    year_work_score = models.FloatField(default=0)

    total_score = models.FloatField(default=0)
    percentage = models.FloatField(default=0)
    letter_grade = models.CharField(max_length=3, blank=True)
    is_passed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('grade_sheet', 'student')
        indexes = [
            models.Index(fields=['student', 'student_structure']),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.grade_sheet.course.name} - {self.letter_grade or 'N/A'}"

    # -----------------------
    # 🔹 التحقق من صحة الدرجات
    # -----------------------
    def clean(self):
        sheet = self.grade_sheet

        if not sheet.is_summer:
            if self.midterm_score > sheet.midterm_full_score:
                raise ValidationError("درجة الميدتيرم أكبر من الحد المسموح")
            if self.section_exam_score > sheet.section_exam_full_score:
                raise ValidationError("درجة السكشن أكبر من الحد المسموح")
            if self.year_work_score > sheet.year_work_full_score:
                raise ValidationError("درجة أعمال السنة أكبر من الحد المسموح")

        if self.final_exam_score > sheet.final_exam_full_score:
            raise ValidationError("درجة الفاينل أكبر من الحد المسموح")

    # -----------------------
    # 💾 حفظ وتحديث النتيجة
    # -----------------------
    def save(self, *args, **kwargs):
        self.full_clean()
        sheet = self.grade_sheet

        # لو المادة سمر كورس: فاينل فقط
        if sheet.is_summer:
            sheet.full_score = sheet.final_exam_full_score
            self.total_score = self.final_exam_score
        else:
            self.total_score = (
                self.midterm_score +
                self.section_exam_score +
                self.final_exam_score +
                self.year_work_score
            )

        # النسبة المئوية
        if sheet.full_score > 0:
            self.percentage = round((self.total_score / sheet.full_score) * 100, 2)

        # التقدير الحرفي
        self.letter_grade = self.get_letter_grade(self.percentage)

        # النجاح بناءً على النسبة ودرجة الفاينل
        passed_total = self.percentage >= 60
        final_exam_percentage = (
            (self.final_exam_score / sheet.final_exam_full_score) * 100
            if sheet.final_exam_full_score > 0 else 0
        )
        passed_final = final_exam_percentage >= 40
        self.is_passed = passed_total and passed_final

        super().save(*args, **kwargs)
        self.update_course_registration_status()

    # -----------------------
    # 🔠 تحويل النسبة لتقدير حرفي
    # -----------------------
    @staticmethod
    def get_letter_grade(percentage):
        if percentage >= 97: return "A+"
        elif percentage >= 93: return "A"
        elif percentage >= 89: return "A-"
        elif percentage >= 84: return "B+"
        elif percentage >= 80: return "B"
        elif percentage >= 76: return "B-"
        elif percentage >= 73: return "C+"
        elif percentage >= 70: return "C"
        elif percentage >= 67: return "C-"
        elif percentage >= 64: return "D+"
        elif percentage >= 60: return "D"
        else: return "F"

    # -----------------------
    # 🔄 تحديث حالة المادة للطالب
    # -----------------------
    def update_course_registration_status(self):
        course_reg = self.course_registration or CourseRegistration.objects.filter(
            student_structure=self.student_structure,
            course=self.grade_sheet.course
        ).first()

        if not course_reg:
            return

        course_reg.status = 'passed' if self.is_passed else 'failed'
        course_reg.save()


# =========================================================
# 📡 SIGNAL — تحديث نسب الطلاب لو اتغير الشيت
# =========================================================

@receiver(post_save, sender=GradeSheet)
def refresh_student_percentages(sender, instance, **kwargs):
    """
    لو اتغير توزيع الدرجات أو الشيت،
    نعيد حساب نسب الطلاب تلقائيًا
    """
    for grade in instance.student_grades.all():
        grade.save()
