from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Meal , DietRecommendation
from .serializers import MealSerializer , DietRecommendationSerializer


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


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
    def get(self, request, pk):
        meal = self.get_object(pk)
        if not meal:
            return Response({"error": "Meal not found"}, status=404)
        
        serializer = MealSerializer(meal)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Update a meal",
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description='Meal ID', type=openapi.TYPE_INTEGER, required=True)
        ],
        request_body=MealSerializer,
        responses={
            200: openapi.Response('Meal updated successfully', MealSerializer),
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


class DietRecommendationAPIView(APIView):
    pagination_class = StandardPagination

    @swagger_auto_schema(
        operation_description="Get all diet recommendations with pagination",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description='Page number', type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description='Items per page', type=openapi.TYPE_INTEGER),
        ],
        responses={200: openapi.Response('List of diet recommendations', DietRecommendationSerializer(many=True))}
    )
    def get(self, request):
        data = DietRecommendation.objects.filter(is_deleted=False).order_by('-created_at')
        
        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(data, request)
        
        serializer = DietRecommendationSerializer(paginated_data, many=True)
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        operation_description="Create a new diet recommendation",
        request_body=DietRecommendationSerializer,
        responses={
            201: openapi.Response('Diet recommendation created successfully', DietRecommendationSerializer),
            400: 'Validation error'
        }
    )
    def post(self, request):
        print(f"Creating diet plan with data: {request.data}")
        serializer = DietRecommendationSerializer(data=request.data)

        if serializer.is_valid():
            instance = serializer.save()
            print(f"Diet plan created successfully with ID: {instance.id}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        print(f"Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DietRecommendationDetailAPI(APIView):

    def get_object(self, pk):
        try:
            return DietRecommendation.objects.get(id=pk, is_deleted=False)
        except DietRecommendation.DoesNotExist:
            return None

    @swagger_auto_schema(
        operation_description="Retrieve a specific diet recommendation by ID",
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description='Diet Recommendation ID', type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={
            200: openapi.Response('Diet recommendation details', DietRecommendationSerializer),
            404: 'Diet recommendation not found'
        }
    )
    def get(self, request, pk):
        diet = self.get_object(pk)
        if not diet:
            return Response({"error": "Diet recommendation not found"}, status=404)
        
        serializer = DietRecommendationSerializer(diet)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Update a diet recommendation",
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description='Diet Recommendation ID', type=openapi.TYPE_INTEGER, required=True)
        ],
        request_body=DietRecommendationSerializer,
        responses={
            200: openapi.Response('Diet recommendation updated successfully', DietRecommendationSerializer),
            404: 'Diet recommendation not found'
        }
    )
    def put(self, request, pk):
        diet = self.get_object(pk)
        if not diet:
            return Response({"error": "Diet recommendation not found"}, status=404)
        
        serializer = DietRecommendationSerializer(diet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        operation_description="Delete a diet recommendation",
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description='Diet Recommendation ID', type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={
            200: 'Diet recommendation deleted successfully',
            404: 'Diet recommendation not found'
        }
    )
    def delete(self, request, pk):
        diet = self.get_object(pk)
        if not diet:
            return Response({"error": "Diet recommendation not found"}, status=404)
        
        diet.delete()
        return Response({"message": "Diet recommendation deleted successfully"})