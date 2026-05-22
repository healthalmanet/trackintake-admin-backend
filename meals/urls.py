from django.urls import path
from .views import DietRecommendationAPIView, DietRecommendationDetailAPI, MealListCreateAPI, MealDetailAPI, DietStatsAPIView


urlpatterns = [

    path("meals/", MealListCreateAPI.as_view()),

    path("meals/<int:pk>/", MealDetailAPI.as_view()),
    path("diet-recommendations/",
        DietRecommendationAPIView.as_view(),
        name='diet-recommendations'),
    path("diet-recommendations/<int:pk>/",
        DietRecommendationDetailAPI.as_view(),
        name='diet-recommendations-detail'),
    path("diet-recommendations/stats/",
        DietStatsAPIView.as_view(),
        name='diet-recommendations-stats'),
]