# 📁 courses/models.py
from django.db import models
from accounts.models import Doctor, Student
from structure.models import StudentStructure


# =========================================================
# 🎯 أنواع الكورسات (عادي - صيفي - مترحل)
# =========================================================
class CourseType(models.TextChoices):
    NORMAL = "normal", "عادي"
    SUMMER = "summer", "صيفي"
    CARRY = "carry", "مترحل"


# =========================================================
# 📆 اختيارات السيميستر (معلومة فقط)
# =========================================================
class SemesterChoices(models.TextChoices):
    FIRST = "first", "الفصل الدراسي الأول"
    SECOND = "second", "الفصل الدراسي الثاني"


# =========================================================
# 🎓 الكورسات
# =========================================================
class Course(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم المادة")
    structure = models.ForeignKey(
        StudentStructure,
        on_delete=models.CASCADE,
        related_name="courses"
    )

    doctor = models.ForeignKey(
        "accounts.Doctor",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        limit_choices_to={'role': 'subject_doctor'},
        related_name='courses'
    )

    # ✅ نوع الكورس (عادي / صيفي / مترحل)
    course_type = models.CharField(
        max_length=20,
        choices=CourseType.choices,
        default=CourseType.NORMAL
    )

    # ✅ السيميستر (معلومة فقط)
    semester = models.CharField(
        max_length=10,
        choices=SemesterChoices.choices,
        default=SemesterChoices.FIRST
    )

    def __str__(self):
        return f"{self.name} - {self.structure.department} - {self.structure.get_year_display()} ({self.get_semester_display()})"


# =========================================================
# 🧑‍🏫 السكاشن والمعيدين
# =========================================================
class CourseSectionAssistant(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='section_assistants'
    )
    section = models.CharField(max_length=10, verbose_name="سكشن")
    assistant = models.ForeignKey(
        "accounts.Doctor",
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teaching_assistant'}
    )

    def __str__(self):
        return f"{self.course.name} - {self.section} - {self.assistant.name}"


# =========================================================
# 📦 المواد المترحلة (Carry Courses)
# =========================================================
class CarryCourse(models.Model):
    student = models.ForeignKey(
        "accounts.Student",
        on_delete=models.CASCADE,
        related_name="carried_instances"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="course_carry_courses"
    )

    # ✅ حالة المادة المترحلة
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'لم تُقيَّم بعد'),
            ('passed', 'ناجح'),
            ('failed', 'راسب')
        ],
        default='pending'
    )

    # ✅ السنة الدراسية اللي المادة اترحلت فيها
    carried_year = models.ForeignKey(
        StudentStructure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carried_courses"
    )

    def __str__(self):
        return f"{self.student.name} - {self.course.name} ({self.get_status_display()})"

    class Meta:
        verbose_name = "مادة مترحلة"
        verbose_name_plural = "المواد المترحلة"
        unique_together = ('student', 'course', 'carried_year')



