from datetime import datetime, timedelta, timezone
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse


PLAN_COLS = [
    "id", "name", "price", "duration_days", "appointment_allowed", "ai_diet_allowed",
    "inhouse_consults", "expert_consults", "is_active", "weight_tracker_allowed",
    "nutrition_search_allowed", "custom_reminder_allowed", "chat_allowed", "plan_type",
    "BMI_Calculator_allowed", "Fat_Calculator_allowed", "meal_log_allowed", "water_intake_allowed",
    "expert_consultation_fee", "inhouse_consultation_fee", "nutri_ai_diet_allowed",
    "nutri_bulk_upload_allowed", "nutri_chat_allowed", "nutri_export_reports_allowed",
    "nutri_lab_reports_allowed", "nutri_manual_diet_allowed", "nutri_max_patients",
    "nutri_offline_appointment_allowed", "nutri_online_appointment_allowed", "nutri_smart_assistant_allowed"
]


def row_to_plan(r):
    res = {}
    for i, col in enumerate(PLAN_COLS):
        val = r[i]
        if isinstance(val, (bool, int, float, str)) or val is None:
            res[col] = val
        else:
            res[col] = str(val)
    return res


# --------- GET ALL PLANS + CREATE PLAN ---------
class SubscriptionPlanAPI(APIView):
    def get(self, request):
        cols_sql = ", ".join(f'"{col}"' for col in PLAN_COLS)
        query = f"SELECT {cols_sql} FROM subscriptions_plan ORDER BY id DESC;"
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        plans = [row_to_plan(r) for r in rows]
        return Response(plans)

    def post(self, request):
        data = request.data
        name = str(data.get("name", "")).strip()
        price = int(data.get("price", 0))
        duration_days = int(data.get("duration_days", 30))
        plan_type = str(data.get("plan_type", "patient")).strip()
        is_active = bool(data.get("is_active", True))

        if not name:
            return Response({"error": "Plan name is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Build insert fields dynamically
        fields = ["name", "price", "duration_days", "plan_type", "is_active"]
        values = [name, price, duration_days, plan_type, is_active]

        for col in PLAN_COLS:
            if col in ["id", "name", "price", "duration_days", "plan_type", "is_active"]:
                continue
            if col in data:
                fields.append(col)
                values.append(data[col])

        quoted_fields = [f'"{f}"' for f in fields]
        placeholders = ", ".join(["%s"] * len(fields))
        query = f"""
            INSERT INTO subscriptions_plan ({', '.join(quoted_fields)})
            VALUES ({placeholders})
            RETURNING id;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            new_id = cursor.fetchone()[0]

        return Response({"id": new_id, "name": name, "message": "Plan created successfully"}, status=status.HTTP_201_CREATED)


# --------- UPDATE PLAN ---------
class UpdateSubscriptionPlanAPI(APIView):
    def put(self, request, pk):
        data = request.data
        updates = []
        values = []

        for col in PLAN_COLS:
            if col == "id":
                continue
            if col in data:
                updates.append(f'"{col}" = %s')
                values.append(data[col])

        if not updates:
            return Response({"error": "No fields provided to update"}, status=status.HTTP_400_BAD_REQUEST)

        values.append(pk)
        query = f"UPDATE subscriptions_plan SET {', '.join(updates)} WHERE id = %s RETURNING id;"
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            row = cursor.fetchone()

        if not row:
            return Response({"error": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"message": "Plan updated successfully", "id": pk})


# --------- USAGE & PAYMENTS LIST API ---------
class SubscriptionUsageAPI(APIView):
    def get(self, request):
        search = request.query_params.get("search", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        plan_filter = request.query_params.get("plan", "").strip()
        date = request.query_params.get("date", "").strip()
        month = request.query_params.get("month", "").strip()
        year = request.query_params.get("year", "").strip()
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        offset = (page - 1) * page_size

        where = ["1=1"]
        params = []

        if status_filter and status_filter.lower() != "all":
            where.append("LOWER(p.status) = LOWER(%s)")
            params.append(status_filter)

        if plan_filter and plan_filter.lower() != "all":
            where.append("p.plan_id = %s")
            params.append(int(plan_filter))

        if date:
            where.append("DATE(p.created_at) = %s")
            params.append(date)
        elif month and year:
            where.append("EXTRACT(MONTH FROM p.created_at) = %s AND EXTRACT(YEAR FROM p.created_at) = %s")
            params.extend([int(month), int(year)])
        elif year:
            where.append("EXTRACT(YEAR FROM p.created_at) = %s")
            params.append(int(year))

        if search:
            where.append("""
                (u.full_name ILIKE %s OR u.email ILIKE %s OR p.pending_email ILIKE %s
                 OR p.razorpay_order_id ILIKE %s OR p.razorpay_payment_id ILIKE %s)
            """)
            wildcard = f"%{search}%"
            params.extend([wildcard, wildcard, wildcard, wildcard, wildcard])

        where_sql = " AND ".join(where)

        count_query = f"""
            SELECT COUNT(*)
            FROM subscriptions_payment p
            LEFT JOIN user_user u ON p.user_id = u.id
            WHERE {where_sql};
        """

        data_query = f"""
            SELECT 
                p.id, p.user_id, p.plan_id, p.amount, p.status,
                p.razorpay_order_id, p.razorpay_payment_id, p.pending_email, p.payment_type,
                p.created_at, u.full_name as user_name, u.email as user_email, pl.name as plan_name,
                s.start_date, s.end_date, s.is_active as sub_is_active
            FROM subscriptions_payment p
            LEFT JOIN user_user u ON p.user_id = u.id
            LEFT JOIN subscriptions_plan pl ON p.plan_id = pl.id
            LEFT JOIN subscriptions_usersubscription s ON (p.user_id = s.user_id AND p.plan_id = s.plan_id)
            WHERE {where_sql}
            ORDER BY p.created_at DESC
            LIMIT %s OFFSET %s;
        """

        metrics_query = """
            SELECT 
                COALESCE(SUM(amount) FILTER (WHERE LOWER(status) = 'success'), 0) as total_rev,
                COUNT(*) as total_payments,
                COUNT(*) FILTER (WHERE LOWER(status) = 'success') as success_count,
                COUNT(*) FILTER (WHERE LOWER(status) = 'failed') as failed_count,
                (SELECT COUNT(*) FROM subscriptions_usersubscription WHERE is_active = true) as active_subs,
                (SELECT COUNT(*) FROM subscriptions_usersubscription WHERE is_active = true AND end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days') as expiring_soon
            FROM subscriptions_payment;
        """

        with connection.cursor() as cursor:
            cursor.execute(metrics_query)
            m = cursor.fetchone()
            metrics = {
                "total_revenue": m[0] or 0,
                "total_payments": m[1] or 0,
                "success_count": m[2] or 0,
                "failed_count": m[3] or 0,
                "active_subscriptions": m[4] or 0,
                "expiring_soon": m[5] or 0,
            }

            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            cursor.execute(data_query, params + [page_size, offset])
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "payment_id": r[0],
                "user_id": r[1],
                "plan_id": r[2],
                "amount": r[3] or 0,
                "payment_status": r[4],
                "razorpay_order_id": r[5],
                "razorpay_payment_id": r[6],
                "pending_email": r[7],
                "payment_type": r[8],
                "created_at": r[9].isoformat() if r[9] else None,
                "user_name": r[10] or r[7] or f"User #{r[1]}",
                "email": r[11] or r[7] or "",
                "plan_name": r[12] or f"Plan #{r[2]}",
                "start_date": str(r[13]) if r[13] else None,
                "end_date": str(r[14]) if r[14] else None,
                "is_active_subscription": bool(r[15]) if r[15] is not None else False,
            })

        total_pages = max(1, (total + page_size - 1) // page_size)
        return Response({
            "metrics": metrics,
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        })


# --------- PAYMENT ANALYTICS ---------
class PaymentAnalyticsAPI(APIView):
    def get(self, request):
        date = request.query_params.get("date")
        month = request.query_params.get("month")
        year = request.query_params.get("year")

        where = ["1=1"]
        params = []
        if date:
            where.append("DATE(created_at) = %s")
            params.append(date)
        elif month and year:
            where.append("EXTRACT(MONTH FROM created_at) = %s AND EXTRACT(YEAR FROM created_at) = %s")
            params.extend([int(month), int(year)])
        elif year:
            where.append("EXTRACT(YEAR FROM created_at) = %s")
            params.append(int(year))

        where_sql = " AND ".join(where)

        summary_query = f"""
            SELECT 
                COUNT(*),
                COALESCE(SUM(CASE WHEN status = 'success' THEN amount ELSE 0 END), 0),
                COUNT(CASE WHEN status = 'success' THEN 1 END),
                COUNT(CASE WHEN status = 'failed' THEN 1 END)
            FROM subscriptions_payment
            WHERE {where_sql};
        """

        plan_query = f"""
            SELECT p.plan_id, pl.name, COALESCE(SUM(p.amount), 0) as rev
            FROM subscriptions_payment p
            LEFT JOIN subscriptions_plan pl ON p.plan_id = pl.id
            WHERE p.status = 'success' AND {where_sql}
            GROUP BY p.plan_id, pl.name
            ORDER BY rev DESC;
        """

        with connection.cursor() as cursor:
            cursor.execute(summary_query, params)
            total_payments, total_revenue, success_payments, failed_payments = cursor.fetchone()

            cursor.execute(plan_query, params)
            plan_rows = cursor.fetchall()

        revenue_per_plan = [
            {"plan_id": r[0], "plan_name": r[1] or f"Plan #{r[0]}", "revenue": r[2]}
            for r in plan_rows
        ]

        return Response({
            "totalPayments": total_payments,
            "totalRevenue": total_revenue,
            "successPayments": success_payments,
            "failedPayments": failed_payments,
            "revenuePerPlan": revenue_per_plan,
        })


# --------- CREATE PAYMENT ---------
class CreatePaymentAPI(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        plan_id = request.data.get("plan_id")
        amount = request.data.get("amount", 0)
        payment_status = request.data.get("payment_status", "success")
        razorpay_order_id = request.data.get("razorpay_order_id", "")
        now_dt = datetime.now(timezone.utc)

        insert_q = """
            INSERT INTO subscriptions_payment (user_id, plan_id, amount, status, razorpay_order_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        with connection.cursor() as cursor:
            cursor.execute(insert_q, [user_id, plan_id, amount, payment_status, razorpay_order_id, now_dt])
            pid = cursor.fetchone()[0]

            # Broadcast real-time WebSocket notification for plan purchase or payment failure
            try:
                cursor.execute("SELECT full_name FROM user_user WHERE id = %s;", [user_id])
                u_row = cursor.fetchone()
                user_name = u_row[0] if u_row and u_row[0] else f"User #{user_id}"

                cursor.execute("SELECT name FROM subscriptions_plan WHERE id = %s;", [plan_id])
                p_row = cursor.fetchone()
                plan_name = p_row[0] if p_row and p_row[0] else f"Plan #{plan_id}"

                if str(payment_status).lower() in ["success", "paid", "completed"]:
                    from notifications.utils import notify_plan_purchased
                    notify_plan_purchased(
                        user_id=user_id,
                        user_name=user_name,
                        plan_name=plan_name,
                        amount=amount,
                        payment_id=pid
                    )
                else:
                    from notifications.utils import notify_payment_failed
                    notify_payment_failed(
                        user_id=user_id,
                        user_name=user_name,
                        plan_name=plan_name,
                        amount=amount,
                        error_reason=f"Payment status: {payment_status}"
                    )
            except Exception as e:
                print(f"[Payment Notification Warning]: {e}")

        return Response({
            "message": "Payment created successfully",
            "data": {
                "payment_id": pid,
                "user_id": user_id,
                "plan_id": plan_id,
                "amount": amount,
                "status": payment_status
            }
        }, status=status.HTTP_201_CREATED)


class PlanDurationTrackingAPI(APIView):
    def get(self, request):
        query = """
            SELECT s.id, s.user_id, s.plan_id, s.start_date, s.end_date, s.is_active,
                   u.full_name as user_name, pl.name as plan_name
            FROM subscriptions_usersubscription s
            LEFT JOIN user_user u ON s.user_id = u.id
            LEFT JOIN subscriptions_plan pl ON s.plan_id = pl.id
            ORDER BY s.created_at DESC
            LIMIT 50;
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        results = [
            {
                "id": r[0],
                "user_id": r[1],
                "plan_id": r[2],
                "start_date": str(r[3]),
                "end_date": str(r[4]),
                "is_active": r[5],
                "user_name": r[6] or f"User #{r[1]}",
                "plan_name": r[7] or f"Plan #{r[2]}",
            } for r in rows
        ]
        return Response(results)


def get_subscription_plan(request):
    return JsonResponse({"status": True, "plan": "Active", "upgrade": False})
