from django.urls import path
from .views import AdminNotificationAPI

urlpatterns = [
    path("admin-notifications/", AdminNotificationAPI.as_view()),
]