from rest_framework import serializers
from .models import Meal, DietRecommendation
from django.utils import timezone
from users.models import UserProfile


class MealSerializer(serializers.ModelSerializer):

    class Meta:
        model = Meal
        fields = "__all__"


class DietRecommendationSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DietRecommendation
        fields = '__all__'
    
    def get_user_name(self, obj):
        """Get the user's full name from user_id"""
        try:
            user = UserProfile.objects.get(id=obj.user_id)
            return user.full_name or f"User #{obj.user_id}"
        except UserProfile.DoesNotExist:
            return f"User #{obj.user_id}"
    
    def create(self, validated_data):
        """Override create to set timestamps if not provided"""
        now = timezone.now()
        if 'created_at' not in validated_data or not validated_data['created_at']:
            validated_data['created_at'] = now
        if 'updated_at' not in validated_data or not validated_data['updated_at']:
            validated_data['updated_at'] = now
        return super().create(validated_data)
    
    def validate(self, data):
        """Validate required fields"""
        if not data.get('user_id'):
            raise serializers.ValidationError("user_id is required")
        if not data.get('for_week_starting'):
            raise serializers.ValidationError("for_week_starting is required")
        if not data.get('status'):
            raise serializers.ValidationError("status is required")
        if not data.get('meals'):
            raise serializers.ValidationError("meals is required")
        return data        