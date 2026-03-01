# 📁 structure/models.py
from django.db import models
from django.apps import apps  # ✅ لحل مشكلة الـ circular import

# ===============================
# 🧩 الاختيارات العامة
# ===============================

class DepartmentChoices(models.TextChoices):
    AI = 'AI', 'Artificial Intelligence'
    DATA = 'DATA', 'Data Science'
    CYBER = 'CYBER', 'Cyber Security'
    AUTOTRONICS = 'AUTOTRONICS', 'Autotronics'
    MECHATRONICS = 'MECHATRONICS', 'Mechatronics'
    GARMENT_MANUFACTURING = 'GARMENT_MANUFACTURING', 'Garment Manufacturing'
    CONTROL_SYSTEMS = 'CONTROL_SYSTEMS', 'Control Systems'


class AcademicYearChoices(models.TextChoices):
    FIRST = 'First', 'First Year'
    SECOND = 'Second', 'Second Year'
    THIRD = 'Third', 'Third Year'
    FOURTH = 'Fourth', 'Fourth Year'


class StudentStatusChoices(models.TextChoices):
    ACTIVE = 'active', 'Active'
    PASSED = 'passed', 'Passed'
    SUMMER = 'summer', 'Summer Course'
    RETAKE_YEAR = 'retake_year', 'Retake Year'


# ===============================
# 🧱 الهيكل الدراسي العام
# ===============================

class StudentStructure(models.Model):
    department = models.CharField(max_length=25, choices=DepartmentChoices.choices)
    year = models.CharField(max_length=6, choices=AcademicYearChoices.choices)
    status = models.CharField(
        max_length=20,
        choices=StudentStatusChoices.choices,
        default=StudentStatusChoices.ACTIVE
    )

    failed_courses = models.ManyToManyField(
        'courses.Course',
        blank=True,
        related_name='failed_structures'
    )
    failed_courses_names = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_department_display()} - {self.get_year_display()} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Student Structure"
        verbose_name_plural = "Student Structures"
        unique_together = ('department', 'year', 'status')


# ===============================
# 🧾 تسجيل المواد العادية
# ===============================

class CourseRegistration(models.Model):
    student = models.ForeignKey(
        'accounts.Student',
        on_delete=models.CASCADE,
        related_name='course_registrations'
    )
    structure = models.ForeignKey(
        StudentStructure,
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    semester = models.CharField(
        max_length=10,
        choices=[('first', 'الفصل الأول'), ('second', 'الفصل الثاني')],
        default='first'
    )
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=[('in_progress', 'In Progress'),
                 ('passed', 'Passed'),
                 ('failed', 'Failed')],
        default='in_progress'
    )

    def __str__(self):
        return f"{self.student.name} - {self.course.name} ({self.get_status_display()})"


# ===============================
# ☀️ تسجيل مواد السمر كورس
# ===============================

class SummerCourseRegistration(models.Model):
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='summer_registrations')
    structure = models.ForeignKey('structure.StudentStructure', on_delete=models.CASCADE, related_name='summer_registrations')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='summer_courses')

    final_exam_full_score = models.FloatField(null=True, blank=True)  # الدرجة الكاملة من جدول الجريد
    student_final_score = models.FloatField(null=True, blank=True)    # الدرجة اللي الدكتور يدخلها
    state = models.CharField(
        max_length=20,
        choices=[('مقبول', 'مقبول'), ('راسب', 'راسب'), ('-', 'لم يحدد بعد')],
        default='-'
    )
    is_evaluated = models.BooleanField(default=False)

    def __str__(self):
        return f"Summer - {self.student.name} - {self.course.name} ({self.state})"

    def evaluate_result(self):
        """تقييم النتيجة بناءً على درجة الطالب في الفاينل"""
        if self.student_final_score is None or not self.final_exam_full_score:
            return
        percentage = (self.student_final_score / self.final_exam_full_score) * 100
        self.state = 'مقبول' if percentage >= 40 else 'راسب'
        self.is_evaluated = True
        self.save(update_fields=['state', 'is_evaluated'])


# ===============================
# 🔁 تسجيل مواد إعادة السنة
# ===============================

class RepeatCourseRegistration(models.Model):
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='repeat_registrations')
    structure = models.ForeignKey('structure.StudentStructure', on_delete=models.CASCADE, related_name='repeat_registrations')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='repeat_courses')
    retake_attempt_number = models.PositiveSmallIntegerField(default=0)
    final_exam_full_score = models.FloatField(null=True, blank=True)
    student_final_score = models.FloatField(null=True, blank=True)
    state = models.CharField(
        max_length=20,
        choices=[('مقبول', 'مقبول'), ('راسب', 'راسب'), ('-', 'لم يحدد بعد')],
        default='-'
    )
    is_evaluated = models.BooleanField(default=False)

    def __str__(self):
        return f"Repeat - {self.student.name} - {self.course.name} ({self.state})"

    def evaluate_result(self):
        if self.student_final_score is None or not self.final_exam_full_score:
            return
        percentage = (self.student_final_score / self.final_exam_full_score) * 100
        self.state = 'مقبول' if percentage >= 40 else 'راسب'
        self.is_evaluated = True
        self.save(update_fields=['state', 'is_evaluated'])


# ===============================
# 📦 المواد المترحلة (Carry Courses)
# ===============================

class CarryCourse(models.Model):
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='carry_records')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='carried_instances')
    from_structure = models.ForeignKey('structure.StudentStructure', on_delete=models.SET_NULL, null=True, blank=True, related_name='carry_from')
    to_structure = models.ForeignKey('structure.StudentStructure', on_delete=models.SET_NULL, null=True, blank=True, related_name='carry_to')

    final_exam_full_score = models.FloatField(null=True, blank=True)
    student_final_score = models.FloatField(null=True, blank=True)
    state = models.CharField(
        max_length=20,
        choices=[('مقبول', 'مقبول'), ('راسب', 'راسب'), ('-', 'لم يحدد بعد')],
        default='-'
    )
    is_evaluated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carry - {self.student.name} - {self.course.name} ({self.state})"

    def evaluate_result(self):
        if self.student_final_score is None or not self.final_exam_full_score:
            return
        percentage = (self.student_final_score / self.final_exam_full_score) * 100
        self.state = 'مقبول' if percentage >= 40 else 'راسب'
        self.is_evaluated = True
        self.save(update_fields=['state', 'is_evaluated'])
