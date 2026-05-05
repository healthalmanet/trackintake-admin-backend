from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    # Add computed fields for frontend compatibility
    title = serializers.SerializerMethodField()
    notif_type = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'type', 'notif_type', 'user_id', 'is_read', 'created_at']
    
    def get_title(self, obj):
        """Extract title from message"""
        # Parse message to extract title (first line or first 50 chars)
        lines = obj.message.split('\n')
        return lines[0][:100] if lines else "Notification"
    
    def get_notif_type(self, obj):
        """Map type to notif_type"""
        return 'ADMIN' if obj.type == 'admin' else 'USER'
    
    def get_type(self, obj):
        """Determine type from message"""
        msg_lower = obj.message.lower()
        if 'registered' in msg_lower or 'registration' in msg_lower:
            return 'Registration'
        elif 'purchased' in msg_lower or 'purchase' in msg_lower:
            return 'Plan Purchase'
        elif 'assigned' in msg_lower or 'assignment' in msg_lower:
            return 'Assignment'
        elif 'expir' in msg_lower:
            return 'Expiry'
        return 'Registration'
    
    def get_user_id(self, obj):
        """Get user_id from related user"""
        return obj.user.id if obj.user else None