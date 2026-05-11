from django.urls import path
from .views import ApproveNutritionistAPIView

urlpatterns = [
    path(
        "approve/<int:pk>/",
        ApproveNutritionistAPIView.as_view(),
        name="approve-nutritionist"
    ),
]