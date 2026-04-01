# 📁 courses\management\commands\seed_structures.py
from django.core.management.base import BaseCommand
from structure.models import (
    StudentStructure,
    DepartmentChoices,
    AcademicYearChoices,
    StudentStatusChoices
)


class Command(BaseCommand):
    help = "Seed all StudentStructures for all departments"

    def handle(self, *args, **kwargs):

        departments = [
            DepartmentChoices.AI,
            DepartmentChoices.DATA,
            DepartmentChoices.CYBER,
            DepartmentChoices.AUTOTRONICS,
            DepartmentChoices.MECHATRONICS,
            DepartmentChoices.GARMENT_MANUFACTURING,
            DepartmentChoices.CONTROL_SYSTEMS,
        ]

        years = [
            AcademicYearChoices.FIRST,
            AcademicYearChoices.SECOND,
            AcademicYearChoices.THIRD,
            AcademicYearChoices.FOURTH,
        ]

        statuses = [
            StudentStatusChoices.ACTIVE,
            StudentStatusChoices.SUMMER,
            StudentStatusChoices.RETAKE_YEAR,
            StudentStatusChoices.DROPPED_OUT,
            StudentStatusChoices.GRADUATED,
        ]

        created_count = 0

        for dept in departments:
            for year in years:
                for status in statuses:

                    obj, created = StudentStructure.objects.get_or_create(
                        department=dept,
                        year=year,
                        status=status
                    )

                    if created:
                        created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Seed completed! Created {created_count} structures"
        ))