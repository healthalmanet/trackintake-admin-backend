import json
from datetime import datetime, timezone
from django.db import connection
from django.contrib.auth.hashers import check_password, make_password
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


def check_db_connection():
    try:
        connection.ensure_connection()
        return True
    except Exception:
        return False


# ===================== ADMIN LOGIN ===================== #
class AdminLoginAPI(APIView):
    """Admin login endpoint using raw SQL against user_user"""
    def post(self, request):
        try:
            email = request.data.get("email", "").strip()
            password = request.data.get("password", "").strip()

            if not email or not password:
                return Response(
                    {"error": "Email and password are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            query = """
                SELECT id, full_name, email, password, role, is_admin, is_active
                FROM user_user
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1;
            """
            with connection.cursor() as cursor:
                cursor.execute(query, [email])
                row = cursor.fetchone()

            if not row:
                return Response(
                    {"error": "Invalid email or password"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user_id, full_name, db_email, db_password, role, is_admin, is_active = row

            if not is_active:
                return Response(
                    {"error": "This account has been disabled or blocked by an administrator. Login access is denied."},
                    status=status.HTTP_403_FORBIDDEN
                )

            if str(role).lower() != "admin" and not is_admin:
                return Response(
                    {"error": "Only admins can access this panel"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Check password: supports plain text or Django PBKDF2 hash
            valid = (db_password == password)
            if not valid:
                try:
                    valid = check_password(password, db_password)
                except Exception:
                    valid = False

            if not valid:
                return Response(
                    {"error": "Invalid email or password"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                "message": "Login successful",
                "user": {
                    "id": user_id,
                    "full_name": full_name,
                    "email": db_email,
                    "role": role
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===================== USER LIST & CREATE ===================== #
class UserListCreateView(APIView):
    def get(self, request):
        search = request.query_params.get("search", "").strip()
        role = request.query_params.get("role", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        date_filter = request.query_params.get("date", "").strip()
        month_filter = request.query_params.get("month", "").strip()
        year_filter = request.query_params.get("year", "").strip()
        city_filter = request.query_params.get("city", "").strip()
        country_filter = request.query_params.get("country", "").strip()
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        offset = (page - 1) * page_size

        where = ["1=1"]
        params = []

        if search:
            where.append("(u.full_name ILIKE %s OR u.email ILIKE %s OR u.phone_number ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        if role and role.lower() != "all":
            if role.lower() in ("inhouse", "in_house"):
                where.append("(LOWER(u.role) = 'nutritionist' AND LOWER(COALESCE(np.nutritionist_type, u.nutritionist_type, 'inhouse')) IN ('inhouse', 'in_house'))")
            elif role.lower() == "expert":
                where.append("(LOWER(u.role) = 'nutritionist' AND LOWER(COALESCE(np.nutritionist_type, u.nutritionist_type, '')) = 'expert')")
            else:
                where.append("LOWER(u.role) = LOWER(%s)")
                params.append(role)

        if status_filter.lower() == "active":
            where.append("u.is_active = true")
        elif status_filter.lower() == "inactive":
            where.append("u.is_active = false")

        if date_filter:
            where.append("DATE(u.date_joined) = %s")
            params.append(date_filter)
        elif month_filter and year_filter:
            where.append("EXTRACT(MONTH FROM u.date_joined) = %s AND EXTRACT(YEAR FROM u.date_joined) = %s")
            params.extend([int(month_filter), int(year_filter)])
        elif year_filter:
            where.append("EXTRACT(YEAR FROM u.date_joined) = %s")
            params.append(int(year_filter))

        if city_filter:
            where.append("hp.city ILIKE %s")
            params.append(f"%{city_filter}%")

        if country_filter:
            where.append("hp.country ILIKE %s")
            params.append(f"%{country_filter}%")

        where_sql = " AND ".join(where)

        count_query = f"""
            SELECT COUNT(DISTINCT u.id)
            FROM user_user u
            LEFT JOIN "userProfile_userprofile" hp ON u.id = hp.user_id
            LEFT JOIN nutritionist_nutritionistprofile np ON u.id = np.user_id
            WHERE {where_sql};
        """

        data_query = f"""
            SELECT 
                u.id, u.full_name, u.email, u.phone_number, u.role, u.is_active, u.date_joined,
                COALESCE(np.nutritionist_type, u.nutritionist_type, '') as nutritionist_type,
                u.is_nutritionist_approved, u.is_admin,
                hp.city,
                (SELECT pl.name FROM subscriptions_usersubscription us 
                 JOIN subscriptions_plan pl ON us.plan_id = pl.id 
                 WHERE us.user_id = u.id AND us.is_active = true LIMIT 1) as plan_name
            FROM user_user u
            LEFT JOIN "userProfile_userprofile" hp ON u.id = hp.user_id
            LEFT JOIN nutritionist_nutritionistprofile np ON u.id = np.user_id
            WHERE {where_sql}
            ORDER BY u.date_joined DESC
            LIMIT %s OFFSET %s;
        """

        with connection.cursor() as cursor:
            # Global overview counts for KPI cards
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(*) FILTER (WHERE LOWER(u.role) = 'user') as total_patients,
                    COUNT(*) FILTER (WHERE LOWER(u.role) = 'nutritionist') as total_nutritionists,
                    COUNT(*) FILTER (WHERE LOWER(u.role) = 'nutritionist' AND (LOWER(COALESCE(np.nutritionist_type, u.nutritionist_type, '')) IN ('inhouse', 'in_house'))) as inhouse,
                    COUNT(*) FILTER (WHERE LOWER(u.role) = 'nutritionist' AND (LOWER(COALESCE(np.nutritionist_type, u.nutritionist_type, '')) = 'expert')) as expert,
                    COUNT(*) FILTER (WHERE u.is_active = true) as active_users
                FROM user_user u
                LEFT JOIN nutritionist_nutritionistprofile np ON u.id = np.user_id;
            """)
            g_row = cursor.fetchone() or (0, 0, 0, 0, 0, 0)
            metrics = {
                "total_users": g_row[0] or 0,
                "total_patients": g_row[1] or 0,
                "total_nutritionists": g_row[2] or 0,
                "inhouse_nutritionists": g_row[3] or 0,
                "expert_nutritionists": g_row[4] or 0,
                "active_users": g_row[5] or 0,
            }

            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            cursor.execute(data_query, params + [page_size, offset])
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "id": r[0],
                "full_name": r[1],
                "email": r[2],
                "phone_number": r[3],
                "role": r[4],
                "is_active": bool(r[5]),
                "date_joined": r[6].isoformat() if r[6] else None,
                "nutritionist_type": r[7],
                "is_nutritionist_approved": bool(r[8]),
                "is_admin": bool(r[9]),
                "city": r[10],
                "plan": r[11],
            })

        total_pages = max(1, (total + page_size - 1) // page_size)
        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "metrics": metrics,
            "results": results
        })

    def post(self, request):
        full_name = request.data.get("full_name", "").strip()
        email = request.data.get("email", "").strip()
        phone_number = request.data.get("phone_number", "").strip()
        password = request.data.get("password", "").strip()
        role = request.data.get("role", "user").strip()

        if not full_name or not email:
            return Response({"error": "full_name and email are required"}, status=400)

        now_utc = datetime.now(timezone.utc)
        query = """
            INSERT INTO user_user (full_name, email, phone_number, password, role, is_active, is_admin, is_superuser, date_joined)
            VALUES (%s, %s, %s, %s, %s, true, false, false, %s)
            RETURNING id;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [full_name, email, phone_number, password, role, now_utc])
            new_id = cursor.fetchone()[0]

            # Broadcast real-time WebSocket notification if a new nutritionist registers
            if str(role).lower() == "nutritionist":
                try:
                    nutri_type = request.data.get("nutritionist_type", "inhouse")
                    from notifications.utils import notify_nutritionist_registered
                    notify_nutritionist_registered(
                        user_id=new_id,
                        full_name=full_name,
                        email=email,
                        nutritionist_type=nutri_type
                    )
                except Exception as ex:
                    print(f"[Nutritionist Registration Notification Warning]: {ex}")

        return Response({"id": new_id, "message": "User created successfully"}, status=status.HTTP_201_CREATED)


# ===================== USER DETAIL ===================== #
class UserDetailView(APIView):
    """
    Complete 360-degree user profile view:
    - User core data (user_user)
    - Health profile (userProfile_userprofile)
    - Nutritionist profile (nutritionist_nutritionistprofile)
    - Subscriptions & Payments history
    - Appointments history
    - Editable via PUT / PATCH with pure parameterized raw SQL.
    """
    def get(self, request, user_id):
        try:
            with connection.cursor() as cursor:
                # 1. Core user data
                cursor.execute("""
                    SELECT id, full_name, email, phone_number, role, is_active, is_admin,
                           date_joined, last_login, plan, nutritionist_type, is_nutritionist_approved
                    FROM user_user
                    WHERE id = %s;
                """, [user_id])
                u = cursor.fetchone()
                if not u:
                    return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

                user_data = {
                    "id": u[0],
                    "full_name": u[1] or "",
                    "email": u[2] or "",
                    "phone_number": u[3] or "",
                    "role": u[4] or "user",
                    "is_active": bool(u[5]),
                    "is_admin": bool(u[6]),
                    "date_joined": u[7].isoformat() if u[7] else None,
                    "last_login": u[8].isoformat() if u[8] else None,
                    "plan": u[9] or "",
                    "nutritionist_type": u[10] or "",
                    "is_nutritionist_approved": bool(u[11]),
                }

                # 2. Health Profile
                cursor.execute("""
                    SELECT id, height_cm, weight_kg, diet_type, allergies, goal, activity_level,
                           city, country, gender, date_of_birth, occupation,
                           is_diabetic, is_hypertensive, has_heart_condition, has_thyroid_disorder,
                           has_arthritis, has_gastric_issues, other_chronic_condition, family_history,
                           is_pregnant, is_breastfeeding
                    FROM "userProfile_userprofile"
                    WHERE user_id = %s;
                """, [user_id])
                hp = cursor.fetchone()
                health_profile = None
                if hp:
                    health_profile = {
                        "id": hp[0],
                        "height_cm": float(hp[1]) if hp[1] is not None else None,
                        "weight_kg": float(hp[2]) if hp[2] is not None else None,
                        "diet_type": hp[3] or "",
                        "allergies": hp[4] or "",
                        "goal": hp[5] or "",
                        "activity_level": hp[6] or "",
                        "city": hp[7] or "",
                        "country": hp[8] or "",
                        "gender": hp[9] or "",
                        "date_of_birth": str(hp[10]) if hp[10] else None,
                        "occupation": hp[11] or "",
                        "is_diabetic": bool(hp[12]),
                        "is_hypertensive": bool(hp[13]),
                        "has_heart_condition": bool(hp[14]),
                        "has_thyroid_disorder": bool(hp[15]),
                        "has_arthritis": bool(hp[16]),
                        "has_gastric_issues": bool(hp[17]),
                        "other_chronic_condition": hp[18] or "",
                        "family_history": hp[19] or "",
                        "is_pregnant": bool(hp[20]),
                        "is_breastfeeding": bool(hp[21]),
                    }

                # 3. Nutritionist Profile
                cursor.execute("""
                    SELECT id, nutritionist_type, is_verified, verified_at, years_of_experience,
                           qualification, online_price, offline_price, pending_online_price, pending_offline_price,
                           price_approval_status, price_rejection_reason, professional_title, professional_bio,
                           specializations, languages_spoken, registration_number, issuing_authority,
                           current_organization, offline_location, is_virtual_enabled,
                           government_id, qualification_certificate, registration_certificate, experience_certificate
                    FROM nutritionist_nutritionistprofile
                    WHERE user_id = %s;
                """, [user_id])
                np = cursor.fetchone()
                nutritionist_profile = None
                if np:
                    specs = np[14]
                    if isinstance(specs, str):
                        try: specs = json.loads(specs)
                        except: specs = [specs]
                    langs = np[15]
                    if isinstance(langs, str):
                        try: langs = json.loads(langs)
                        except: langs = [langs]

                    nutritionist_profile = {
                        "id": np[0],
                        "nutritionist_type": np[1] or "inhouse",
                        "is_verified": bool(np[2]),
                        "verified_at": np[3].isoformat() if np[3] else None,
                        "years_of_experience": np[4] or 0,
                        "qualification": np[5] or "",
                        "online_price": float(np[6]) if np[6] else 0.0,
                        "offline_price": float(np[7]) if np[7] else 0.0,
                        "pending_online_price": float(np[8]) if np[8] else None,
                        "pending_offline_price": float(np[9]) if np[9] else None,
                        "price_approval_status": np[10] or "approved",
                        "price_rejection_reason": np[11] or "",
                        "professional_title": np[12] or "",
                        "professional_bio": np[13] or "",
                        "specializations": specs or [],
                        "languages_spoken": langs or [],
                        "registration_number": np[16] or "",
                        "issuing_authority": np[17] or "",
                        "current_organization": np[18] or "",
                        "offline_location": np[19] or "",
                        "is_virtual_enabled": bool(np[20]),
                        "government_id": np[21] or "",
                        "qualification_certificate": np[22] or "",
                        "registration_certificate": np[23] or "",
                        "experience_certificate": np[24] or "",
                        "documents": {
                            "government_id": np[21] or "",
                            "qualification_certificate": np[22] or "",
                            "registration_certificate": np[23] or "",
                            "experience_certificate": np[24] or "",
                        }
                    }

                # 4. Subscriptions
                cursor.execute("""
                    SELECT s.id, s.start_date, s.end_date, s.remaining_inhouse, s.remaining_expert,
                           s.is_active, p.id as plan_id, COALESCE(p.name, 'Subscription Plan') as plan_name,
                           COALESCE(p.price, 0) as price, s.created_at
                    FROM subscriptions_usersubscription s
                    LEFT JOIN subscriptions_plan p ON s.plan_id = p.id
                    WHERE s.user_id = %s
                    ORDER BY s.created_at DESC;
                """, [user_id])
                subscriptions = [
                    {
                        "id": r[0],
                        "start_date": str(r[1]) if r[1] else None,
                        "end_date": str(r[2]) if r[2] else None,
                        "remaining_inhouse": r[3] or 0,
                        "remaining_expert": r[4] or 0,
                        "is_active": bool(r[5]),
                        "plan_id": r[6],
                        "plan_name": r[7],
                        "price": r[8],
                        "created_at": r[9].isoformat() if r[9] else None,
                    }
                    for r in cursor.fetchall()
                ]

                # 5. Payments
                cursor.execute("""
                    SELECT p.id, p.amount, p.status, p.razorpay_payment_id, p.created_at,
                           COALESCE(pl.name, 'Plan #' || p.plan_id::text) as plan_name
                    FROM subscriptions_payment p
                    LEFT JOIN subscriptions_plan pl ON p.plan_id = pl.id
                    WHERE p.user_id = %s
                    ORDER BY p.created_at DESC;
                """, [user_id])
                payments = [
                    {
                        "id": r[0],
                        "amount": r[1],
                        "status": r[2],
                        "razorpay_payment_id": r[3] or "",
                        "created_at": r[4].isoformat() if r[4] else None,
                        "plan_name": r[5],
                    }
                    for r in cursor.fetchall()
                ]

                # 6. Appointments
                cursor.execute("""
                    SELECT a.id, a.slot_date, a.slot_start_time, a.appointment_category,
                           a.appointment_type, a.status, COALESCE(a.fee_amount, 0),
                           COALESCE(a.payment_status, 'UNPAID'),
                           n.full_name as nutri_name, p.full_name as patient_name,
                           a.created_at
                    FROM appointments_appointment a
                    LEFT JOIN user_user n ON a.nutritionist_id = n.id
                    LEFT JOIN user_user p ON a.patient_id = p.id
                    WHERE a.patient_id = %s OR a.nutritionist_id = %s
                    ORDER BY a.created_at DESC
                    LIMIT 10;
                """, [user_id, user_id])
                appointments = [
                    {
                        "id": r[0],
                        "slot_date": str(r[1]) if r[1] else None,
                        "slot_start_time": str(r[2]) if r[2] else None,
                        "category": r[3] or "IN_HOUSE",
                        "type": r[4] or "VIRTUAL",
                        "status": r[5] or "CONFIRMED",
                        "fee_amount": float(r[6]),
                        "payment_status": r[7],
                        "nutritionist_name": r[8] or "Nutritionist",
                        "patient_name": r[9] or "Patient",
                        "created_at": r[10].isoformat() if r[10] else None,
                    }
                    for r in cursor.fetchall()
                ]

            resp_data = {
                **user_data,
                "status": "success",
                "user": user_data,
                "health_profile": health_profile,
                "nutritionist_profile": nutritionist_profile,
                "subscriptions": subscriptions,
                "payments": payments,
                "appointments": appointments,
            }
            return Response(resp_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, user_id):
        return self.patch(request, user_id)

    def patch(self, request, user_id):
        try:
            data = request.data
            user_updates = []
            user_params = []

            # 1. Update user_user
            for field in ["full_name", "email", "phone_number", "role", "is_active", "plan", "nutritionist_type"]:
                if field in data:
                    val = data[field]
                    if field == "is_active":
                        if isinstance(val, str):
                            val = val.lower() in ("true", "1", "active")
                        else:
                            val = bool(val)
                    user_updates.append(f"{field} = %s")
                    user_params.append(val)

            with connection.cursor() as cursor:
                if user_updates:
                    user_params.append(user_id)
                    query = f"UPDATE user_user SET {', '.join(user_updates)} WHERE id = %s RETURNING id;"
                    cursor.execute(query, user_params)
                    if not cursor.fetchone():
                        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

                # 2. Update or Insert Health Profile if health fields provided
                health_data = data.get("health_profile") or data
                hp_fields = [
                    "height_cm", "weight_kg", "diet_type", "allergies", "goal", "activity_level",
                    "city", "country", "gender", "occupation", "is_diabetic", "is_hypertensive",
                    "has_heart_condition", "has_thyroid_disorder", "has_arthritis", "has_gastric_issues",
                    "other_chronic_condition", "family_history"
                ]
                hp_updates = []
                hp_params = []
                for f in hp_fields:
                    if f in health_data:
                        hp_updates.append(f)
                        hp_params.append(health_data[f])

                if hp_updates:
                    # Check if health profile exists
                    cursor.execute('SELECT id FROM "userProfile_userprofile" WHERE user_id = %s;', [user_id])
                    row = cursor.fetchone()
                    if row:
                        set_clauses = [f"{f} = %s" for f in hp_updates]
                        q = f'UPDATE "userProfile_userprofile" SET {", ".join(set_clauses)} WHERE user_id = %s;'
                        cursor.execute(q, hp_params + [user_id])
                    else:
                        cols = ["user_id"] + hp_updates
                        placeholders = ", ".join(["%s"] * len(cols))
                        q = f'INSERT INTO "userProfile_userprofile" ({", ".join(cols)}) VALUES ({placeholders});'
                        cursor.execute(q, [user_id] + hp_params)

                # 3. Update Nutritionist Profile if nutritionist fields provided
                nutri_data = data.get("nutritionist_profile") or data
                np_fields = [
                    "nutritionist_type", "is_verified", "years_of_experience", "qualification",
                    "online_price", "offline_price", "professional_title", "professional_bio",
                    "current_organization", "offline_location", "registration_number", "issuing_authority"
                ]
                np_updates = []
                np_params = []
                for f in np_fields:
                    if f in nutri_data:
                        np_updates.append(f)
                        np_params.append(nutri_data[f])

                if np_updates:
                    cursor.execute("SELECT id FROM nutritionist_nutritionistprofile WHERE user_id = %s;", [user_id])
                    row = cursor.fetchone()
                    if row:
                        set_clauses = [f"{f} = %s" for f in np_updates]
                        q = f"UPDATE nutritionist_nutritionistprofile SET {', '.join(set_clauses)} WHERE user_id = %s;"
                        cursor.execute(q, np_params + [user_id])
                    else:
                        cols = ["user_id"] + np_updates
                        placeholders = ", ".join(["%s"] * len(cols))
                        q = f"INSERT INTO nutritionist_nutritionistprofile ({', '.join(cols)}) VALUES ({placeholders});"
                        cursor.execute(q, [user_id] + np_params)

            return Response({
                "status": "success",
                "message": "User profile updated successfully",
                "id": user_id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, user_id):
        query = "UPDATE user_user SET is_active = false WHERE id = %s RETURNING id;"
        with connection.cursor() as cursor:
            cursor.execute(query, [user_id])
            updated = cursor.fetchone()

        if not updated:
            return Response({"error": "User not found"}, status=404)

        return Response({"message": "User access deactivated successfully"})


# ===================== USER HEALTH PROFILE ===================== #
class UserHealthProfileAPI(APIView):
    def get(self, request, user_id):
        query = """
            SELECT user_id, date_of_birth, country, mobile_number, gender, occupation,
                   height_cm, weight_kg, activity_level, goal, diet_type, allergies,
                   is_diabetic, is_hypertensive, has_heart_condition, has_thyroid_disorder,
                   has_arthritis, has_gastric_issues, is_pregnant, is_breastfeeding, city
            FROM "userProfile_userprofile"
            WHERE user_id = %s
            LIMIT 1;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [user_id])
            r = cursor.fetchone()

        if not r:
            return Response({"message": "No health profile found"}, status=404)

        return Response({
            "user_id": r[0],
            "date_of_birth": str(r[1]) if r[1] else None,
            "country": r[2],
            "mobile_number": r[3],
            "gender": r[4],
            "occupation": r[5],
            "height_cm": r[6],
            "weight_kg": r[7],
            "activity_level": r[8],
            "goal": r[9],
            "diet_type": r[10],
            "allergies": r[11],
            "is_diabetic": bool(r[12]),
            "is_hypertensive": bool(r[13]),
            "has_heart_condition": bool(r[14]),
            "has_thyroid_disorder": bool(r[15]),
            "has_arthritis": bool(r[16]),
            "has_gastric_issues": bool(r[17]),
            "is_pregnant": bool(r[18]),
            "is_breastfeeding": bool(r[19]),
            "city": r[20],
        })


