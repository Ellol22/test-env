# 📁 structure/admin.py
from django.contrib import admin
from django.apps import apps
from django.db import transaction
from django.utils import timezone
from .models import (
    StudentStructure,
    CourseRegistration,
    SummerCourseRegistration,
    RepeatCourseRegistration,
    CarryCourse,
    DepartmentChoices,
    AcademicYearChoices,
    StudentStatusChoices
)
from grades.models import StudentGrade
from accounts.models import Student
from django.db.models import Max

# -----------------------
# Helper: جلب موديلات من apps (late import-safe)
# -----------------------
def get_model(app_label, model_name):
    return apps.get_model(app_label, model_name)

# -----------------------
# Helper: إنشاء سجل Graduation
# -----------------------
def create_graduation_record(student):
    Graduation = get_model('student_records', 'Graduation')
    if not Graduation:
        return None

    grad, created = Graduation.objects.get_or_create(student=student)

    # ✅ نجيب الـ structures من structures_history الصح
    history = student.structures_history or []
    struct_ids = [item.get("id") for item in history if item.get("id")]
    structures = StudentStructure.objects.filter(id__in=struct_ids)
    grad.structures.set(structures)

    grad.graduated_at = timezone.now()
    grad.save(update_fields=['graduated_at'])

    # ✅ تغيير current_structure للطالب إلى graduated
    if student.current_structure:
        graduated_structure, _ = StudentStructure.objects.get_or_create(
            department=student.current_structure.department,
            year=student.current_structure.year,
            status=StudentStatusChoices.GRADUATED,
        )
        Student.objects.filter(pk=student.pk).update(
            current_structure=graduated_structure
        )
        # ✅ نحدث الـ instance في الذاكرة كمان
        student.current_structure = graduated_structure
        print(f"[Graduation] {student.name} moved to graduated structure")

    return grad


def archive_student_before_drop(student, dropped_record):
    """
    أرشفة كل بيانات الطالب داخل DroppedOut record قبل ما يخرج نهائي.
    """
    from structure.models import (
        StudentStructure,
        CarryCourse,
        SummerCourseRegistration,
        RepeatCourseRegistration,
        CourseRegistration
    )
    from grades.models import StudentGrade

    # 1) أرشفة structures_history → M2M
    history = student.structures_history or []
    struct_ids = [item.get("id") for item in history if item.get("id")]
    structures = StudentStructure.objects.filter(id__in=struct_ids)
    dropped_record.structures.set(structures)

    # 2) أرشفة المواد العادية مع كل الدرجات
    for reg in CourseRegistration.objects.filter(student=student):
        try:
            grade = StudentGrade.objects.get(student=student, course_registration=reg)
        except StudentGrade.DoesNotExist:
            grade = None

        dropped_record.courses.create(
            course_name=reg.course.name,
            course_type='regular',
            midterm_score=grade.midterm_score if grade else None,
            section_exam_score=grade.section_exam_score if grade else None,
            year_work_score=grade.year_work_score if grade else None,
            final_exam_score=grade.final_exam_score if grade else None,
            final_exam_full_score=reg.course.main_grade_sheet.final_exam_full_score if hasattr(reg.course, 'main_grade_sheet') else None,
            total_score=grade.total_score if grade else None,
            percentage=grade.percentage if grade else None,
            letter_grade=grade.letter_grade if grade else None,
            is_passed=grade.is_passed if grade else None
        )

    # 3) أرشفة Summer
    for reg in SummerCourseRegistration.objects.filter(student=student):
        dropped_record.courses.create(
            course_name=reg.course.name,
            course_type='summer',
            final_exam_score=reg.student_final_score,
            final_exam_full_score=reg.final_exam_full_score
        )

    # 4) أرشفة Repeat
    for reg in RepeatCourseRegistration.objects.filter(student=student):
        dropped_record.courses.create(
            course_name=reg.course.name,
            course_type='repeat',
            final_exam_score=reg.student_final_score,
            final_exam_full_score=reg.final_exam_full_score
        )

    # 5) أرشفة Carry
    for reg in CarryCourse.objects.filter(student=student):
        dropped_record.courses.create(
            course_name=reg.course.name,
            course_type='carry',
            final_exam_score=reg.student_final_score,
            final_exam_full_score=reg.final_exam_full_score
        )

    dropped_record.save()


