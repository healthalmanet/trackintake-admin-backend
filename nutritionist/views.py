from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from nutritionist.models import NutritionistProfile


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