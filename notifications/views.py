from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Notification
from .serializers import NotificationSerializer
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db.models import Q
from .models import UserProfile


class AdminNotificationAPI(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Get notifications by type (admin/user/nutritionist)",
        manual_parameters=[
            openapi.Parameter(
                name='type',
                in_=openapi.IN_QUERY,
                description="admin | user | nutritionist (default: admin)",
                type=openapi.TYPE_STRING,
                required=False,
            )
        ],
        responses={200: openapi.Response('List of notifications')}
    )
    def get(self, request):
        notif_type = request.query_params.get('type', 'admin')

        user_profile = None
        if request.user.is_authenticated:
            user_profile = UserProfile.objects.filter(user=request.user).first()

        notifications = Notification.objects.filter(
            type=notif_type
        ).order_by("-created_at")

        serializer = NotificationSerializer(notifications, many=True)

        return Response({
            "type": notif_type,
            "total": notifications.count(),
            "unread_count": notifications.filter(is_read=False).count(),
            "notifications": serializer.data
        })


# ✅ Single notification mark as read
class MarkNotificationReadAPI(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Mark a single notification as read",
        responses={
            200: "Notification marked as read",
            404: "Notification not found"
        }
    )
    def patch(self, request, notification_id):
        try:
            user_profile = None
            if request.user.is_authenticated:
                user_profile = UserProfile.objects.filter(user=request.user).first()

            # ✅ Fixed: Q filter same as GET API
            notification = Notification.objects.get(
                id=notification_id,
            )
            notification.is_read = True
            notification.save()
            return Response({
                "message": "Notification marked as read",
                "id": notification_id
            }, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found"},
                status=status.HTTP_404_NOT_FOUND
            )


# ✅ Mark ALL notifications as read
class MarkAllNotificationsReadAPI(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Mark all notifications as read by type",
        manual_parameters=[
            openapi.Parameter(
                name='type',
                in_=openapi.IN_QUERY,
                description="admin | user | nutritionist (default: admin)",
                type=openapi.TYPE_STRING,
                required=False,
            )
        ],
        responses={200: "All notifications marked as read"}
    )
    def patch(self, request):
        notif_type = request.query_params.get('type', 'admin')
        
        updated = Notification.objects.filter(
            type=notif_type,
            is_read=False
        ).update(is_read=True)

        return Response({
            "message": "All notifications marked as read",
            "type": notif_type,
            "updated_count": updated
        }, status=status.HTTP_200_OK)