def create_droppedout_record_and_archive(student, reason=None):
    from student_records.models import DroppedOut

    dropped, created = DroppedOut.objects.get_or_create(student=student)

    # أرشفة البيانات بالكامل
    archive_student_before_drop(student, dropped)

    # ✅ تغيير current_structure للطالب إلى dropped_out
    if student.current_structure:
        dropped_structure, _ = StudentStructure.objects.get_or_create(
            department=student.current_structure.department,
            year=student.current_structure.year,
            status=StudentStatusChoices.DROPPED_OUT,
        )
        Student.objects.filter(pk=student.pk).update(current_structure=dropped_structure)
        # نحدث الـ instance في الذاكرة كمان عشان أي كود بعده يشوف التغيير
        student.current_structure = dropped_structure
        print(f"[DroppedOut] {student.name} moved to dropped_out structure. Reason: {reason}")

    return dropped


# =========================================================
# 🎯 الأكشن: التقييم السنوي
# =========================================================
@admin.action(description="تقييم سنوي شامل (اعتمادًا على نتائج الطلاب) — تنفيذ الانتقالات (Active / Summer / Graduation)")
def evaluate_annual_performance(modeladmin, request, queryset):
    CourseRegistration = get_model('structure', 'CourseRegistration')
    CarryCourse = get_model('structure', 'CarryCourse')
    SummerCourseRegistration = get_model('structure', 'SummerCourseRegistration')
    StudentStructure = get_model('structure', 'StudentStructure')
    GradeSheet = get_model('grades', 'GradeSheet')

    promoted = 0
    to_summer = 0
    graduated = 0

    YEAR_MAP = {
        "First": "Second",
        "Second": "Third",
        "Third": "Fourth",
        "Fourth": "Fourth",
    }

    for structure in queryset:
        students = Student.objects.filter(course_registrations__structure=structure).distinct()
        if not students.exists():
            continue

        for student in students:
            course_regs = CourseRegistration.objects.filter(student=student, structure=structure)
            carry_courses = CarryCourse.objects.filter(student=student)

            for cc in carry_courses:
                if not cc.is_evaluated:
                    cc.evaluate_result()

            failed_normal = course_regs.filter(status='failed')
            failed_carry = carry_courses.filter(state='راسب')
            total_failed = failed_normal.count() + failed_carry.count()

            if total_failed == 0:
                promoted += 1
                next_year = YEAR_MAP.get(structure.year, structure.year)
                next_structure, _ = StudentStructure.objects.get_or_create(
                    department=structure.department,
                    year=next_year,
                    status=StudentStatusChoices.ACTIVE
                )
                student.current_structure = next_structure
                try:
                    student.structures.add(structure)
                except Exception:
                    pass
                student.save(update_fields=['current_structure'])

                if structure.year == "Fourth":
                    create_graduation_record(student)
                    graduated += 1
                continue

            summer_structure, _ = StudentStructure.objects.get_or_create(
                department=structure.department,
                year=structure.year,
                status=StudentStatusChoices.SUMMER
            )
            student.current_structure = summer_structure
            student.save(update_fields=['current_structure'])

            for f in failed_normal:
                gs = GradeSheet.objects.filter(course=f.course).first()
                final_full_score = gs.final_exam_full_score if gs else None
                SummerCourseRegistration.objects.get_or_create(
                    student=student,
                    structure=summer_structure,
                    course=f.course,
                    defaults={'final_exam_full_score': final_full_score}
                )

            for c in failed_carry:
                gs = GradeSheet.objects.filter(course=c.course).first()
                final_full_score = gs.final_exam_full_score if gs else None
                SummerCourseRegistration.objects.get_or_create(
                    student=student,
                    structure=summer_structure,
                    course=c.course,
                    defaults={'final_exam_full_score': final_full_score}
                )
                CarryCourse.objects.update_or_create(
                    student=student,
                    course=c.course,
                    from_structure=structure,
                    defaults={'final_exam_full_score': final_full_score}
                )

            to_summer += 1

    modeladmin.message_user(request, f"✅ ناجحين: {promoted} | 🌞 دخلوا سمر: {to_summer} | 🎓 خريجين جدد: {graduated}")