# ===================== NUTRITIONISTS LIST & DETAILS ===================== #
class NutritionistListAPIView(APIView):
    def get(self, request):
        query = """
            SELECT 
                u.id as user_id, u.full_name as user_name, u.email,
                np.id, np.nutritionist_type, np.is_virtual_enabled, np.is_verified,
                np.online_price, np.offline_price, np.years_of_experience, np.qualification,
                np.registration_number, np.offline_location,
                (SELECT COUNT(*) FROM nutritionist_patientassignment WHERE nutritionist_id = u.id) as patient_count
            FROM user_user u
            LEFT JOIN nutritionist_nutritionistprofile np ON u.id = np.user_id
            WHERE LOWER(u.role) = 'nutritionist'
            ORDER BY u.id DESC;
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "id": r[3] or r[0],
                "user_id": r[0],
                "user_name": r[1] or f"Nutritionist #{r[0]}",
                "email": r[2],
                "nutritionist_type": r[4] or "inhouse",
                "is_virtual_enabled": bool(r[5]),
                "is_verified": bool(r[6]),
                "online_price": r[7],
                "offline_price": r[8],
                "years_of_experience": r[9],
                "qualification": r[10],
                "registration_number": r[11],
                "offline_location": r[12],
                "patient_count": r[13] or 0
            })

        return Response({"status": "success", "count": len(results), "data": results})


class AvailableNutritionistsView(APIView):
    def get(self, request):
        query = """
            SELECT u.id, u.full_name, u.email, np.id as profile_id, np.nutritionist_type, np.is_verified
            FROM user_user u
            LEFT JOIN nutritionist_nutritionistprofile np ON u.id = np.user_id
            WHERE LOWER(u.role) = 'nutritionist'
            ORDER BY u.full_name ASC;
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        results = [
            {
                "id": r[0],
                "full_name": r[1],
                "email": r[2],
                "profile_id": r[3],
                "nutritionist_type": r[4] or "inhouse",
                "is_verified": bool(r[5])
            } for r in rows
        ]
        return Response(results)


