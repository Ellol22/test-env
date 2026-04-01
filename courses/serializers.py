# 📁 courses/serializers.py
from rest_framework import serializers
from .models import Course

class CourseSerializer(serializers.ModelSerializer):
    semester = serializers.CharField(source='get_semester_display')

    class Meta:
        model = Course
        fields = ['id', 'name', 'semester']