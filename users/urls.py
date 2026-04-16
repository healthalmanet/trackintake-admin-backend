from django.urls import path
from users.views import (
    AssignNutritionistAPI,
    NutritionistListAPIView,
    UserListCreateView,
    UserDetailView,
    UserPlanNotificationAPI,
    UsersWithPaymentNoProfileAPI,
    UserHealthProfileAPI,
    SubscribedUsersAPI,
)

urlpatterns = [
    path('', UserListCreateView.as_view(), name='user-list-create'),
    path('create-user', UserListCreateView.as_view(), name='user-create'),
    path("<int:user_id>/", UserDetailView.as_view(), name='user-detail'),
    path("<int:user_id>/health-profile/", UserHealthProfileAPI.as_view(), name='user-health-profile'),
    path("assign-nutritionist/", AssignNutritionistAPI.as_view(), name='assign-nutritionist'),
    path("payment-no-profile/", UsersWithPaymentNoProfileAPI.as_view()),
    path('nutritionists/', NutritionistListAPIView.as_view(), name='nutritionist-list'),
    path("plan-renewal/", UserPlanNotificationAPI.as_view(), name='plan-renewal-notifications'),
    path("subscribed/", SubscribedUsersAPI.as_view(), name='subscribed-users'),
]
