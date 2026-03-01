# 📁 courses/admin.py
from django.contrib import admin
from .models import Course, CourseSectionAssistant


# =========================================================
# 🧾 إدارة المواد الدراسية Course Admin
# =========================================================
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'get_department',
        'get_year',
        'semester',
        'course_type',
        'doctor',
    )
    list_filter = (
        'structure__department',
        'structure__year',
        'semester',
        'course_type',
    )
    search_fields = ('name', 'doctor__name')
    list_select_related = ('structure', 'doctor')

    @admin.display(description="Department")
    def get_department(self, obj):
        return obj.structure.get_department_display()

    @admin.display(description="Year")
    def get_year(self, obj):
        return obj.structure.get_year_display()


# =========================================================
# 👨‍🏫 إدارة السكاشن والمعيدين Course Section Assistants
# =========================================================
@admin.register(CourseSectionAssistant)
class CourseSectionAssistantAdmin(admin.ModelAdmin):
    list_display = ('course', 'section', 'assistant', 'get_department', 'get_year')
    list_filter = (
        'course__structure__department',
        'course__structure__year',
        'course__semester',
    )
    search_fields = ('course__name', 'assistant__name')

    @admin.display(description="Department")
    def get_department(self, obj):
        return obj.course.structure.get_department_display()

    @admin.display(description="Year")
    def get_year(self, obj):
        return obj.course.structure.get_year_display()
