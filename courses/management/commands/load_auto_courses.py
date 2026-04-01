# 📁 courses\management\commands\load_auto_courses.py
from django.core.management.base import BaseCommand
import json

from courses.models import Course, SemesterChoices
from structure.models import (
    DepartmentChoices,
    AcademicYearChoices,
    StudentStructure,
    StudentStatusChoices
)


# =========================
# 🧠 Mapping Helpers
# =========================

def map_academic_year(year_key):
    return {
        'year_1': AcademicYearChoices.FIRST,
        'year_2': AcademicYearChoices.SECOND,
        'year_3': AcademicYearChoices.THIRD,
        'year_4': AcademicYearChoices.FOURTH,
    }.get(year_key)


def map_semester(term_key):
    return {
        'term_1': SemesterChoices.FIRST,
        'term_2': SemesterChoices.SECOND,
    }.get(term_key)


# =========================
# 🚀 Command
# =========================

class Command(BaseCommand):
    help = 'Load Autotronics courses from JSON into DB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/auto_courses.json',
            help='Path to JSON file'
        )

        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing Autotronics courses before loading'
        )

    def handle(self, *args, **kwargs):
        json_path = kwargs['file']

        # =========================
        # 📥 Load JSON
        # =========================
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ File not found: {json_path}"))
            return

        auto_data = data.get('autotronics', {})

        # =========================
        # 🗑️ Optional Clear
        # =========================
        if kwargs['clear']:
            deleted, _ = Course.objects.filter(
                structure__department=DepartmentChoices.AUTOTRONICS
            ).delete()

            self.stdout.write(self.style.WARNING(
                f"🗑️ Deleted {deleted} existing courses"
            ))

        count = 0

        # =========================
        # 🔁 Loop JSON
        # =========================
        for year_key, year_data in auto_data.items():
            academic_year = map_academic_year(year_key)

            if not academic_year:
                self.stdout.write(self.style.WARNING(
                    f"⚠️ Invalid year: {year_key}"
                ))
                continue

            # 🔍 get structure
            structure = StudentStructure.objects.filter(
                department=DepartmentChoices.AUTOTRONICS,
                year=academic_year,
                status=StudentStatusChoices.ACTIVE
            ).first()

            if not structure:
                self.stdout.write(self.style.WARNING(
                    f"⚠️ No structure found for {academic_year}"
                ))
                continue

            # =========================
            # 📚 Terms
            # =========================
            for term_key, subjects in year_data.items():
                semester = map_semester(term_key)

                if not semester:
                    self.stdout.write(self.style.WARNING(
                        f"⚠️ Invalid term: {term_key}"
                    ))
                    continue

                # =========================
                # 📌 Courses
                # =========================
                for subject_name in subjects:
                    obj, created = Course.objects.get_or_create(
                        name=subject_name,
                        structure=structure,
                        semester=semester,
                        defaults={
                            "course_type": "normal"
                        }
                    )

                    if created:
                        count += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Done! Added {count} courses"
        ))