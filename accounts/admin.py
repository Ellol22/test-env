# 📁 accounts/admin.py
from django.contrib import admin
from .models import Student, Doctor

# =========================================================
# 👨‍🎓 إدارة الطلاب Student Admin
# =========================================================
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'student_id',
        'national_id',
        'get_department',
        'get_year',
        'get_status',
        'get_academic_history',  # العمود الجديد للسجل الأكاديمي
    )
    list_filter = (
        'current_structure__department',
        'current_structure__year',
        'current_structure__status',
    )
    search_fields = ('name', 'student_id', 'national_id')
    list_select_related = ('current_structure',)

    # override save_model للتأكد من إضافة الهيكل للسجل مباشرة في admin
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.current_structure:
            new_struct = {
                'id': obj.current_structure.id,
                'department': obj.current_structure.department,
                'year': obj.current_structure.year,
                'status': obj.current_structure.status,
            }

            history = obj.structures_history or []
            if new_struct not in history:
                history.append(new_struct)
                # ⚠️ update بدون save إضافي لتجنب Recursion
                Student.objects.filter(pk=obj.pk).update(structures_history=history)
                print(f"[Admin] Added {new_struct} to history for {obj.name}")
            else:
                print(f"[Admin] {new_struct} already in history")
        else:
            print(f"[Admin] No current_structure set for {obj.name}")

    @admin.display(description="Department")
    def get_department(self, obj):
        return obj.current_structure.get_department_display() if obj.current_structure else "-"

    @admin.display(description="Year")
    def get_year(self, obj):
        return obj.current_structure.get_year_display() if obj.current_structure else "-"

    @admin.display(description="Status")
    def get_status(self, obj):
        return obj.current_structure.get_status_display() if obj.current_structure else "-"

    @admin.display(description="Academic History")
    def get_academic_history(self, obj):
        history = obj.structures_history or []
        if not history:
            return "-"
        return ", ".join([
            f"{h['department']} {h['year']} ({h['status']})"
            for h in history
        ])

# =========================================================
# 👨‍🏫 إدارة الدكاترة Doctor Admin
# =========================================================
@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'national_id', 'get_departments')
    list_filter = ('role', 'structures__department')
    search_fields = ('name', 'national_id')
    filter_horizontal = ('structures',)

    @admin.display(description="Departments")
    def get_departments(self, obj):
        departments = obj.structures.values_list('department', flat=True).distinct()
        return ", ".join(departments) if departments else "-"
