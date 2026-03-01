# 📁 accounts/models.py
import logging
from django.db import models
from django.contrib.auth.models import User
from collections import defaultdict

logger = logging.getLogger(__name__)


# =========================================================
# 👨‍🎓 نموذج الطالب Student
# =========================================================
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=25)
    mobile = models.CharField(max_length=11, blank=True, null=True)
    national_id = models.CharField(max_length=14)
    student_id = models.CharField(  # ✅ رقم الجلوس
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        db_index=True
    )
    sec_num = models.IntegerField(null=True, blank=True)

    # ✅ الهيكل الحالي (السنة الدراسية اللي فيها الطالب دلوقتي)
    current_structure = models.ForeignKey(
        'structure.StudentStructure',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_students"
    )

    # ✅ كل الهياكل اللي الطالب مرّ بيها (السجل الأكاديمي الكامل)
    structures_history = models.JSONField(default=list, blank=True, null=True)

                    
    def __str__(self):
        return f"{self.name} ({self.student_id or self.pk})"

    # =========================================================
    # 🎯 المواد المترحلة (Carry Courses)
    # =========================================================
    @property
    def carry_courses(self):
        from structure.models import CarryCourse
        return CarryCourse.objects.filter(student=self, status='pending')

    # =========================================================
    # 🧠 المواد الحالية (السنة الدراسية الحالية)
    # =========================================================
    def get_my_courses(self):
        from courses.models import Course
        if self.current_structure:
            logger.debug("Fetching current courses for student: %s", self.name)
            return Course.objects.filter(structure=self.current_structure)
        logger.warning("No current_structure found for student: %s", self.name)
        return Course.objects.none()

    # =========================================================
    # 📚 جميع المواد بالقسم مجمعة حسب السنة
    # =========================================================
    def get_all_department_courses_grouped(self):
        from courses.models import Course
        if not self.current_structure:
            logger.warning("No current_structure found for student: %s", self.name)
            return {}

        logger.debug("Fetching grouped courses for student: %s", self.name)
        courses = Course.objects.filter(structure__department=self.current_structure.department)
        grouped = defaultdict(list)

        for course in courses:
            key = f"{course.structure.get_year_display()}"
            grouped[key].append(course)

        return dict(grouped)

    # =========================================================
    # 📊 المواد المطلوب تقييمها (السنة الحالية + المواد المترحلة)
    # =========================================================
    def get_all_courses_for_evaluation(self):
        from courses.models import Course
        if not self.current_structure:
            return Course.objects.none()

        current_courses = Course.objects.filter(structure=self.current_structure)
        carry = [c.course for c in self.carry_courses]
        return current_courses.union(Course.objects.filter(pk__in=[c.pk for c in carry]))

    class Meta:
        indexes = [
            models.Index(fields=['national_id']),
        ]


# =========================================================
# 👨‍🏫 نموذج الدكتور Doctor
# =========================================================
class DoctorRole(models.TextChoices):
    SUBJECT_DOCTOR = 'subject_doctor', 'دكتور مادة'
    ADMIN_DOCTOR = 'admin_doctor', 'دكتور إداري'
    TEACHING_ASSISTANT = 'teaching_assistant', 'معيد'


class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=25)
    mobile = models.CharField(max_length=11, blank=True, null=True)
    national_id = models.CharField(max_length=14, unique=True)
    role = models.CharField(
        max_length=20,
        choices=DoctorRole.choices,
        default=DoctorRole.SUBJECT_DOCTOR
    )

    # ✅ الدكتور ممكن يدرّس في أكتر من سنة أو قسم
    structures = models.ManyToManyField(
        'structure.StudentStructure',
        blank=True,
        related_name="doctors"
    )

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

    def get_my_courses(self):
        from courses.models import Course
        logger.debug("Fetching courses for doctor: %s", self.name)
        return Course.objects.filter(doctor=self)

    class Meta:
        indexes = [
            models.Index(fields=['national_id']),
        ]
