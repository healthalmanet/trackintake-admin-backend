from django.urls import path
from .views import (
    RevenueDetailsAPI,
    TotalUsersAPI,
    ActiveUsersAPI,
    TotalRevenueAPI,
    PendingAppointmentsAPI,
    UserGrowthAPI,
    PlanDistributionAPI,
    RecentActivityAPI,
    RevenueByPlanAPI,
    RevenueDetailsAPI,
    UsersWithPaymentNoProfileAPI,
    UsersWithPaymentNoProfileAPI
)

urlpatterns = [

    path("total-users/", TotalUsersAPI.as_view()),
    path("active-users/", ActiveUsersAPI.as_view()),
    path("total-revenue/", TotalRevenueAPI.as_view()),
    path("pending-appointments/", PendingAppointmentsAPI.as_view()),
    path("user-growth/", UserGrowthAPI.as_view()),
    path("plan-distribution/", PlanDistributionAPI.as_view()),
    path("recent-activity/", RecentActivityAPI.as_view()),
    path("revenue-by-plan/", RevenueByPlanAPI.as_view()),
    path("revenue-details/", RevenueDetailsAPI.as_view()),
    path("missing-profile-users/", UsersWithPaymentNoProfileAPI.as_view()),
]