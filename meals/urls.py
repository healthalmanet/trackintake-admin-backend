from django.urls import path
from .views import MealListCreateAPI, MealDetailAPI


urlpatterns = [

    path("meals/", MealListCreateAPI.as_view()),

    path("meals/<int:pk>/", MealDetailAPI.as_view()),

]