# =========================================================
# 🎯 الأكشن: تقييم السمر كورس
# =========================================================
@admin.action(description="تقييم السمر كورس وتحديد الترحيل النهائي (Carry / Retake / Active / Graduation / DroppedOut)")
def evaluate_summer_courses(modeladmin, request, queryset):
    from django.db.models import Max
    from django.apps import apps

    Student = apps.get_model('accounts', 'Student')
    SummerModel = apps.get_model('structure', 'SummerCourseRegistration')
    StudentStructure = apps.get_model('structure', 'StudentStructure')
    CarryCourse = apps.get_model('structure', 'CarryCourse')
    RepeatModel = apps.get_model('structure', 'RepeatCourseRegistration')
    GradeSheet = apps.get_model('grades', 'GradeSheet')

    YEAR_MAP = {"First": "Second", "Second": "Third", "Third": "Fourth", "Fourth": "Fourth"}

    passed = carry = retake = graduated = dropped = 0

    for structure in queryset:
    # ✅ نتأكد إن الـ structure دي summer فعلاً
        if structure.status != StudentStatusChoices.SUMMER:
            continue

        students = Student.objects.filter(summer_registrations__structure=structure).distinct()
        for student in students:
            # ✅ بس اللي مش متقيَّم
            regs = SummerModel.objects.filter(
                student=student,
                structure=structure,
                is_evaluated=False
            ).select_related('course')

            if not regs.exists():
                continue

            for reg in regs:
                gs = GradeSheet.objects.filter(course=reg.course).first()
                if gs and (reg.final_exam_full_score is None or reg.final_exam_full_score != gs.final_exam_full_score):
                    reg.final_exam_full_score = gs.final_exam_full_score
                    reg.save(update_fields=['final_exam_full_score'])
                reg.evaluate_result()

            failed_courses = {reg.course for reg in regs if reg.state == 'راسب'}
            failed_count = len(failed_courses)
            
            # ----------------------------
            # نجاح كامل
            # ----------------------------
            if failed_count == 0:
                passed += 1
                nxt, _ = StudentStructure.objects.get_or_create(
                    department=structure.department,
                    year=YEAR_MAP.get(structure.year),
                    status='active'
                )
                student.current_structure = nxt
                student.save(update_fields=['current_structure'])
                if structure.year == "Fourth":
                    create_graduation_record(student)
                    graduated += 1
                continue

            # ----------------------------
            # 1-2 مواد راسبة
            # ----------------------------
            if failed_count < 3:
                if structure.year == "Fourth":
                    # ✅ نتحقق الأول: هل تجاوز المحاولتين؟
                    should_drop = False
                    for course in failed_courses:
                        max_prev = RepeatModel.objects.filter(
                            student=student, course=course
                        ).aggregate(m=Max('retake_attempt_number'))['m'] or 0
                        if max_prev >= 2:
                            should_drop = True
                            break

                    if should_drop:
                        create_droppedout_record_and_archive(
                            student,
                            reason='Exceeded repeat attempts in Fourth year'
                        )
                        dropped += 1
                        continue  # ✅ مش break

                    retake += 1
                    retake_structure, _ = StudentStructure.objects.get_or_create(
                        department=structure.department,
                        year=structure.year,
                        status=StudentStatusChoices.RETAKE_YEAR
                    )
                    student.current_structure = retake_structure
                    student.save(update_fields=['current_structure'])

                    for course in failed_courses:
                        max_prev = RepeatModel.objects.filter(
                            student=student, course=course
                        ).aggregate(m=Max('retake_attempt_number'))['m'] or 0
                        new_attempt = max_prev + 1
                        gs = GradeSheet.objects.filter(course=course).first()
                        RepeatModel.objects.get_or_create(
                            student=student,
                            structure=retake_structure,
                            course=course,
                            retake_attempt_number=new_attempt,
                            defaults={
                                'final_exam_full_score': gs.final_exam_full_score if gs else None,
                                'state': '-',
                                'is_evaluated': False
                            }
                        )
                    continue

                # سنة عادية → Carry عادي
                carry += 1
                for course in failed_courses:
                    CarryCourse.objects.get_or_create(
                        student=student,
                        course=course,
                        from_structure=structure
                    )
                nxt, _ = StudentStructure.objects.get_or_create(
                    department=structure.department,
                    year=YEAR_MAP.get(structure.year),
                    status='active'
                )
                student.current_structure = nxt
                student.save(update_fields=['current_structure'])
                continue

            # ----------------------------
            # 3+ مواد راسبة -> Retake Year
            # ----------------------------
            retake += 1
            retake_structure, _ = StudentStructure.objects.get_or_create(
                department=structure.department,
                year=structure.year,
                status='retake_year'
            )
            student.current_structure = retake_structure
            student.save(update_fields=['current_structure'])

            for course in failed_courses:
                max_prev = RepeatModel.objects.filter(
                    student=student, course=course
                ).aggregate(m=Max('retake_attempt_number'))['m'] or 0
                new_attempt = max_prev + 1

                if new_attempt > 2:
                    create_droppedout_record_and_archive(
                        student,
                        reason=f'Exceeded allowed repeat attempts for {course.name}'
                    )
                    dropped += 1
                    continue  # ✅ مش break
                else:
                    gs = GradeSheet.objects.filter(course=course).first()
                    RepeatModel.objects.get_or_create(
                        student=student,
                        structure=retake_structure,
                        course=course,
                        retake_attempt_number=new_attempt,
                        defaults={
                            'final_exam_full_score': gs.final_exam_full_score if gs else None,
                            'state': '-',
                            'is_evaluated': False
                        }
                    )

    modeladmin.message_user(
        request,
        f"سمر: ✅ ناجحين: {passed} | كاري: {carry} | إعادة سنة: {retake} | 🎓 خريجين: {graduated} | ❌ مطرودين: {dropped}"
    )


