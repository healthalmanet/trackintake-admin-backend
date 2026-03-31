from rest_framework import serializers
from .models import UserProfile


class UserSerializer(serializers.ModelSerializer):

    plan = serializers.CharField(source='role')

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "full_name",
            "email",
            "plan",
            "is_active",
            "date_joined"
        ]


class UserWriteSerializer(serializers.ModelSerializer):

    plan = serializers.CharField(source='role')

    class Meta:
        model = UserProfile
        fields = [
            "full_name",
            "email",
            "plan",
            "is_active"
        ]