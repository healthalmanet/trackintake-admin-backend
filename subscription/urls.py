from django.urls import path
from .views import SubscriptionPlanAPI, UpdateSubscriptionPlanAPI, SubscriptionUsageAPI, PaymentAnalyticsAPI, PlanDurationTrackingAPI
urlpatterns = [

    path("plans/", SubscriptionPlanAPI.as_view()),
    path("plans/update/<int:pk>/", UpdateSubscriptionPlanAPI.as_view()),
    path("usage/", SubscriptionUsageAPI.as_view()),
    path("payments/analytics/", PaymentAnalyticsAPI.as_view()),
    path("plans/duration/", PlanDurationTrackingAPI.as_view()),
]