# ===================== PATIENT ASSIGNMENT ===================== #
class AssignNutritionistAPI(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        nutritionist_id = request.data.get("nutritionist_id")

        if not user_id or not nutritionist_id:
            return Response({"error": "user_id and nutritionist_id are required"}, status=400)

        now_utc = datetime.now(timezone.utc)
        with connection.cursor() as cursor:
            # Check user and nutritionist exist
            cursor.execute("SELECT id FROM user_user WHERE id = %s;", [user_id])
            if not cursor.fetchone():
                return Response({"error": "User not found"}, status=404)

            cursor.execute("SELECT id FROM user_user WHERE id = %s AND LOWER(role) = 'nutritionist';", [nutritionist_id])
            if not cursor.fetchone():
                return Response({"error": "Nutritionist not found"}, status=404)

            # Check if assignment already exists
            cursor.execute("SELECT id FROM nutritionist_patientassignment WHERE patient_id = %s;", [user_id])
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    "UPDATE nutritionist_patientassignment SET nutritionist_id = %s, assigned_at = %s WHERE id = %s;",
                    [nutritionist_id, now_utc, existing[0]]
                )
            else:
                cursor.execute(
                    "INSERT INTO nutritionist_patientassignment (patient_id, nutritionist_id, assigned_at) VALUES (%s, %s, %s);",
                    [user_id, nutritionist_id, now_utc]
                )

        return Response({"message": "Nutritionist assigned successfully"}, status=200)


