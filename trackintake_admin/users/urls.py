from django.urls import path
from .views import forgot_password, reset_password
from users.views import(
    AssignNutritionistAPI,
    # AvailableNutritionistsView,
    NutritionistListAPIView,
    UserListCreateView,
    UserDetailView,
    UserPlanNotificationAPI,
    UsersWithPaymentNoProfileAPI,
    UserHealthProfileAPI,
    SubscribedUsersAPI,
    # AssignablePatientListAPI,
    AvailableNutritionistsView,
    EligibleUsersForNutritionistAPI,
    DebugSubscriptionsAPI,
)   

urlpatterns = [
    path('create-user', UserListCreateView.as_view(), name='user-create'),
    path("<int:user_id>/", UserDetailView.as_view(), name='user-detail'),
    path("<int:user_id>/health-profile/", UserHealthProfileAPI.as_view(), name='user-health-profile'),
    path("payment-no-profile/", UsersWithPaymentNoProfileAPI.as_view()),
    path("plan-renewal/", UserPlanNotificationAPI.as_view(), name='plan-renewal-notifications'),
    path("subscribed/", SubscribedUsersAPI.as_view(), name='subscribed-users'),
    path('user-list-create/', UserListCreateView.as_view(), name='user-list-create'),
    path('nutritionists/', NutritionistListAPIView.as_view(), name='nutritionist-list'),
    path('available-nutritionists/', AvailableNutritionistsView.as_view(), name='available-nutritionists'),
    path('eligible-users-for-nutritionist/', EligibleUsersForNutritionistAPI.as_view(), name='eligible-users-for-nutritionist'),
    path('debug-subscriptions/', DebugSubscriptionsAPI.as_view(), name='debug-subscriptions'),
    path('assign-nutritionist/', AssignNutritionistAPI.as_view(), name='assign-nutritionist'),
    path("forgot-password/", forgot_password),
    path("reset-password/<uidb64>/<token>/", reset_password),
]