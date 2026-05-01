from django.urls import path
from .views import AdminNotificationAPI, MarkNotificationReadAPI, MarkAllNotificationsReadAPI

urlpatterns = [
    path("admin-notifications/", AdminNotificationAPI.as_view()),
    path("admin-notifications/mark-all-read/", MarkAllNotificationsReadAPI.as_view()),  # ✅ static first
    path("admin-notifications/<int:notification_id>/read/", MarkNotificationReadAPI.as_view()),  # ✅ dynamic after
]