from django.urls import path
<<<<<<< HEAD
from .views import SubscriptionPlanAPI, UpdateSubscriptionPlanAPI,SubscriptionUsageAPI,PaymentAnalyticsAPI, PlanDurationTrackingAPI,get_subscription_plan
from .utils import get_user_plan_and_upgrade
=======
from .views import SubscriptionPlanAPI, UpdateSubscriptionPlanAPI,SubscriptionUsageAPI,PaymentAnalyticsAPI, PlanDurationTrackingAPI

>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
urlpatterns = [

    path("plans/", SubscriptionPlanAPI.as_view()),
    path("plans/update/<int:pk>/", UpdateSubscriptionPlanAPI.as_view()),
    path("usage/", SubscriptionUsageAPI.as_view()),
    path("payments/analytics/", PaymentAnalyticsAPI.as_view()),
    path("plans/duration/", PlanDurationTrackingAPI.as_view()),
<<<<<<< HEAD
    path("api/subscription/", get_subscription_plan)
    
=======
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
]