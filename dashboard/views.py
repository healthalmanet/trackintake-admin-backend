from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response


def check_db_connection():
    try:
        connection.ensure_connection()
        return True
    except Exception:
        return False


# ---------------- TOTAL USERS ----------------
class TotalUsersAPI(APIView):
    def get(self, request):
        date = request.GET.get("date")
        month = request.GET.get("month")
        year = request.GET.get("year")

        where = ["1=1"]
        params = []
        if date:
            where.append("DATE(date_joined) = %s")
            params.append(date)
        elif month and year:
            where.append("EXTRACT(MONTH FROM date_joined) = %s AND EXTRACT(YEAR FROM date_joined) = %s")
            params.extend([int(month), int(year)])
        elif year:
            where.append("EXTRACT(YEAR FROM date_joined) = %s")
            params.append(int(year))

        query = f"SELECT COUNT(*) FROM user_user WHERE {' AND '.join(where)};"
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            total = cursor.fetchone()[0]

        return Response({"totalUsers": total})


# ---------------- ACTIVE USERS ----------------
class ActiveUsersAPI(APIView):
    def get(self, request):
        date = request.GET.get("date")
        month = request.GET.get("month")
        year = request.GET.get("year")

        where = ["is_active = true"]
        params = []
        if date:
            where.append("DATE(date_joined) = %s")
            params.append(date)
        elif month and year:
            where.append("EXTRACT(MONTH FROM date_joined) = %s AND EXTRACT(YEAR FROM date_joined) = %s")
            params.extend([int(month), int(year)])
        elif year:
            where.append("EXTRACT(YEAR FROM date_joined) = %s")
            params.append(int(year))

        query = f"SELECT COUNT(*) FROM user_user WHERE {' AND '.join(where)};"
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            active = cursor.fetchone()[0]

        return Response({"activeUsers": active})


# ---------------- TOTAL REVENUE ----------------
class TotalRevenueAPI(APIView):
    def get(self, request):
        date = request.GET.get("date")
        month = request.GET.get("month")
        year = request.GET.get("year")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        where = ["status = 'success'"]
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
        elif start_date and end_date:
            where.append("DATE(created_at) BETWEEN %s AND %s")
            params.extend([start_date, end_date])

        query = f"SELECT COALESCE(SUM(amount), 0) FROM subscriptions_payment WHERE {' AND '.join(where)};"
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            total = cursor.fetchone()[0]

        return Response({"totalRevenue": total})


# ---------------- PENDING APPOINTMENTS ----------------
class PendingAppointmentsAPI(APIView):
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM appointments_appointment WHERE UPPER(status) IN ('PENDING_REVIEW', 'AWAITING_PAYMENT');")
                count = cursor.fetchone()[0]
        except Exception:
            count = 0

        return Response({"pendingAppointments": count})


# ---------------- USER GROWTH ----------------
class UserGrowthAPI(APIView):
    def get(self, request):
        date = request.GET.get("date")
        month = request.GET.get("month")
        year = request.GET.get("year")

        where = ["1=1"]
        params = []
        if date:
            where.append("DATE(date_joined) = %s")
            params.append(date)
        elif month and year:
            where.append("EXTRACT(MONTH FROM date_joined) = %s AND EXTRACT(YEAR FROM date_joined) = %s")
            params.extend([int(month), int(year)])
        elif year:
            where.append("EXTRACT(YEAR FROM date_joined) = %s")
            params.append(int(year))

        query = f"""
            SELECT DATE(date_joined) as d, COUNT(id) as users_count
            FROM user_user
            WHERE {' AND '.join(where)}
            GROUP BY DATE(date_joined)
            ORDER BY d ASC;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        user_growth = [{"date": str(r[0]), "users": r[1]} for r in rows]
        return Response({"userGrowth": user_growth})


# ---------------- PLAN DISTRIBUTION ----------------
class PlanDistributionAPI(APIView):
    def get(self, request):
        date = request.GET.get("date")
        month = request.GET.get("month")
        year = request.GET.get("year")

        where = ["status = 'success'"]
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

        query = f"""
            SELECT plan_id, COUNT(user_id) as users_count
            FROM subscriptions_payment
            WHERE {' AND '.join(where)}
            GROUP BY plan_id
            ORDER BY users_count DESC;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        plans = [{"plan_id": r[0], "users": r[1]} for r in rows]
        return Response({"planDistribution": plans})


