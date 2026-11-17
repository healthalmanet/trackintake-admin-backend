from rest_framework import serializers


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(allow_null=True, required=False)
    role = serializers.CharField(default="user")
    plan = serializers.CharField(allow_null=True, required=False)
    nutritionist_type = serializers.CharField(allow_null=True, required=False)
    is_nutritionist_approved = serializers.BooleanField(default=False)
    is_active = serializers.BooleanField(default=True)
    is_admin = serializers.BooleanField(default=False)
    date_joined = serializers.DateTimeField(read_only=True, required=False)


class UserWriteSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(allow_null=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    role = serializers.CharField(default="user")
    plan = serializers.CharField(allow_null=True, required=False)
    is_active = serializers.BooleanField(default=True)


class AssignNutritionistSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    nutritionist_id = serializers.IntegerField()
