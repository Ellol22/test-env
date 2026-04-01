# 📁 accounts/signals.py
from django.db.models.signals import post_save, pre_save
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


# =========================================================
# 🧠 الدالة الأساسية لتوزيع المواد وإنشاء الجريد
# =========================================================
def auto_assign_courses_and_grades(student):
    structure = student.current_structure
    if not structure:
        return

    if structure.status == StudentStatusChoices.ACTIVE:
        if structure.year not in ["First", "Second", "Third", "Fourth"]:
            return

        courses = Course.objects.filter(
            structure__department=structure.department,
            structure__year=structure.year,
        )

        for course in courses:
            course_reg, _ = CourseRegistration.objects.get_or_create(
                student=student,
                structure=structure,
                course=course,
                defaults={'status': 'in_progress'},
            )

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

            StudentGrade.objects.get_or_create(
                grade_sheet=grade_sheet,
                student=student,
                student_structure=structure,
                course_registration=course_reg,
            )

    elif structure.status == StudentStatusChoices.SUMMER:
        courses = structure.failed_courses.all()
        for course in courses:
            SummerCourseRegistration.objects.get_or_create(
                student=student,
                structure=structure,
                course=course,
                defaults={'state': '-'},
            )

    elif structure.status == StudentStatusChoices.RETAKE_YEAR:
    # ⛔ الـ action هو المسؤول عن إضافة RepeatCourseRegistration
    # الـ signal لا تتدخل هنا عشان متضيفش كل مواد السنة
        return


# =========================================================
# 🔍 pre_save: نحفظ الـ structure القديمة قبل الـ save
# =========================================================
@receiver(pre_save, sender=Student)
def track_structure_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_structure = Student.objects.get(pk=instance.pk).current_structure
        except Student.DoesNotExist:
            instance._old_structure = None
    else:
        instance._old_structure = None


# =========================================================
# 📝 post_save: إضافة الـ structure للـ history
# =========================================================
@receiver(post_save, sender=Student)
def add_current_structure_to_history(sender, instance, created, **kwargs):
    if not instance.current_structure:
        return

    new_struct = {
        'id': instance.current_structure.id,
        'department': instance.current_structure.department,
        'year': instance.current_structure.year,
        'status': instance.current_structure.status,
    }

    history = instance.structures_history or []
    if new_struct not in history:
        history.append(new_struct)
        instance.structures_history = history
        Student.objects.filter(pk=instance.pk).update(structures_history=history)
        print(f"[Signal] Added {new_struct} to history for {instance.name}")
    else:
        print(f"[Signal] {new_struct} already in history")


# =========================================================
# 🚀 post_save: توزيع المواد والجريد
# =========================================================
@receiver(post_save, sender=Student)
def create_student_structure_and_courses(sender, instance, created, **kwargs):
    student = instance

    if created:
        # أول مرة: نتأكد من وجود current_structure
        if not student.current_structure:
            structure, _ = StudentStructure.objects.get_or_create(
                department=student.department,
                year=student.year,
                status=StudentStatusChoices.ACTIVE,
            )
            Student.objects.filter(pk=student.pk).update(current_structure=structure)
            student.current_structure = structure

        auto_assign_courses_and_grades(student)

    else:
        # ✅ لو الـ structure اتغير → شغّل التوزيع تاني
        old_structure = getattr(student, '_old_structure', None)
        if (
            student.current_structure is not None
            and old_structure != student.current_structure
        ):
            print(f"[Signal] Structure changed for {student.name}: {old_structure} → {student.current_structure}")
            auto_assign_courses_and_grades(student)