# ---------------- RECENT ACTIVITY ----------------
class RecentActivityAPI(APIView):
    def get(self, request):
        signups_q = """
            SELECT id, full_name, email, date_joined
            FROM user_user
            ORDER BY date_joined DESC
            LIMIT 5;
        """
        subs_q = """
            SELECT user_id, plan_id, created_at
            FROM subscriptions_usersubscription
            ORDER BY created_at DESC
            LIMIT 5;
        """
        with connection.cursor() as cursor:
            cursor.execute(signups_q)
            signups = [
                {
                    "id": r[0],
                    "full_name": r[1],
                    "email": r[2],
                    "date_joined": r[3].isoformat() if r[3] else None,
                    "activity": "User signed up"
                } for r in cursor.fetchall()
            ]

            cursor.execute(subs_q)
            subs = [
                {
                    "user_id": r[0],
                    "plan_id": r[1],
                    "created_at": r[2].isoformat() if r[2] else None,
                    "activity": "User purchased subscription"
                } for r in cursor.fetchall()
            ]

        return Response({
            "recentSignups": signups,
            "recentSubscriptions": subs
        })


# ---------------- REVENUE BY PLAN ----------------
class RevenueByPlanAPI(APIView):
    def get(self, request):
        date = request.GET.get("date")
        month = request.GET.get("month")
        year = request.GET.get("year")

        where = ["p.status = 'success'"]
        params = []
        if date:
            where.append("DATE(p.created_at) = %s")
            params.append(date)
        elif month and year:
            where.append("EXTRACT(MONTH FROM p.created_at) = %s AND EXTRACT(YEAR FROM p.created_at) = %s")
            params.extend([int(month), int(year)])
        elif year:
            where.append("EXTRACT(YEAR FROM p.created_at) = %s")
            params.append(int(year))

        query = f"""
            SELECT p.plan_id, pl.name as plan_name, COALESCE(SUM(p.amount), 0) as total_rev
            FROM subscriptions_payment p
            LEFT JOIN subscriptions_plan pl ON p.plan_id = pl.id
            WHERE {' AND '.join(where)}
            GROUP BY p.plan_id, pl.name
            ORDER BY total_rev DESC;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        revenue = [{"plan_id": r[0], "plan_name": r[1] or f"Plan #{r[0]}", "total_revenue": r[2]} for r in rows]
        return Response({"revenueByPlan": revenue})


# ---------------- REVENUE DETAILS ----------------
class RevenueDetailsAPI(APIView):
    def get(self, request):
        query = """
            SELECT id, user_id, plan_id, amount, created_at
            FROM subscriptions_payment
            WHERE status = 'success'
            ORDER BY created_at DESC;
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            payments = [
                {
                    "id": r[0],
                    "user_id": r[1],
                    "plan_id": r[2],
                    "amount": r[3],
                    "created_at": r[4].isoformat() if r[4] else None
                } for r in cursor.fetchall()
            ]

        return Response({"payments": payments})


