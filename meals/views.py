from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q

from .models import Meal , DietRecommendation
from .serializers import MealSerializer , DietRecommendationSerializer
from users.models import UserProfile


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
        operation_description="Get all diet recommendations with pagination and search",
        manual_parameters=[
            openapi.Parameter('search',
                openapi.IN_QUERY,
                description='Search by user name or nutritionist name',
                type=openapi.TYPE_STRING),
            openapi.Parameter('nutritionist_id',
                openapi.IN_QUERY,
                description='Filter by nutritionist ID',
                type=openapi.TYPE_INTEGER),
            openapi.Parameter('status',
                openapi.IN_QUERY,
                description='Filter by status (approved, pending, failed, rejected, etc.)',
                type=openapi.TYPE_STRING),
            openapi.Parameter('page',
                openapi.IN_QUERY,
                description='Page number',
                type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size',
                openapi.IN_QUERY,
                description='Items per page',
                type=openapi.TYPE_INTEGER),
        ],
    )
    def get(self, request):
        from nutritionist.models import PatientAssignment
        
        search = request.GET.get("search")
        nutritionist_id = request.GET.get("nutritionist_id")
        status_filter = request.GET.get("status")
        
        data = DietRecommendation.objects.filter(is_deleted=False).order_by('-created_at')
        
        # Filter by search term (user name or assigned nutritionist name)
        if search:
            # Search by user name
            matched_user_ids = UserProfile.objects.filter(full_name__icontains=search).values_list("id", flat=True)
            
            # Search by assigned nutritionist name
            matched_nutritionist_ids = UserProfile.objects.filter(full_name__icontains=search).values_list("id", flat=True)
            assigned_patient_ids = PatientAssignment.objects.filter(
                nutritionist_id__in=matched_nutritionist_ids
            ).values_list('patient_id', flat=True)
            
            # Filter: show plans where EITHER user name matches OR assigned nutritionist name matches
            # This ensures we only show plans with the searched nutritionist
            data = data.filter(Q(user_id__in=matched_user_ids) |
                Q(user_id__in=assigned_patient_ids))
        
        # Filter by status
        if status_filter:
            data = data.filter(status__iexact=status_filter)
        
        # Filter by assigned nutritionist
        if nutritionist_id:
            try:
                # Convert nutritionist_id to int
                nut_id = int(nutritionist_id)
                
                # Get all patients assigned to this nutritionist
                assigned_patients = PatientAssignment.objects.filter(
                    nutritionist_id=nut_id
                ).values_list('patient_id', flat=True)
                
                # Filter diet plans for these patients
                data = data.filter(user_id__in=assigned_patients)
                print(f"Filtered by nutritionist {nut_id}: found {data.count()} plans")
            except (ValueError, TypeError) as e:
                print(f"Error filtering by nutritionist: {e}")
        
        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(data, request)
        
        serializer = DietRecommendationSerializer(paginated_data,
            many=True)
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
        serializer = DietRecommendationSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

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


# ==========================================================================DIET STATS API====================================================================#

class DietStatsAPIView(APIView):
    """Get diet recommendation statistics with single database query"""
    
    @swagger_auto_schema(
        operation_summary="Get Diet Plans Statistics",
        operation_description="Get count of diet plans by status (total, approved, pending, failed, rejected)",
        responses={
            200: openapi.Response('Diet stats', examples={
                "application/json": {
                    "total": 100,
                    "approved": 45,
                    "pending": 30,
                    "failed": 15,
                    "rejected": 10
                }
            })
        }
    )
    def get(self, request):
        try:
            from django.db.models import Count, Q
            
            # Single database query to get all stats
            stats = DietRecommendation.objects.filter(
                is_deleted=False
            ).aggregate(
                total=Count('id'),
                approved=Count('id', filter=Q(status__iexact='approved')),
                pending=Count('id', filter=Q(status__iexact='pending')),
                failed=Count('id', filter=Q(status__iexact='failed')),
                rejected=Count('id', filter=Q(status__iexact='rejected')),
            )
            
            return Response({
                "success": True,
                "data": {
                    "total": stats['total'],
                    "approved": stats['approved'],
                    "pending": stats['pending'],
                    "failed": stats['failed'],
                    "rejected": stats['rejected'],
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            print("DIET STATS ERROR:", traceback.format_exc())
            return Response({
                "error": str(e),
                "message": "Error fetching diet stats"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
