# 📁 student_records/models.py
from django.db import models
from accounts.models import Student
from structure.models import StudentStructure, SummerCourseRegistration, RepeatCourseRegistration, CarryCourse

class Graduation(models.Model):
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name="graduation_record"
    )
    # كل الاستراكتشرز اللي الطالب عدِّي عليها
    structures = models.ManyToManyField(
        StudentStructure,
        related_name="graduated_students",
        blank=True
    )
    # التاريخ اللي تم فيه تسجيل التخرج
    graduated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Graduation - {self.student.name} ({self.student.student_id or self.pk})"


# 📁 student_records/models.py
class DroppedOut(models.Model):
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name="dropped_out_record"
    )

    # كل الاستراكتشرز اللي الطالب عدِّي عليها
    structures = models.ManyToManyField(
        StudentStructure,
        related_name="dropped_out_students",
        blank=True
    )

    # درجات الطالب في الحالات المختلفة قبل المسح من الجداول الأصلية
    summer_courses = models.ManyToManyField(
        SummerCourseRegistration,
        related_name="dropped_out_students",
        blank=True
    )
    repeat_courses = models.ManyToManyField(
        RepeatCourseRegistration,
        related_name="dropped_out_students",
        blank=True
    )
    carry_courses = models.ManyToManyField(
        CarryCourse,
        related_name="dropped_out_students",
        blank=True
    )

    # التاريخ اللي تم فيه تسجيل الطالب كفاشل / خرج
    dropped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DroppedOut - {self.student.name} ({self.student.student_id})"

class DroppedOutCourse(models.Model):
    DROPPED_COURSE_TYPE = [
        ('regular', 'Regular'),
        ('summer', 'Summer'),
        ('repeat', 'Repeat'),
        ('carry', 'Carry'),
    ]

    dropped = models.ForeignKey(
        'DroppedOut',
        on_delete=models.CASCADE,
        related_name='courses'
    )

    course_name = models.CharField(max_length=255)
    course_type = models.CharField(max_length=10, choices=DROPPED_COURSE_TYPE)

    # ---- درجات كاملة (تنفع للـ regular) ----
    midterm_score = models.FloatField(null=True, blank=True)
    section_exam_score = models.FloatField(null=True, blank=True)
    year_work_score = models.FloatField(null=True, blank=True)
    final_exam_score = models.FloatField(null=True, blank=True)

    final_exam_full_score = models.FloatField(null=True, blank=True)

    total_score = models.FloatField(null=True, blank=True)
    percentage = models.FloatField(null=True, blank=True)
    letter_grade = models.CharField(max_length=3, blank=True)
    is_passed = models.BooleanField(null=True, blank=True)
