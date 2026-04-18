<<<<<<< HEAD
from django.urls import path
from users.views import (
    # AssignNutritionistAPI,
    AvailableNutritionistsView,
    NutritionistListAPIView,
    UserListCreateView,
    UserDetailView,
    UserPlanNotificationAPI,
    UsersWithPaymentNoProfileAPI,
    UserHealthProfileAPI,
    SubscribedUsersAPI,
    # AssignablePatientListAPI,
)

urlpatterns = [
    path('create-user', UserListCreateView.as_view(), name='user-create'),
    path("<int:user_id>/", UserDetailView.as_view(), name='user-detail'),
    path("<int:user_id>/health-profile/", UserHealthProfileAPI.as_view(), name='user-health-profile'),
    path("payment-no-profile/", UsersWithPaymentNoProfileAPI.as_view()),
    path("plan-renewal/", UserPlanNotificationAPI.as_view(), name='plan-renewal-notifications'),
    path("subscribed/", SubscribedUsersAPI.as_view(), name='subscribed-users'),
     path('nutritionists/available/', AvailableNutritionistsView.as_view(), name='available-nutritionists'),
     path('user-list-create/', UserListCreateView.as_view(), name='user-list-create'),
     path('nutritionists/', NutritionistListAPIView.as_view(), name='nutritionist-list'),
     

]
=======
from django.contrib import admin
from django.urls import path
from rest_framework.permissions import AllowAny
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from users.views import (
    UserListCreateView,
    UserDetailView,
    UserStatusView,
    DashboardStatsView
)

schema_view = get_schema_view(
    openapi.Info(
        title="User API",
        default_version='v1',
        description="User management API",
    ),
    public=True,
    permission_classes=[AllowAny],
)

urlpatterns = [
    # admin path is not needed here, because project root already exposes /admin/

    path('', UserListCreateView.as_view(), name='user-list-create'),
    path('<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('<int:pk>/status/', UserStatusView.as_view(), name='user-status'),
    path('stats/', DashboardStatsView.as_view(), name='user-dashboard-stats'),

    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0)),
]
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