# =========================================================
# 🎯 الأكشن: تقييم مواد إعادة السنة
# =========================================================
@admin.action(description="🔁 تقييم مواد إعادة السنة (حسب أعلى attempt و Summer)")
def evaluate_retake_courses(modeladmin, request, queryset):
    RepeatModel = get_model('structure', 'RepeatCourseRegistration')
    SummerModel = get_model('structure', 'SummerCourseRegistration')
    StudentStructure = get_model('structure', 'StudentStructure')

    passed = 0
    to_summer = 0

    YEAR_MAP = {
        "First": "Second",
        "Second": "Third",
        "Third": "Fourth",
        "Fourth": "Fourth",
    }

    for structure in queryset:
        students = Student.objects.filter(repeat_registrations__structure=structure).distinct()
        for student in students:
            repeat_courses = RepeatModel.objects.filter(
                student=student,
                structure=structure,
                is_evaluated=False
            )

            if not repeat_courses.exists():
                continue

            max_attempts = repeat_courses.values('course').annotate(
                max_attempt=Max('retake_attempt_number')
            )
            highest_attempt = max([x['max_attempt'] for x in max_attempts], default=0)

            target_courses = [
                rr for rr in repeat_courses if rr.retake_attempt_number == highest_attempt
            ]

            failed_courses = []

            for rc in target_courses:
                rc.evaluate_result()
                if rc.state == 'راسب':
                    failed_courses.append(rc)

            if not failed_courses:
                passed += 1
                next_structure, _ = StudentStructure.objects.get_or_create(
                    department=structure.department,
                    year=YEAR_MAP.get(structure.year),
                    status=StudentStatusChoices.ACTIVE
                )
                student.current_structure = next_structure
                student.save(update_fields=['current_structure'])
                continue

            to_summer += 1
            summer_structure, _ = StudentStructure.objects.get_or_create(
                department=structure.department,
                year=structure.year,
                status=StudentStatusChoices.SUMMER
            )

            for f in failed_courses:
                SummerModel.objects.create(
                    student=student,
                    structure=summer_structure,
                    course=f.course,
                    final_exam_full_score=f.final_exam_full_score or 100,
                    state='-',
                    is_evaluated=False,
                )

            student.current_structure = summer_structure
            student.save(update_fields=['current_structure'])

    modeladmin.message_user(
        request,
        f"🔁 إعادة السنة: ✅ ناجحين: {passed} | ☀️ دخلوا Summer: {to_summer}"
    )


# =========================================================
# Admin registrations
# =========================================================
@admin.register(StudentStructure)
class StudentStructureAdmin(admin.ModelAdmin):
    list_display = ('department', 'year', 'status', 'created_at', 'student_count')
    list_filter = ('department', 'year', 'status')
    search_fields = ('department',)
    actions = [evaluate_annual_performance, evaluate_summer_courses, evaluate_retake_courses]

    def student_count(self, obj):
        return Student.objects.filter(current_structure=obj).count()
    student_count.short_description = "عدد الطلبة"


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = ('course', 'student', 'structure', 'status', 'grade')
    list_filter = ('status',)
    search_fields = ('student__name', 'course__name')


@admin.register(SummerCourseRegistration)
class SummerCourseRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        'course',
        'student',
        'structure',
        'final_exam_full_score',
        'student_final_score',
        'state',
        'is_evaluated'
    )
    list_filter = ('state', 'is_evaluated')
    search_fields = ('student__name', 'course__name')


@admin.register(RepeatCourseRegistration)
class RepeatCourseRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        'course',
        'student',
        'structure',
        'final_exam_full_score',
        'student_final_score',
        'state',
        'is_evaluated',
        'retake_attempt_number',
    )
    list_filter = ('state', 'is_evaluated')
    search_fields = ('student__name', 'course__name')


@admin.register(CarryCourse)
class CarryCourseAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'course',
        'final_exam_full_score',
        'student_final_score',
        'state',
        'is_evaluated',
        'from_structure',
        'to_structure'
    )
    list_filter = ('state', 'is_evaluated')
    search_fields = ('student__name', 'course__name')