# 📁 dashboard/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User

from accounts.models import Doctor, Student
from courses.models import Course
from structure.models import StudentStructure
from .models import Announcement, Dash, Notifications


# =========================================================
# 👨‍🎓 Student Serializer
# =========================================================

class StudentSerializer(serializers.ModelSerializer):
    username   = serializers.CharField(source='user.username', read_only=True)
    email      = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    structure  = serializers.PrimaryKeyRelatedField(read_only=True)
    image      = serializers.SerializerMethodField()

    class Meta:
        model  = Student
        fields = ['username', 'first_name', 'email', 'name', 'mobile', 'national_id', 'structure', 'image']

    def get_image(self, obj):
        try:
            return obj.dash.image.url if obj.dash and obj.dash.image else None
        except Exception:
            return None


# =========================================================
# 👨‍🏫 Doctor Serializer
# =========================================================

class DoctorSerializer(serializers.ModelSerializer):
    email       = serializers.EmailField(source='user.email', read_only=True)
    image       = serializers.SerializerMethodField()
    departments = serializers.SerializerMethodField()
    courses     = serializers.SerializerMethodField()

    class Meta:
        model  = Doctor
        fields = ['name', 'national_id', 'mobile', 'image', 'email', 'departments', 'courses']

    def get_image(self, obj):
        try:
            return obj.dash.image.url if obj.dash and obj.dash.image else None
        except Exception:
            return None

    def get_departments(self, obj):
        """
        department في الموديل هو TextChoices مش FK،
        فبنجيب الـ display value من الـ structures المرتبطة بالدكتور.
        """
        return list(set(
            s.get_department_display()
            for s in obj.structures.all()
        ))

    def get_courses(self, obj):
        """
        المواد المرتبطة بالدكتور عن طريق GradeSheet.
        """
        from grades.models import GradeSheet
        sheets = GradeSheet.objects.filter(doctor=obj).select_related('course')
        return [{"id": s.course.id, "name": s.course.name} for s in sheets]


# =========================================================
# 📢 Announcement Serializer
# =========================================================

class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model  = Announcement
        fields = '__all__'
        extra_kwargs = {
            'created_by': {'required': False, 'write_only': True},
            'created_at': {'required': False},
        }

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def to_internal_value(self, data):
        """قبول أسماء حقول بديلة من الفرونت"""
        modified = data.copy()
        if 'message' in modified:
            modified['content'] = modified.pop('message')
        if 'date' in modified:
            modified['created_at'] = modified.pop('date')
        return super().to_internal_value(modified)


# =========================================================
# 🔔 Notification Serializer
# =========================================================

class NotificationSerializer(serializers.ModelSerializer):
    # write: بيبعت course_id
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        source='course',
        write_only=True
    )
    # read: بيرجع اسم المادة
    course = serializers.CharField(source='course.name', read_only=True)
    # read: اسم الدكتور
    sender = serializers.CharField(source='sender.user.username', read_only=True)

    class Meta:
        model  = Notifications
        fields = ['id', 'title', 'message', 'created_at', 'course_id', 'course', 'sender']