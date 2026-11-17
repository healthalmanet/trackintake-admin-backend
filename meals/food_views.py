from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection


class FoodItemListAPI(APIView):
    """
    List food items from production database userFood_fooditem
    with search and filtering.
    """

    def get(self, request):
        search = request.GET.get('search', '').strip()
        fodmap_filter = request.GET.get('fodmap', '').strip()
        spice_filter = request.GET.get('spice', '').strip()
        verified_filter = request.GET.get('verified', '').strip()

        try:
            page = max(1, int(request.GET.get('page', 1)))
            page_size = max(1, min(100, int(request.GET.get('page_size', 20))))
        except ValueError:
            page = 1
            page_size = 20

        offset = (page - 1) * page_size

        where_clauses = ["1=1"]
        params = []

        if search:
            where_clauses.append("name ILIKE %s")
            params.append(f"%{search}%")

        if fodmap_filter and fodmap_filter.upper() != 'ALL':
            where_clauses.append("LOWER(fodmap_level) = LOWER(%s)")
            params.append(fodmap_filter)

        if spice_filter and spice_filter.upper() != 'ALL':
            where_clauses.append("LOWER(spice_level) = LOWER(%s)")
            params.append(spice_filter)

        if verified_filter and verified_filter.upper() != 'ALL':
            is_v = verified_filter.lower() in ['true', '1', 'yes']
            where_clauses.append("is_verified = %s")
            params.append(is_v)

        where_sql = " AND ".join(where_clauses)

        count_query = f'SELECT COUNT(*) FROM "userFood_fooditem" WHERE {where_sql};'

        data_query = f"""
        SELECT 
            id, name, default_quantity, default_unit,
            COALESCE(calories, 0), COALESCE(protein, 0), COALESCE(carbs, 0), COALESCE(fats, 0), COALESCE(fiber, 0),
            fodmap_level, spice_level, purine_level, is_verified
        FROM "userFood_fooditem"
        WHERE {where_sql}
        ORDER BY name ASC
        LIMIT %s OFFSET %s;
        """

        with connection.cursor() as cursor:
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            cursor.execute(data_query, params + [page_size, offset])
            rows = cursor.fetchall()

            items = []
            for r in rows:
                items.append({
                    "id": r[0],
                    "name": r[1],
                    "default_quantity": float(r[2]) if r[2] is not None else 1.0,
                    "default_unit": r[3] or "serving",
                    "calories": float(r[4]),
                    "protein": float(r[5]),
                    "carbs": float(r[6]),
                    "fats": float(r[7]),
                    "fiber": float(r[8]),
                    "fodmap_level": r[9] or "None",
                    "spice_level": r[10] or "None",
                    "purine_level": r[11] or "None",
                    "is_verified": bool(r[12]),
                })

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return Response({
            "results": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }, status=status.HTTP_200_OK)