# ---------------- USERS WITH PAYMENT BUT NO PROFILE ----------------
class UsersWithPaymentNoProfileAPI(APIView):
    def get(self, request):
        try:
            status_filter = request.query_params.get('status')
            where = ["up.id IS NULL"]
            params = []
            if status_filter:
                where.append("p.status = %s")
                params.append(status_filter)

            query = f"""
                SELECT p.user_id, p.amount, p.plan_id, p.status, p.created_at, u.full_name
                FROM subscriptions_payment p
                LEFT JOIN "userProfile_userprofile" up ON p.user_id = up.user_id
                LEFT JOIN user_user u ON p.user_id = u.id
                WHERE {' AND '.join(where)}
                ORDER BY p.created_at DESC;
            """
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

            users_data = [
                {
                    "user_id": r[0],
                    "amount": r[1],
                    "plan_id": r[2],
                    "status": r[3],
                    "created_at": r[4].isoformat() if r[4] else None,
                    "user_name": r[5] or f"User #{r[0]}"
                } for r in rows
            ]

            unique_user_ids = sorted(list(set(r[0] for r in rows if r[0] is not None)))

            return Response({
                "count": len(users_data),
                "status_filter": status_filter or "all",
                "total_missing_users": len(unique_user_ids),
                "missing_user_ids": unique_user_ids,
                "users_data": users_data
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# ---------------- CONSOLIDATED DASHBOARD OVERVIEW ----------------
class DashboardOverviewAPI(APIView):
    """
    Consolidated dashboard overview API that computes:
    - Executive Metrics: Total Users, Total Patients, Total Nutritionists,
      In-House Consultants, Expert Consultants, In-House Consultations,
      Expert Consultations, Total Consultations, Total Revenue, Active Users
    - Dynamic Filters: All Time, Today, Weekly (Last 7 Days), Monthly, Yearly, Custom
    - Charts Data: User Growth, Revenue Trend, Plan Distribution,
      Consultations Breakdown (Category, Type, Status)
    - Live Activity: Recent Signups, Recent Payments, Recent Appointments
    All queries use parameterized raw SQL with zero Django models.
    """
    def get(self, request):
        try:
            range_val = request.GET.get("range", "all").strip().lower()
            date_val = request.GET.get("date", "").strip()
            month_val = request.GET.get("month", "").strip()
            year_val = request.GET.get("year", "").strip()
            start_date = request.GET.get("start_date", "").strip()
            end_date = request.GET.get("end_date", "").strip()

            # Handle date formatted as YYYY-MM for month range
            if (range_val == "month" or not month_val) and date_val and "-" in date_val:
                parts = date_val.split("-")
                if len(parts) == 2:
                    year_val, month_val = parts[0], parts[1]
            if (range_val == "year" or not year_val) and date_val and len(date_val) == 4 and date_val.isdigit():
                year_val = date_val

            u_where = ["1=1"]
            u_params = []
            p_where = ["status = 'success'"]
            p_params = []
            a_where = ["1=1"]
            a_params = []

            if range_val == "day" and date_val:
                u_where.append("DATE(date_joined) = %s")
                u_params.append(date_val)
                p_where.append("DATE(created_at) = %s")
                p_params.append(date_val)
                a_where.append("(slot_date = %s OR DATE(created_at) = %s)")
                a_params.extend([date_val, date_val])
            elif range_val == "week":
                u_where.append("DATE(date_joined) >= CURRENT_DATE - INTERVAL '7 days'")
                p_where.append("DATE(created_at) >= CURRENT_DATE - INTERVAL '7 days'")
                a_where.append("(slot_date >= CURRENT_DATE - INTERVAL '7 days' OR DATE(created_at) >= CURRENT_DATE - INTERVAL '7 days')")
            elif (range_val == "month" or month_val) and month_val and year_val:
                u_where.append("EXTRACT(MONTH FROM date_joined) = %s AND EXTRACT(YEAR FROM date_joined) = %s")
                u_params.extend([int(month_val), int(year_val)])
                p_where.append("EXTRACT(MONTH FROM created_at) = %s AND EXTRACT(YEAR FROM created_at) = %s")
                p_params.extend([int(month_val), int(year_val)])
                a_where.append("(EXTRACT(MONTH FROM slot_date) = %s AND EXTRACT(YEAR FROM slot_date) = %s OR EXTRACT(MONTH FROM created_at) = %s AND EXTRACT(YEAR FROM created_at) = %s)")
                a_params.extend([int(month_val), int(year_val), int(month_val), int(year_val)])
            elif (range_val == "year" or year_val) and year_val:
                u_where.append("EXTRACT(YEAR FROM date_joined) = %s")
                u_params.append(int(year_val))
                p_where.append("EXTRACT(YEAR FROM created_at) = %s")
                p_params.append(int(year_val))
                a_where.append("(EXTRACT(YEAR FROM slot_date) = %s OR EXTRACT(YEAR FROM created_at) = %s)")
                a_params.extend([int(year_val), int(year_val)])
            elif start_date and end_date:
                u_where.append("DATE(date_joined) BETWEEN %s AND %s")
                u_params.extend([start_date, end_date])
                p_where.append("DATE(created_at) BETWEEN %s AND %s")
                p_params.extend([start_date, end_date])
                a_where.append("(slot_date BETWEEN %s AND %s OR DATE(created_at) BETWEEN %s AND %s)")
                a_params.extend([start_date, end_date, start_date, end_date])

            with connection.cursor() as cursor:
                # 1. All-time baseline totals
                cursor.execute("""
                    SELECT 
                        (SELECT COUNT(*) FROM user_user) as total_users,
                        (SELECT COUNT(*) FROM user_user WHERE LOWER(role) IN ('user', 'patient')) as total_patients,
                        (SELECT COUNT(*) FROM user_user WHERE LOWER(role) = 'nutritionist') as total_nutritionists,
                        (SELECT COUNT(*) FROM nutritionist_nutritionistprofile WHERE LOWER(nutritionist_type) = 'inhouse') as inhouse_consultants,
                        (SELECT COUNT(*) FROM nutritionist_nutritionistprofile WHERE LOWER(nutritionist_type) IN ('expert', 'freelancer')) as expert_consultants,
                        (SELECT COUNT(*) FROM appointments_appointment WHERE UPPER(appointment_category) = 'IN_HOUSE') as inhouse_consultations,
                        (SELECT COUNT(*) FROM appointments_appointment WHERE UPPER(appointment_category) = 'EXPERT') as expert_consultations,
                        (SELECT COUNT(*) FROM appointments_appointment) as total_consultations,
                        (SELECT COALESCE(SUM(amount), 0) FROM subscriptions_payment WHERE LOWER(status) = 'success') as total_revenue
                """)
                at = cursor.fetchone()
                all_time = {
                    "total_users": at[0],
                    "total_patients": at[1],
                    "total_nutritionists": at[2],
                    "inhouse_consultants": at[3],
                    "expert_consultants": at[4],
                    "inhouse_consultations": at[5],
                    "expert_consultations": at[6],
                    "total_consultations": at[7],
                    "total_revenue": at[8]
                }

                # 2. Filtered Metrics
                metrics_sql = f"""
                    SELECT 
                        (SELECT COUNT(*) FROM user_user WHERE {' AND '.join(u_where)}) as total_users,
                        (SELECT COUNT(*) FROM user_user WHERE LOWER(role) IN ('user', 'patient') AND {' AND '.join(u_where)}) as total_patients,
                        (SELECT COUNT(*) FROM user_user WHERE LOWER(role) = 'nutritionist' AND {' AND '.join(u_where)}) as total_nutritionists,
                        (SELECT COUNT(*) FROM appointments_appointment WHERE UPPER(appointment_category) = 'IN_HOUSE' AND {' AND '.join(a_where)}) as inhouse_consultations,
                        (SELECT COUNT(*) FROM appointments_appointment WHERE UPPER(appointment_category) = 'EXPERT' AND {' AND '.join(a_where)}) as expert_consultations,
                        (SELECT COUNT(*) FROM appointments_appointment WHERE {' AND '.join(a_where)}) as total_consultations,
                        (SELECT COALESCE(SUM(amount), 0) FROM subscriptions_payment WHERE {' AND '.join(p_where)}) as total_revenue,
                        (SELECT COUNT(*) FROM user_user WHERE is_active = true AND {' AND '.join(u_where)}) as active_users,
                        (SELECT COUNT(*) FROM appointments_appointment WHERE UPPER(appointment_type) = 'VIRTUAL' AND {' AND '.join(a_where)}) as virtual_consultations,
                        (SELECT COUNT(*) FROM appointments_appointment WHERE UPPER(appointment_type) = 'IN_PERSON' AND {' AND '.join(a_where)}) as inperson_consultations,
                        (SELECT COUNT(*) FROM appointments_appointment WHERE UPPER(status) = 'CONFIRMED' AND {' AND '.join(a_where)}) as confirmed_consultations,
                        (SELECT COUNT(*) FROM appointments_appointment WHERE UPPER(status) IN ('PENDING_REVIEW', 'AWAITING_PAYMENT') AND {' AND '.join(a_where)}) as pending_consultations,
                        (SELECT COUNT(*) FROM appointments_appointment WHERE UPPER(status) = 'CANCELLED' AND {' AND '.join(a_where)}) as cancelled_consultations
                """
                m_params = u_params + u_params + u_params + a_params + a_params + a_params + p_params + u_params + a_params + a_params + a_params + a_params + a_params
                cursor.execute(metrics_sql, m_params)
                m = cursor.fetchone()

                metrics = {
                    "total_users": m[0],
                    "total_patients": m[1],
                    "total_nutritionists": m[2],
                    "inhouse_consultants": all_time["inhouse_consultants"],
                    "expert_consultants": all_time["expert_consultants"],
                    "inhouse_consultations": m[3],
                    "expert_consultations": m[4],
                    "total_consultations": m[5],
                    "total_revenue": m[6],
                    "active_users": m[7],
                    "virtual_consultations": m[8],
                    "inperson_consultations": m[9],
                    "confirmed_consultations": m[10],
                    "pending_consultations": m[11],
                    "cancelled_consultations": m[12],
                    "all_time": all_time
                }

                # 3. User Growth Trajectory
                cursor.execute(f"""
                    SELECT DATE(date_joined) as d, 
                           COUNT(*) as users,
                           COUNT(*) FILTER (WHERE LOWER(role) IN ('user', 'patient')) as patients,
                           COUNT(*) FILTER (WHERE LOWER(role) = 'nutritionist') as nutritionists
                    FROM user_user
                    WHERE {' AND '.join(u_where)}
                    GROUP BY DATE(date_joined)
                    ORDER BY d ASC;
                """, u_params)
                user_growth = [
                    {"date": str(r[0]), "users": r[1], "patients": r[2], "nutritionists": r[3]}
                    for r in cursor.fetchall()
                ]

                # 4. Revenue Trend
                cursor.execute(f"""
                    SELECT DATE(created_at) as d,
                           COALESCE(SUM(amount), 0) as revenue
                    FROM subscriptions_payment
                    WHERE {' AND '.join(p_where)}
                    GROUP BY DATE(created_at)
                    ORDER BY d ASC;
                """, p_params)
                revenue_trend = [{"date": str(r[0]), "revenue": r[1]} for r in cursor.fetchall()]

                # 5. Revenue by Plan
                cursor.execute(f"""
                    SELECT p.plan_id, COALESCE(pl.name, 'Plan #' || p.plan_id::text) as plan_name,
                           COALESCE(SUM(p.amount), 0) as total_rev
                    FROM subscriptions_payment p
                    LEFT JOIN subscriptions_plan pl ON p.plan_id = pl.id
                    WHERE {' AND '.join(p_where)}
                    GROUP BY p.plan_id, pl.name
                    ORDER BY total_rev DESC;
                """, p_params)
                revenue_by_plan = [
                    {"plan_id": r[0], "plan_name": r[1], "total_revenue": r[2]}
                    for r in cursor.fetchall()
                ]

                # 6. Plan Distribution
                cursor.execute(f"""
                    SELECT p.plan_id, COALESCE(pl.name, 'Plan #' || p.plan_id::text) as plan_name,
                           COUNT(DISTINCT p.user_id) as users_count
                    FROM subscriptions_payment p
                    LEFT JOIN subscriptions_plan pl ON p.plan_id = pl.id
                    WHERE {' AND '.join(p_where)}
                    GROUP BY p.plan_id, pl.name
                    ORDER BY users_count DESC;
                """, p_params)
                plan_rows = cursor.fetchall()
                total_plan_users = sum(r[2] for r in plan_rows) or 1
                plan_distribution = [
                    {
                        "plan_id": r[0],
                        "plan_name": r[1],
                        "users": r[2],
                        "percentage": round((r[2] / total_plan_users) * 100, 1)
                    }
                    for r in plan_rows
                ]

                # 7. Consultations Breakdown
                consultations_breakdown = {
                    "by_category": [
                        {"name": "In-House", "count": metrics["inhouse_consultations"], "color": "#3b82f6"},
                        {"name": "Specialist Expert", "count": metrics["expert_consultations"], "color": "#a855f7"}
                    ],
                    "by_type": [
                        {"name": "Virtual Video", "count": metrics["virtual_consultations"], "color": "#0ea5e9"},
                        {"name": "In-Person Clinic", "count": metrics["inperson_consultations"], "color": "#10b981"}
                    ],
                    "by_status": [
                        {"name": "Confirmed", "count": metrics["confirmed_consultations"], "color": "#22c55e"},
                        {"name": "Pending Review", "count": metrics["pending_consultations"], "color": "#f59e0b"},
                        {"name": "Cancelled", "count": metrics["cancelled_consultations"], "color": "#ef4444"}
                    ]
                }

                # 8. Recent Activities
                cursor.execute("""
                    SELECT id, full_name, email, role, date_joined
                    FROM user_user
                    ORDER BY date_joined DESC
                    LIMIT 6;
                """)
                recent_signups = [
                    {
                        "id": r[0],
                        "full_name": r[1] or f"User #{r[0]}",
                        "email": r[2],
                        "role": r[3] or "user",
                        "date_joined": r[4].isoformat() if r[4] else None
                    }
                    for r in cursor.fetchall()
                ]

                cursor.execute("""
                    SELECT p.id, p.user_id, COALESCE(u.full_name, 'User #' || p.user_id::text) as user_name,
                           COALESCE(pl.name, 'Plan #' || p.plan_id::text) as plan_name,
                           p.amount, p.status, p.created_at
                    FROM subscriptions_payment p
                    LEFT JOIN user_user u ON p.user_id = u.id
                    LEFT JOIN subscriptions_plan pl ON p.plan_id = pl.id
                    ORDER BY p.created_at DESC
                    LIMIT 6;
                """)
                recent_payments = [
                    {
                        "id": r[0],
                        "user_id": r[1],
                        "user_name": r[2],
                        "plan_name": r[3],
                        "amount": r[4],
                        "status": r[5],
                        "created_at": r[6].isoformat() if r[6] else None
                    }
                    for r in cursor.fetchall()
                ]

                cursor.execute("""
                    SELECT a.id, COALESCE(p.full_name, 'Patient #' || a.patient_id::text) as patient_name,
                           COALESCE(n.full_name, 'Dr. #' || a.nutritionist_id::text) as nutritionist_name,
                           a.appointment_category, a.appointment_type, a.status, a.slot_date, a.fee_amount, a.created_at
                    FROM appointments_appointment a
                    LEFT JOIN user_user p ON a.patient_id = p.id
                    LEFT JOIN user_user n ON a.nutritionist_id = n.id
                    ORDER BY a.created_at DESC
                    LIMIT 6;
                """)
                recent_consultations = [
                    {
                        "id": r[0],
                        "patient_name": r[1],
                        "nutritionist_name": r[2],
                        "category": r[3] or "IN_HOUSE",
                        "type": r[4] or "VIRTUAL",
                        "status": r[5] or "CONFIRMED",
                        "slot_date": str(r[6]) if r[6] else None,
                        "fee_amount": float(r[7]) if r[7] else 0,
                        "created_at": r[8].isoformat() if r[8] else None
                    }
                    for r in cursor.fetchall()
                ]

            return Response({
                "status": "success",
                "filter": {
                    "range": range_val,
                    "date": date_val or None,
                    "month": month_val or None,
                    "year": year_val or None
                },
                "metrics": metrics,
                "charts": {
                    "user_growth": user_growth,
                    "revenue_trend": revenue_trend,
                    "revenue_by_plan": revenue_by_plan,
                    "plan_distribution": plan_distribution,
                    "consultations_breakdown": consultations_breakdown
                },
                "recent_activity": {
                    "recent_signups": recent_signups,
                    "recent_payments": recent_payments,
                    "recent_consultations": recent_consultations
                }
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)
