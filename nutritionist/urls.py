from django.urls import path
from .views import (
    ApproveNutritionistAPIView,
    NutritionistCreateAPIView,
    NutritionistListAPIView,
    PatientAssignmentListAPIView
)

urlpatterns = [
    path(
        "list/",
        NutritionistListAPIView.as_view(),
        name="nutritionist-list"
    ),
    path(
        "assignments/",
        PatientAssignmentListAPIView.as_view(),
        name="patient-assignments"
    ),
    path(
        "approve/<int:pk>/",
        ApproveNutritionistAPIView.as_view(),
        name="approve-nutritionist"
    ),
    path(
        "create/",
        NutritionistCreateAPIView.as_view(),
        name="create-nutritionist"
    ),
]