class AssignedNutritionistAPI(APIView):
    def get(self, request, user_id):
        query = """
            SELECT u.id, u.full_name, u.email, pa.assigned_at
            FROM nutritionist_patientassignment pa
            JOIN user_user u ON pa.nutritionist_id = u.id
            WHERE pa.patient_id = %s
            ORDER BY pa.assigned_at DESC
            LIMIT 1;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [user_id])
            r = cursor.fetchone()

        if not r:
            return Response({"message": "No nutritionist assigned"}, status=404)

        return Response({
            "id": r[0],
            "full_name": r[1],
            "email": r[2],
            "assigned_at": r[3].isoformat() if r[3] else None
        })


class EligibleUsersForNutritionistAPI(APIView):
    def get(self, request):
        query = """
            SELECT u.id, u.full_name, u.email, u.phone_number
            FROM user_user u
            WHERE LOWER(u.role) != 'nutritionist' AND LOWER(u.role) != 'admin'
            ORDER BY u.date_joined DESC
            LIMIT 200;
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        results = [{"id": r[0], "full_name": r[1], "email": r[2], "phone_number": r[3]} for r in rows]
        return Response(results)


# ===================== PASSWORD RESET & FORGOT ===================== #
class ResetPasswordAPI(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        new_password = request.data.get('new_password', '').strip()
        confirm_password = request.data.get('confirm_password', '').strip()

        if not user_id:
            return Response({"error": "user_id is required"}, status=400)
        if not new_password or new_password != confirm_password:
            return Response({"error": "Passwords do not match"}, status=400)
        if len(new_password) < 6:
            return Response({"error": "Password must be at least 6 characters"}, status=400)

        hashed = make_password(new_password)
        query = "UPDATE user_user SET password = %s WHERE id = %s RETURNING full_name;"
        with connection.cursor() as cursor:
            cursor.execute(query, [hashed, user_id])
            row = cursor.fetchone()

        if not row:
            return Response({"error": "User not found"}, status=404)

        return Response({
            "success": True,
            "message": f"Password for '{row[0]}' has been reset successfully"
        }, status=200)


class ForgotPasswordAPI(APIView):
    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response({"error": "email is required"}, status=400)

        return Response({"success": True, "message": "Password reset instructions sent."})


# ===================== USER STATUS / BLOCK ACCESS ===================== #
class UserToggleStatusAPI(APIView):
    """
    Toggle or explicitly set user active status (block / unblock account).
    If is_active is false, the user account is disabled and prevented from logging in.
    """
    def post(self, request, user_id):
        is_active = request.data.get("is_active")

        with connection.cursor() as cursor:
            if is_active is None:
                # Toggle current status
                cursor.execute("SELECT is_active, full_name, email FROM user_user WHERE id = %s;", [user_id])
                row = cursor.fetchone()
                if not row:
                    return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
                new_status = not bool(row[0])
                full_name = row[1]
            else:
                if isinstance(is_active, str):
                    new_status = is_active.lower() in ("true", "1", "active")
                else:
                    new_status = bool(is_active)

                cursor.execute("SELECT full_name, email FROM user_user WHERE id = %s;", [user_id])
                row = cursor.fetchone()
                if not row:
                    return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
                full_name = row[0]

            cursor.execute("UPDATE user_user SET is_active = %s WHERE id = %s RETURNING id, is_active;", [new_status, user_id])
            updated = cursor.fetchone()

        action_word = "activated and login access restored" if new_status else "disabled and login access blocked"
        return Response({
            "success": True,
            "user_id": user_id,
            "full_name": full_name,
            "is_active": new_status,
            "message": f"Account for '{full_name}' has been {action_word}."
        }, status=status.HTTP_200_OK)


# ===================== OTHER UTILITY APIS ===================== #
class UsersWithPaymentNoProfileAPI(APIView):
    def get(self, request):
        query = """
            SELECT p.user_id, p.amount, p.plan_id, p.status, p.created_at, u.full_name
            FROM subscriptions_payment p
            LEFT JOIN "userProfile_userprofile" up ON p.user_id = up.user_id
            LEFT JOIN user_user u ON p.user_id = u.id
            WHERE up.id IS NULL
            ORDER BY p.created_at DESC;
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
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
        return Response({
            "count": len(users_data),
            "total_missing_users": len(set(r[0] for r in rows if r[0])),
            "users_data": users_data
        })


class SubscribedUsersAPI(APIView):
    def get(self, request):
        query = """
            SELECT u.id, u.full_name, u.email, pl.name as plan_name, s.start_date, s.end_date
            FROM subscriptions_usersubscription s
            JOIN user_user u ON s.user_id = u.id
            JOIN subscriptions_plan pl ON s.plan_id = pl.id
            WHERE s.is_active = true
            ORDER BY s.created_at DESC;
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        results = [
            {
                "id": r[0],
                "full_name": r[1],
                "email": r[2],
                "plan_name": r[3],
                "start_date": str(r[4]),
                "end_date": str(r[5]),
            } for r in rows
        ]
        return Response(results)


class UserPlanNotificationAPI(APIView):
    def get(self, request):
        return Response({"status": "success", "notifications": []})


class DebugSubscriptionsAPI(APIView):
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM subscriptions_usersubscription;")
            total_subs = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM subscriptions_plan;")
            total_plans = cursor.fetchone()[0]
        return Response({"total_subscriptions": total_subs, "total_plans": total_plans})
