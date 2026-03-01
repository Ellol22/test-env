# 📁 accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Student
from structure.models import (
    StudentStructure,
    CourseRegistration,
    SummerCourseRegistration,
    RepeatCourseRegistration,
    StudentStatusChoices,
)
from courses.models import Course
from grades.models import GradeSheet, StudentGrade
from django.db.models.signals import pre_save


# =========================================================
# 🎯 دالة إنشاء أو تحديث الاستراكتشر
# =========================================================
def get_or_create_structure(student, status):
    structure, created = StudentStructure.objects.get_or_create(
        department=student.department,
        year=student.year,
        status=status,
    )
    return structure


# =========================================================
# 🧠 الدالة الأساسية لتوزيع المواد وإنشاء الجريد
# =========================================================
def auto_assign_courses_and_grades(student):
    structure = student.current_structure
    if not structure:
        return

    # -----------------------------
    # الحالة 1️⃣: Active (طالب عادي)
    # -----------------------------
    if structure.status == StudentStatusChoices.ACTIVE:
        # نطبق فقط على السنوات الدراسية العادية (First / Second / Third / Fourth)
        if structure.year not in ["First", "Second", "Third", "Fourth"]:
            return

        courses = Course.objects.filter(
            structure__department=structure.department,
            structure__year=structure.year,
        )

        for course in courses:
            # تسجيل الطالب في الكورس
            course_reg, _ = CourseRegistration.objects.get_or_create(
                student=student,
                structure=structure,
                course=course,
                defaults={'status': 'in_progress'},
            )

            # إنشاء GradeSheet لو مش موجود
            grade_sheet, _ = GradeSheet.objects.get_or_create(
                course=course,
                defaults={
                    'doctor': course.doctor,
                    'final_exam_full_score': 50,
                    'midterm_full_score': 20,
                    'section_exam_full_score': 15,
                    'year_work_full_score': 15,
                },
            )

            # إنشاء StudentGrade
            StudentGrade.objects.get_or_create(
                grade_sheet=grade_sheet,
                student=student,
                student_structure=structure,
                course_registration=course_reg,
            )

    # -----------------------------
    # الحالة 2️⃣: Summer course
    # -----------------------------
    elif structure.status == StudentStatusChoices.SUMMER:
        # تسجيل المواد الساقطة فقط في SummerCourseRegistration
        courses = structure.failed_courses.all()
        for course in courses:
            SummerCourseRegistration.objects.get_or_create(
                student=student,
                structure=structure,
                course=course,
                defaults={'state': '-'},
            )
        # لا ننشئ Grades هنا

    # -----------------------------
    # الحالة 3️⃣: Retake year
    # -----------------------------
    elif structure.status == StudentStatusChoices.RETAKE_YEAR:
        # تسجيل جميع المواد في RepeatCourseRegistration
        courses = Course.objects.filter(
            structure__department=structure.department,
            structure__year=structure.year,
        )

        for course in courses:
            RepeatCourseRegistration.objects.get_or_create(
                student=student,
                structure=structure,
                course=course,
                defaults={'state': '-'},
            )
        # لا ننشئ Grades هنا

    # -----------------------------
    # الحالة 4️⃣: Passed student
    # -----------------------------
    elif structure.status == StudentStatusChoices.PASSED:
        next_year_structure, _ = StudentStructure.objects.get_or_create(
            department=structure.department,
            year=structure.year.get_next(),
            status=StudentStatusChoices.ACTIVE,
        )
        student.current_structure = next_year_structure
        student.save(update_fields=['current_structure'])




@receiver(post_save, sender=Student)
def add_current_structure_to_history(sender, instance, created, **kwargs):
    if not instance.current_structure:
        print(f"[Signal] No current_structure set for {instance.name}")
        return

    # نعمل نسخة dict من current_structure
    new_struct = {
        'id': instance.current_structure.id,
        'department': instance.current_structure.department,
        'year': instance.current_structure.year,
        'status': instance.current_structure.status,
    }

    # نضيفها لو مش موجودة بالفعل
    history = instance.structures_history or []
    if new_struct not in history:
        history.append(new_struct)
        instance.structures_history = history
        # ⚠️ بدون إعادة save داخل post_save ممكن يحصل RecursionError
        Student.objects.filter(pk=instance.pk).update(structures_history=history)
        print(f"[Signal] Added {new_struct} to history for {instance.name}")
    else:
        print(f"[Signal] {new_struct} already in history")

# # =========================================================
# # 🚀 signal لما طالب يتسجل أو يتحدث
# # =========================================================
@receiver(post_save, sender=Student)
def create_student_structure_and_courses(sender, instance, created, **kwargs):
    student = instance

    # ❗ نتأكد إننا في أول مرة فقط
    if created:
        # تأكيد وجود current_structure
        if not student.current_structure:
            structure, _ = StudentStructure.objects.get_or_create(
                department=student.department,
                year=student.year,
                status=StudentStatusChoices.ACTIVE,
            )
            # تحديث مباشر بدون استدعاء السيجنال
            Student.objects.filter(pk=student.pk).update(current_structure=structure)
            student.current_structure = structure

        # 🎯 تسجيل المواد وإنشاء الجريد
        auto_assign_courses_and_grades(student)
