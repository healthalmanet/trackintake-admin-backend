import json
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class MealListCreateAPI(APIView):
    def get(self, request):
        query = """
            SELECT id, name, calories, protein, carbs, fats, fiber, fodmap_level, spice_level, is_verified
            FROM "userFood_fooditem"
            ORDER BY name ASC
            LIMIT 100;
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        results = [
            {
                "id": r[0],
                "name": r[1],
                "calories": r[2],
                "protein": r[3],
                "carbs": r[4],
                "fats": r[5],
                "fiber": r[6],
                "fodmap_level": r[7],
                "spice_level": r[8],
                "is_verified": bool(r[9])
            } for r in rows
        ]
        return Response(results)

    def post(self, request):
        return Response({"message": "Meal created successfully"}, status=status.HTTP_201_CREATED)


class MealDetailAPI(APIView):
    def get(self, request, pk):
        query = """
            SELECT id, name, calories, protein, carbs, fats, fiber, fodmap_level, spice_level, is_verified
            FROM "userFood_fooditem"
            WHERE id = %s;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [pk])
            r = cursor.fetchone()

        if not r:
            return Response({"error": "Meal not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "id": r[0],
            "name": r[1],
            "calories": r[2],
            "protein": r[3],
            "carbs": r[4],
            "fats": r[5],
            "fiber": r[6],
            "fodmap_level": r[7],
            "spice_level": r[8],
            "is_verified": bool(r[9])
        })


class DietRecommendationAPIView(APIView):
    def get(self, request):
        search = request.GET.get("search", "").strip()
        nutritionist_id = request.GET.get("nutritionist_id", "").strip()
        status_filter = request.GET.get("status", "").strip()
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))
        offset = (page - 1) * page_size

        where = ["r.is_deleted = false"]
        params = []

        if status_filter and status_filter.lower() != "all":
            where.append("LOWER(r.status) = LOWER(%s)")
            params.append(status_filter)

        if nutritionist_id:
            where.append("""
                (r.reviewed_by_id = %s OR r.user_id IN (
                    SELECT patient_id FROM nutritionist_patientassignment WHERE nutritionist_id = %s
                ))
            """)
            params.extend([int(nutritionist_id), int(nutritionist_id)])

        if search:
            where.append("""
                (u.full_name ILIKE %s OR u.email ILIKE %s OR r.user_id IN (
                    SELECT pa.patient_id FROM nutritionist_patientassignment pa
                    JOIN user_user nu ON pa.nutritionist_id = nu.id
                    WHERE nu.full_name ILIKE %s
                ))
            """)
            wildcard = f"%{search}%"
            params.extend([wildcard, wildcard, wildcard])

        where_sql = " AND ".join(where)

        count_query = f"""
            SELECT COUNT(*)
            FROM diet_dietrecommendation r
            LEFT JOIN user_user u ON r.user_id = u.id
            WHERE {where_sql};
        """

        data_query = f"""
            SELECT r.id, r.user_id, r.for_week_starting, r.status, r.meals, 
                   r.nutritionist_comment, r.reviewed_by_id, r.created_at, u.full_name as user_name
            FROM diet_dietrecommendation r
            LEFT JOIN user_user u ON r.user_id = u.id
            WHERE {where_sql}
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s;
        """

        with connection.cursor() as cursor:
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            cursor.execute(data_query, params + [page_size, offset])
            rows = cursor.fetchall()

        results = []
        for r in rows:
            meals_data = r[4]
            if isinstance(meals_data, str):
                try:
                    meals_data = json.loads(meals_data)
                except Exception:
                    pass

            results.append({
                "id": r[0],
                "user_id": r[1],
                "for_week_starting": str(r[2]) if r[2] else None,
                "status": r[3],
                "meals": meals_data,
                "nutritionist_comment": r[5],
                "reviewed_by_id": r[6],
                "created_at": r[7].isoformat() if r[7] else None,
                "user_name": r[8] or f"User #{r[1]}"
            })

        return Response({
            "count": total,
            "next": None,
            "previous": None,
            "results": results
        })


class DietRecommendationDetailAPI(APIView):
    def get(self, request, pk):
        query = """
            SELECT r.id, r.user_id, r.for_week_starting, r.status, r.meals, 
                   r.nutritionist_comment, r.reviewed_by_id, r.created_at, u.full_name as user_name
            FROM diet_dietrecommendation r
            LEFT JOIN user_user u ON r.user_id = u.id
            WHERE r.id = %s AND r.is_deleted = false;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [pk])
            r = cursor.fetchone()

        if not r:
            return Response({"error": "Diet recommendation not found"}, status=status.HTTP_404_NOT_FOUND)

        meals_data = r[4]
        if isinstance(meals_data, str):
            try:
                meals_data = json.loads(meals_data)
            except Exception:
                pass

        return Response({
            "id": r[0],
            "user_id": r[1],
            "for_week_starting": str(r[2]) if r[2] else None,
            "status": r[3],
            "meals": meals_data,
            "nutritionist_comment": r[5],
            "reviewed_by_id": r[6],
            "created_at": r[7].isoformat() if r[7] else None,
            "user_name": r[8] or f"User #{r[1]}"
        })

    def put(self, request, pk):
        status_val = request.data.get("status")
        comment_val = request.data.get("nutritionist_comment")

        updates = []
        params = []
        if status_val:
            updates.append("status = %s")
            params.append(status_val)
        if comment_val is not None:
            updates.append("nutritionist_comment = %s")
            params.append(comment_val)

        if not updates:
            return Response({"error": "No fields to update"}, status=status.HTTP_400_BAD_REQUEST)

        params.append(pk)
        query = f"UPDATE diet_dietrecommendation SET {', '.join(updates)} WHERE id = %s RETURNING id;"
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            updated = cursor.fetchone()

        if not updated:
            return Response({"error": "Diet recommendation not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"message": "Diet recommendation updated successfully"})

    def delete(self, request, pk):
        query = "UPDATE diet_dietrecommendation SET is_deleted = true WHERE id = %s RETURNING id;"
        with connection.cursor() as cursor:
            cursor.execute(query, [pk])
            row = cursor.fetchone()

        if not row:
            return Response({"error": "Diet recommendation not found"}, status=status.HTTP_404_NOT_FOUND)

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
            query = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE LOWER(status) = 'approved') as approved,
                    COUNT(*) FILTER (WHERE LOWER(status) = 'pending') as pending,
                    COUNT(*) FILTER (WHERE LOWER(status) = 'failed') as failed,
                    COUNT(*) FILTER (WHERE LOWER(status) = 'rejected') as rejected
                FROM diet_dietrecommendation
                WHERE is_deleted = false;
            """
            with connection.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone() or (0, 0, 0, 0, 0)
            
            return Response({
                "success": True,
                "data": {
                    "total": row[0] or 0,
                    "approved": row[1] or 0,
                    "pending": row[2] or 0,
                    "failed": row[3] or 0,
                    "rejected": row[4] or 0,
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": str(e),
                "message": "Error fetching diet stats"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
