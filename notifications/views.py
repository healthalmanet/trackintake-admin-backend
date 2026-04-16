from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Notification
from .serializers import NotificationSerializer


class AdminNotificationAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get all admin notifications",
        responses={200: openapi.Response('List of admin notifications')}
    )
    def get(self, request):

        notifications = Notification.objects.filter(type="admin").order_by("-created_at")

        serializer = NotificationSerializer(notifications, many=True)

        return Response({
            "notifications": serializer.data
        })