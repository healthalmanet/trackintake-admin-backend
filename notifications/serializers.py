from rest_framework import serializers


class NotificationSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    message = serializers.CharField()
    type = serializers.CharField()
    notif_type = serializers.CharField()
    user_id = serializers.IntegerField(allow_null=True, required=False)
    is_read = serializers.BooleanField(default=False)
    created_at = serializers.DateTimeField(allow_null=True, required=False)
