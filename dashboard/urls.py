from django.urls import path
from .views import (
    DashboardOverviewAPI,
    TotalUsersAPI,
    ActiveUsersAPI,
    TotalRevenueAPI,
    PendingAppointmentsAPI,
    UserGrowthAPI,
    PlanDistributionAPI,
    RecentActivityAPI,
    RevenueByPlanAPI,
    RevenueDetailsAPI,
    UsersWithPaymentNoProfileAPI
)
from .appointment_views import AppointmentListAPI, AppointmentDetailAPI
from .blog_views import BlogListCreateAPI, BlogDetailAPI, BlogImageUploadAPI
from .progress_views import ProgressLogsAPI
from .payables_views import PayablesListAPI, PayableDetailUpdateAPI
from .approvals_views import ApprovalsListAPI, ApprovalActionAPI
from .settings_views import InhousePricingSettingsAPI
from .assignment_views import PatientAssignmentListAPI, BatchAssignPatientsAPI, UnassignPatientAPI

urlpatterns = [
    path("overview/", DashboardOverviewAPI.as_view()),
    path("settings/inhouse-pricing/", InhousePricingSettingsAPI.as_view(), name="settings-inhouse-pricing"),
    path("assignments/", PatientAssignmentListAPI.as_view(), name="assignments-list"),
    path("assignments/batch-assign/", BatchAssignPatientsAPI.as_view(), name="assignments-batch-assign"),
    path("assignments/unassign/", UnassignPatientAPI.as_view(), name="assignments-unassign"),
    path("payables/", PayablesListAPI.as_view()),
    path("payables/<int:pk>/", PayableDetailUpdateAPI.as_view()),
    path("approvals/", ApprovalsListAPI.as_view()),
    path("approvals/<int:pk>/", ApprovalActionAPI.as_view()),
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
    path("appointments/", AppointmentListAPI.as_view()),
    path("appointments/<int:pk>/", AppointmentDetailAPI.as_view()),
    path("blogs/", BlogListCreateAPI.as_view()),
    path("blogs/upload-image/", BlogImageUploadAPI.as_view(), name="blog-image-upload"),
    path("blogs/<int:pk>/", BlogDetailAPI.as_view()),
    path("progress-logs/", ProgressLogsAPI.as_view()),
]
