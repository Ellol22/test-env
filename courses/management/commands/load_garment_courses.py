# 📁 courses\management\commands\load_garment_courses.py
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
    help = 'Reload Garment Technology department courses from JSON (clear old and add new)'

    def handle(self, *args, **kwargs):
        json_path = 'data/garment_courses.json'

        # =========================
        # 📥 Load JSON
        # =========================
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ File not found: {json_path}"))
            return

        garment_courses = data.get('garment_technology', {})

        # =========================
        # 🗑️ Delete old courses
        # =========================
        deleted, _ = Course.objects.filter(
            structure__department=DepartmentChoices.GARMENT_MANUFACTURING
        ).delete()

        self.stdout.write(self.style.WARNING(
            f"🗑️ Deleted {deleted} old courses from Garment Technology department"
        ))

        count = 0

        # =========================
        # 🔁 Loop years
        # =========================
        for year_key, year_data in garment_courses.items():
            academic_year = map_academic_year(year_key)

            if not academic_year:
                self.stdout.write(self.style.WARNING(
                    f"⚠️ Invalid academic year: {year_key}"
                ))
                continue

            # =========================
            # 📦 FIXED STRUCTURE QUERY (NO SEMESTER ❌)
            # =========================
            try:
                structure = StudentStructure.objects.get(
                    department=DepartmentChoices.GARMENT_MANUFACTURING,
                    year=academic_year,
                    status=StudentStatusChoices.ACTIVE
                )
            except StudentStructure.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"⚠️ No StudentStructure found for Garment Technology, {academic_year}"
                ))
                continue

            # =========================
            # 📚 Terms
            # =========================
            for term_key, courses in year_data.items():
                semester = map_semester(term_key)

                if not semester:
                    self.stdout.write(self.style.WARNING(
                        f"⚠️ Invalid semester: {term_key}"
                    ))
                    continue

                # =========================
                # ➕ Courses
                # =========================
                for name in courses:
                    Course.objects.create(
                        name=name,
                        structure=structure,
                        semester=semester
                    )
                    count += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Successfully added {count} new courses for Garment Technology department"
        ))