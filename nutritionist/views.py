from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from nutritionist.models import NutritionistProfile, PatientAssignment
from .serializers import NutritionistProfileSerializer, PatientAssignmentSerializer
from rest_framework.parsers import MultiPartParser, FormParser


class NutritionistListAPIView(APIView):
    """Get list of all nutritionists with their details"""
    
    @swagger_auto_schema(
        operation_summary="List All Nutritionists",
        operation_description="Get all nutritionists with their profiles and patient counts, sorted alphabetically by name",
        responses={
            200: openapi.Response(
                description="List of nutritionists",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        )
                    }
                )
            )
        }
    )
    def get(self, request):
        try:
            # Get all nutritionists and sort by user's full_name alphabetically
            nutritionists = NutritionistProfile.objects.all().select_related('user').order_by('user__full_name')
            serializer = NutritionistProfileSerializer(nutritionists, many=True)
            return Response({
                "success": True,
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientAssignmentListAPIView(APIView):
    """Get list of all patient assignments"""
    
    @swagger_auto_schema(
        operation_summary="List All Patient Assignments",
        operation_description="Get all patient-nutritionist assignments",
        responses={
            200: openapi.Response(
                description="List of assignments",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                )
            )
        }
    )
    def get(self, request):
        try:
            assignments = PatientAssignment.objects.all().order_by('-assigned_at')
            serializer = PatientAssignmentSerializer(assignments, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ApproveNutritionistAPIView(APIView):

    @swagger_auto_schema(
        operation_summary="Approve Nutritionist",
        operation_description="Approve a nutritionist by setting is_verified=True",
        request_body=None,
        manual_parameters=[
            openapi.Parameter(
                name='pk',
                in_=openapi.IN_PATH,
                description="Nutritionist ID",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Nutritionist approved successfully"
            ),
            404: openapi.Response(
                description="Nutritionist not found"
            )
        }
    )
    def post(self, request, pk):

        try:
            nutritionist = NutritionistProfile.objects.get(id=pk)

        except NutritionistProfile.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Nutritionist not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        nutritionist.is_verified = True
        nutritionist.save()

        return Response(
            {
                "success": True,
                "message": "Nutritionist approved successfully",
                "data": {
                    "nutritionist_id": nutritionist.id,
                    "is_verified": nutritionist.is_verified
                }
            },
            status=status.HTTP_200_OK
        )
        
        
class NutritionistCreateAPIView(APIView):
    
    parser_classes = [MultiPartParser, FormParser]
    @swagger_auto_schema(
        operation_summary="Create Nutritionist",
        request_body=NutritionistProfileSerializer
    )
    def post(self, request):

        serializer = NutritionistProfileSerializer(
            data=request.data
        )

        if serializer.is_valid():

            serializer.save()

            return Response(
                {
                    "success": True,
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )