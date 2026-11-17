from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class ApproveNutritionistAPIView(APIView):
    def post(self, request, pk):
        is_verified_param = request.data.get("is_verified") if isinstance(request.data, dict) else None

        with connection.cursor() as cursor:
            cursor.execute("SELECT id, is_verified FROM nutritionist_nutritionistprofile WHERE id = %s;", [pk])
            row = cursor.fetchone()

            if not row:
                return Response(
                    {"success": False, "message": "Nutritionist not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            current_status = bool(row[1])
            new_status = bool(is_verified_param) if is_verified_param is not None else not current_status

            cursor.execute(
                "UPDATE nutritionist_nutritionistprofile SET is_verified = %s WHERE id = %s RETURNING id, is_verified;",
                [new_status, pk]
            )
            updated = cursor.fetchone()

        return Response({
            "success": True,
            "message": "Nutritionist approved successfully",
            "data": {
                "nutritionist_id": updated[0],
                "is_verified": updated[1]
            }
        }, status=status.HTTP_200_OK)
