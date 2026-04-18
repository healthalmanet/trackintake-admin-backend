from rest_framework import serializers
from .models import UserProfile


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "full_name",
            "email",
            "role",
            "is_active",
            "date_joined"
        ]


class UserWriteSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = UserProfile
        fields = [
            "full_name",
            "email",
            "password",
            "role",
            "is_active"
        ]

    def create(self, validated_data):
        """Override create to handle password properly"""
        user = UserProfile.objects.create(
            full_name=validated_data['full_name'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data['role'],
            is_active=validated_data.get('is_active', True)
        )
        return user
    
from rest_framework import serializers

class AssignNutritionistSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    nutritionist_id = serializers.IntegerField()