# 📁 courses\management\commands\load_ds_courses.py
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
# 🧠 Mappers
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
    help = 'Load Data Science courses from JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/ds_courses.json'
        )

        parser.add_argument(
            '--clear',
            action='store_true'
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

        ds_data = data.get('data_science_department', {})

        # =========================
        # 🗑️ Optional Clear
        # =========================
        if kwargs['clear']:
            deleted, _ = Course.objects.filter(
                structure__department=DepartmentChoices.DATA
            ).delete()

            self.stdout.write(self.style.WARNING(
                f"🗑️ Deleted {deleted} old courses"
            ))

        count = 0

        # =========================
        # 🔁 Loop
        # =========================
        for year_key, year_data in ds_data.items():
            academic_year = map_academic_year(year_key)

            if not academic_year:
                self.stdout.write(self.style.WARNING(
                    f"⚠️ Invalid year: {year_key}"
                ))
                continue

            # =========================
            # 📦 Ensure structure exists
            # =========================
            structure, created = StudentStructure.objects.get_or_create(
                department=DepartmentChoices.DATA,
                year=academic_year,
                status=StudentStatusChoices.ACTIVE
            )

            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"📦 Created structure: {structure}"
                ))

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
                for name in subjects:
                    obj, created = Course.objects.get_or_create(
                        name=name,
                        structure=structure,
                        semester=semester,
                        defaults={
                            "course_type": "normal"
                        }
                    )

                    if created:
                        count += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Done! Added {count} Data Science courses"
        ))