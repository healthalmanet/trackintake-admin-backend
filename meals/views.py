from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Meal
from .serializers import MealSerializer


# ---------- LIST + CREATE ----------

class MealListCreateAPI(APIView):

    @swagger_auto_schema(
        operation_description="List all meals",
        responses={200: openapi.Response('List of meals', MealSerializer(many=True))}
    )
    def get(self, request):

        meals = Meal.objects.all()

        serializer = MealSerializer(meals, many=True)

        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Create a new meal",
        request_body=MealSerializer,
        responses={
            201: openapi.Response('Meal created successfully', MealSerializer),
            400: 'Validation error'
        }
    )
    def post(self, request):

        serializer = MealSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- UPDATE / DELETE ----------

class MealDetailAPI(APIView):

    def get_object(self, pk):

        try:
            return Meal.objects.get(id=pk)
        except Meal.DoesNotExist:
            return None

    @swagger_auto_schema(
        operation_description="Retrieve a specific meal by ID",
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description='Meal ID', type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={
            200: openapi.Response('Meal details', MealSerializer),
            404: 'Meal not found'
        }
    )
    def put(self, request, pk):

        meal = self.get_object(pk)

        if not meal:
            return Response({"error": "Meal not found"}, status=404)

        serializer = MealSerializer(meal, data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)

        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        operation_description="Delete a meal",
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description='Meal ID', type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={
            200: 'Meal deleted successfully',
            404: 'Meal not found'
        }
    )
    def delete(self, request, pk):

        meal = self.get_object(pk)

        if not meal:
            return Response({"error": "Meal not found"}, status=404)

        meal.delete()

        return Response({"message": "Meal deleted successfully"})