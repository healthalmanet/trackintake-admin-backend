from django.urls import path
from .views import AdminNotificationAPI

urlpatterns = [
    path("", AdminNotificationAPI.as_view()),
    path("admin-notifications/", AdminNotificationAPI.as_view()),
]
