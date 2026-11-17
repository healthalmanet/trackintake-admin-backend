from django.urls import path
from .views import (
    AdminNotificationAPI,
    MarkNotificationReadAPI,
    MarkAllNotificationsReadAPI,
    TriggerNotificationEventAPI,
)

urlpatterns = [
    path("admin-notifications/", AdminNotificationAPI.as_view()),
    path("admin-notifications/mark-all-read/", MarkAllNotificationsReadAPI.as_view()),
    path("admin-notifications/trigger-event/", TriggerNotificationEventAPI.as_view()),
    path("admin-notifications/test-event/", TriggerNotificationEventAPI.as_view()),
    path("admin-notifications/<int:notification_id>/read/", MarkNotificationReadAPI.as_view()),
]