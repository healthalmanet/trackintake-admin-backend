from rest_framework import serializers


class MealSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    meal_name = serializers.CharField(required=True)
    calories = serializers.IntegerField(default=0)
    protein = serializers.FloatField(default=0.0)
    carbohydrates = serializers.FloatField(default=0.0)
    fat = serializers.FloatField(default=0.0)
    category = serializers.CharField(default="breakfast")
    created_at = serializers.DateTimeField(read_only=True, required=False)


class DietRecommendationSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(required=True)
    user_name = serializers.CharField(allow_null=True, required=False)
    for_week_starting = serializers.DateField(required=True)
    status = serializers.CharField(required=True)
    meals = serializers.JSONField(required=True)
    nutritionist_comment = serializers.CharField(allow_null=True, required=False)
    reviewed_by_id = serializers.IntegerField(allow_null=True, required=False)
    is_deleted = serializers.BooleanField(default=False)
    created_at = serializers.DateTimeField(read_only=True, required=False)
    updated_at = serializers.DateTimeField(read_only=True, required=False)
