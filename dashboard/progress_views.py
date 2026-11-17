from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response


class ProgressLogsAPI(APIView):
    """
    Unified user progress & health logs: Meals, Water intake, and Weight tracking.
    Query raw SQL safely without DDL modifications.
    """
    def get(self, request):
        log_type = request.query_params.get("type", "meals").lower()  # meals, water, weight
        search = request.query_params.get("search", "").strip()
        date = request.query_params.get("date", "").strip()
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        offset = (page - 1) * page_size

        # Get summary counts
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM "userFood_usermeal";')
            total_meals = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM features_waterintakelog;')
            total_water = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM features_weightlog;')
            total_weight = cursor.fetchone()[0]

        results = []
        total = 0

        if log_type == "water":
            where = ["1=1"]
            params = []
            if search:
                where.append("(u.full_name ILIKE %s OR u.email ILIKE %s)")
                params.extend([f"%{search}%", f"%{search}%"])
            if date:
                where.append("w.date = %s")
                params.append(date)

            where_sql = " AND ".join(where)

            count_q = f"""
                SELECT COUNT(*) FROM features_waterintakelog w
                LEFT JOIN user_user u ON w.user_id = u.id
                WHERE {where_sql};
            """
            data_q = f"""
                SELECT w.id, w.amount_ml, w.date, w.user_id, u.full_name, u.email
                FROM features_waterintakelog w
                LEFT JOIN user_user u ON w.user_id = u.id
                WHERE {where_sql}
                ORDER BY w.date DESC, w.id DESC
                LIMIT %s OFFSET %s;
            """
            with connection.cursor() as cursor:
                cursor.execute(count_q, params)
                total = cursor.fetchone()[0]
                cursor.execute(data_q, params + [page_size, offset])
                for r in cursor.fetchall():
                    results.append({
                        "id": r[0],
                        "type": "water",
                        "amount_ml": r[1],
                        "date": str(r[2]) if r[2] else None,
                        "user_id": r[3],
                        "user_name": r[4] or f"User #{r[3]}",
                        "user_email": r[5] or "",
                    })

        elif log_type == "weight":
            where = ["1=1"]
            params = []
            if search:
                where.append("(u.full_name ILIKE %s OR u.email ILIKE %s)")
                params.extend([f"%{search}%", f"%{search}%"])
            if date:
                where.append("w.date = %s")
                params.append(date)

            where_sql = " AND ".join(where)

            count_q = f"""
                SELECT COUNT(*) FROM features_weightlog w
                LEFT JOIN user_user u ON w.user_id = u.id
                WHERE {where_sql};
            """
            data_q = f"""
                SELECT w.id, w.weight_kg, w.date, w.time_logged, w.user_id, u.full_name, u.email
                FROM features_weightlog w
                LEFT JOIN user_user u ON w.user_id = u.id
                WHERE {where_sql}
                ORDER BY w.date DESC, w.id DESC
                LIMIT %s OFFSET %s;
            """
            with connection.cursor() as cursor:
                cursor.execute(count_q, params)
                total = cursor.fetchone()[0]
                cursor.execute(data_q, params + [page_size, offset])
                for r in cursor.fetchall():
                    results.append({
                        "id": r[0],
                        "type": "weight",
                        "weight_kg": r[1],
                        "date": str(r[2]) if r[2] else None,
                        "time_logged": r[3].isoformat() if r[3] else None,
                        "user_id": r[4],
                        "user_name": r[5] or f"User #{r[4]}",
                        "user_email": r[6] or "",
                    })

        else:  # meals (default)
            where = ["1=1"]
            params = []
            if search:
                where.append("(m.food_name ILIKE %s OR u.full_name ILIKE %s OR u.email ILIKE %s)")
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
            if date:
                where.append("m.date = %s")
                params.append(date)

            where_sql = " AND ".join(where)

            count_q = f"""
                SELECT COUNT(*) FROM "userFood_usermeal" m
                LEFT JOIN user_user u ON m.user_id = u.id
                WHERE {where_sql};
            """
            data_q = f"""
                SELECT m.id, m.food_name, m.quantity, m.unit, m.meal_type, m.date,
                       m.calories, m.protein, m.carbs, m.fats, m.user_id, u.full_name, u.email
                FROM "userFood_usermeal" m
                LEFT JOIN user_user u ON m.user_id = u.id
                WHERE {where_sql}
                ORDER BY m.date DESC, m.id DESC
                LIMIT %s OFFSET %s;
            """
            with connection.cursor() as cursor:
                cursor.execute(count_q, params)
                total = cursor.fetchone()[0]
                cursor.execute(data_q, params + [page_size, offset])
                for r in cursor.fetchall():
                    results.append({
                        "id": r[0],
                        "type": "meal",
                        "food_name": r[1],
                        "quantity": r[2],
                        "unit": r[3],
                        "meal_type": r[4],
                        "date": str(r[5]) if r[5] else None,
                        "calories": r[6],
                        "protein": r[7],
                        "carbs": r[8],
                        "fats": r[9],
                        "user_id": r[10],
                        "user_name": r[11] or f"User #{r[10]}",
                        "user_email": r[12] or "",
                    })

        total_pages = max(1, (total + page_size - 1) // page_size)
        return Response({
            "summary": {
                "total_meals": total_meals,
                "total_water": total_water,
                "total_weight": total_weight,
            },
            "type": log_type,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "results": results,
        })

