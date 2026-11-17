from rest_framework import serializers
from nutritionist.models import NutritionistProfile, PatientAssignment
from django.db.models import Count


class NutritionistProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    patient_count = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()

    class Meta:
        model = NutritionistProfile
        fields = [
            "id",
            "user_id",
            "user_name",
            "email",
            "nutritionist_type",
            "is_virtual_enabled",
            "is_verified",
            "experience_years",
            "degree",
            "license_number",
            "certificate",
            "patient_count"
        ]

    def get_user_name(self, obj):
        """Get user's full name"""
        return obj.user.full_name if obj.user else "Unknown"

    def get_email(self, obj):
        """Get user's email"""
        return obj.user.email if obj.user else ""

    def get_user_id(self, obj):
        """Get user ID"""
        return obj.user.id if obj.user else None

    def get_patient_count(self, obj):
        """Get count of assigned patients"""
        try:
            return PatientAssignment.objects.filter(nutritionist_id=obj.user_id).count()
        except:
            return 0


class PatientAssignmentSerializer(serializers.ModelSerializer):
    nutritionist_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = PatientAssignment
        fields = [
            "id",
            "nutritionist_id",
            "nutritionist_name",
            "patient_id",
            "patient_name",
            "assigned_at"
        ]

    def get_nutritionist_name(self, obj):
        """Get nutritionist's full name"""
        try:
            from users.models import UserProfile
            nutritionist = UserProfile.objects.get(id=obj.nutritionist_id)
            return nutritionist.full_name
        except:
            return "Unknown"

    def get_patient_name(self, obj):
        """Get patient's full name"""
        try:
            from users.models import UserProfile
            patient = UserProfile.objects.get(id=obj.patient_id)
            return patient.full_name
        except:
            return "Unknown"