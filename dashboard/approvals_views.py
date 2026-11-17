import json
from datetime import datetime, timezone
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class ApprovalsListAPI(APIView):
    """
    List profiles requiring administrative verification and review:
    - Nutritionist credentials verification (degrees, certificates, registration)
    - Price change approvals (online/offline price approval)
    - Patient / User account verification & activations
    Pure parameterized raw SQL - Zero models.
    """
    def get(self, request):
        try:
            category = request.query_params.get("category", "all").strip().lower()  # all, nutritionist, patient, price
            status_filter = request.query_params.get("status", "all").strip().lower()  # all, pending, approved
            search = request.query_params.get("search", "").strip()
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = max(1, min(100, int(request.query_params.get("page_size", 15))))
            offset = (page - 1) * page_size

            with connection.cursor() as cursor:
                # 1. Executive Metrics
                cursor.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE is_verified = false) as pending_nutritionists,
                        COUNT(*) FILTER (WHERE is_verified = true) as verified_nutritionists,
                        COUNT(*) FILTER (WHERE LOWER(price_approval_status) = 'pending' OR pending_online_price IS NOT NULL) as pending_price_reviews,
                        COUNT(*) FILTER (WHERE LOWER(nutritionist_type) = 'inhouse') as inhouse_nutritionists,
                        COUNT(*) FILTER (WHERE LOWER(nutritionist_type) = 'expert') as expert_nutritionists,
                        COUNT(*) as total_nutritionist_profiles
                    FROM nutritionist_nutritionistprofile;
                """)
                m = cursor.fetchone()
                metrics = {
                    "pending_nutritionists": m[0] or 0,
                    "verified_nutritionists": m[1] or 0,
                    "pending_price_reviews": m[2] or 0,
                    "inhouse_nutritionists": m[3] or 0,
                    "expert_nutritionists": m[4] or 0,
                    "total_profiles": m[5] or 0,
                }

                # 2. Build Query
                where_clauses = ["1=1"]
                params = []

                if status_filter == "pending":
                    where_clauses.append("(np.is_verified = false OR LOWER(np.price_approval_status) = 'pending' OR u.is_active = false)")
                elif status_filter == "approved":
                    where_clauses.append("np.is_verified = true")

                if category == "nutritionist":
                    where_clauses.append("u.role = 'nutritionist'")
                elif category == "inhouse":
                    where_clauses.append("LOWER(np.nutritionist_type) = 'inhouse'")
                elif category == "expert":
                    where_clauses.append("LOWER(np.nutritionist_type) = 'expert'")
                elif category == "price":
                    where_clauses.append("(LOWER(np.price_approval_status) = 'pending' OR np.pending_online_price IS NOT NULL)")

                if search:
                    where_clauses.append("""
                        (u.full_name ILIKE %s OR u.email ILIKE %s OR 
                         COALESCE(np.qualification, '') ILIKE %s OR 
                         COALESCE(np.professional_title, '') ILIKE %s OR 
                         COALESCE(np.registration_number, '') ILIKE %s)
                    """)
                    s = f"%{search}%"
                    params.extend([s, s, s, s, s])

                where_sql = " AND ".join(where_clauses)

                cursor.execute(f"""
                    SELECT COUNT(*)
                    FROM nutritionist_nutritionistprofile np
                    JOIN user_user u ON np.user_id = u.id
                    WHERE {where_sql};
                """, params)
                total_filtered = cursor.fetchone()[0]

                cursor.execute(f"""
                    SELECT 
                        np.id, np.user_id, u.full_name, u.email, u.phone_number, u.role,
                        u.is_active, u.date_joined,
                        np.is_verified, np.verified_at, np.nutritionist_type,
                        COALESCE(np.years_of_experience, 0), np.qualification, np.current_organization,
                        np.professional_title, np.professional_bio,
                        np.online_price, np.offline_price, np.pending_online_price, np.pending_offline_price,
                        np.price_approval_status, np.price_rejection_reason,
                        np.government_id, np.qualification_certificate, np.registration_certificate, np.experience_certificate,
                        np.registration_number, np.issuing_authority, np.specializations, np.languages_spoken,
                        np.created_at, np.updated_at,
                        np.is_online_available, np.is_offline_available, np.offline_location,
                        np.offline_payment_required, np.is_virtual_enabled, np.additional_certifications,
                        np.profile_photo,
                        hp.city, hp.country,
                        (SELECT COUNT(*) FROM nutritionist_patientassignment WHERE nutritionist_id = u.id) as assigned_patients_count,
                        (SELECT COUNT(*) FROM appointments_appointment WHERE nutritionist_id = u.id) as total_appointments_count
                    FROM nutritionist_nutritionistprofile np
                    JOIN user_user u ON np.user_id = u.id
                    LEFT JOIN "userProfile_userprofile" hp ON u.id = hp.user_id
                    WHERE {where_sql}
                    ORDER BY np.is_verified ASC, np.created_at DESC
                    LIMIT %s OFFSET %s;
                """, params + [page_size, offset])

                rows = cursor.fetchall()

            results = []
            for r in rows:
                specs = r[28]
                if isinstance(specs, str):
                    try: specs = json.loads(specs)
                    except: specs = [specs] if specs else []
                langs = r[29]
                if isinstance(langs, str):
                    try: langs = json.loads(langs)
                    except: langs = [langs] if langs else []

                results.append({
                    "id": r[0],
                    "user_id": r[1],
                    "full_name": r[2] or f"User #{r[1]}",
                    "email": r[3] or "",
                    "phone_number": r[4] or "",
                    "role": r[5] or "nutritionist",
                    "is_active": bool(r[6]),
                    "date_joined": r[7].isoformat() if r[7] else None,
                    "is_verified": bool(r[8]),
                    "verified_at": r[9].isoformat() if r[9] else None,
                    "nutritionist_type": r[10] or "inhouse",
                    "years_of_experience": r[11],
                    "qualification": r[12] or "",
                    "current_organization": r[13] or "",
                    "professional_title": r[14] or "",
                    "professional_bio": r[15] or "",
                    "online_price": float(r[16]) if r[16] else 0.0,
                    "offline_price": float(r[17]) if r[17] else 0.0,
                    "pending_online_price": float(r[18]) if r[18] else None,
                    "pending_offline_price": float(r[19]) if r[19] else None,
                    "price_approval_status": r[20] or "approved",
                    "price_rejection_reason": r[21] or "",
                    "government_id": r[22] or "",
                    "qualification_certificate": r[23] or "",
                    "registration_certificate": r[24] or "",
                    "experience_certificate": r[25] or "",
                    "documents": {
                        "government_id": r[22] or "",
                        "qualification_certificate": r[23] or "",
                        "registration_certificate": r[24] or "",
                        "experience_certificate": r[25] or "",
                    },
                    "registration_number": r[26] or "",
                    "issuing_authority": r[27] or "",
                    "specializations": specs or [],
                    "languages_spoken": langs or [],
                    "created_at": r[30].isoformat() if r[30] else None,
                    "updated_at": r[31].isoformat() if r[31] else None,
                    "is_online_available": bool(r[32]),
                    "is_offline_available": bool(r[33]),
                    "offline_location": r[34] or "",
                    "offline_payment_required": bool(r[35]),
                    "is_virtual_enabled": bool(r[36]),
                    "additional_certifications": r[37] or "",
                    "profile_photo": r[38] or "",
                    "city": r[39] or "",
                    "country": r[40] or "",
                    "assigned_patients_count": r[41] or 0,
                    "total_appointments_count": r[42] or 0,
                })

            total_pages = max(1, (total_filtered + page_size - 1) // page_size)
            return Response({
                "status": "success",
                "metrics": metrics,
                "total": total_filtered,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "results": results
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ApprovalActionAPI(APIView):
    """
    Execute approval/verification action on a nutritionist or user profile.
    Actions supported:
    - 'verify': Approve nutritionist verification
    - 'unverify': Revoke nutritionist verification
    - 'approve_price': Accept pending online/offline rates
    - 'reject_price': Decline pending rates with a reason
    - 'toggle_active': Activate or deactivate user account
    Pure raw SQL.
    """
    def patch(self, request, pk):
        try:
            action = request.data.get("action", "").strip().lower()
            rejection_reason = request.data.get("reason", "").strip()
            now_utc = datetime.now(timezone.utc)

            with connection.cursor() as cursor:
                if action == "verify":
                    cursor.execute("""
                        UPDATE nutritionist_nutritionistprofile
                        SET is_verified = true, verified_at = %s
                        WHERE id = %s
                        RETURNING user_id;
                    """, [now_utc, pk])
                    row = cursor.fetchone()
                    if not row:
                        return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
                    user_id = row[0]
                    cursor.execute("UPDATE user_user SET is_nutritionist_approved = true WHERE id = %s;", [user_id])
                    return Response({"status": "success", "message": "Nutritionist verified successfully", "id": pk})

                elif action == "unverify":
                    cursor.execute("""
                        UPDATE nutritionist_nutritionistprofile
                        SET is_verified = false, verified_at = NULL
                        WHERE id = %s
                        RETURNING user_id;
                    """, [pk])
                    row = cursor.fetchone()
                    if not row:
                        return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
                    user_id = row[0]
                    cursor.execute("UPDATE user_user SET is_nutritionist_approved = false WHERE id = %s;", [user_id])
                    return Response({"status": "success", "message": "Verification status revoked", "id": pk})

                elif action == "approve_price":
                    cursor.execute("""
                        UPDATE nutritionist_nutritionistprofile
                        SET online_price = COALESCE(pending_online_price, online_price),
                            offline_price = COALESCE(pending_offline_price, offline_price),
                            pending_online_price = NULL,
                            pending_offline_price = NULL,
                            price_approval_status = 'approved',
                            price_rejection_reason = NULL
                        WHERE id = %s
                        RETURNING id;
                    """, [pk])
                    return Response({"status": "success", "message": "Pricing approved successfully", "id": pk})

                elif action == "reject_price":
                    cursor.execute("""
                        UPDATE nutritionist_nutritionistprofile
                        SET pending_online_price = NULL,
                            pending_offline_price = NULL,
                            price_approval_status = 'rejected',
                            price_rejection_reason = %s
                        WHERE id = %s
                        RETURNING id;
                    """, [rejection_reason, pk])
                    return Response({"status": "success", "message": "Pricing changes rejected", "id": pk})

                elif action == "toggle_active":
                    is_active = bool(request.data.get("is_active", True))
                    cursor.execute("""
                        UPDATE user_user
                        SET is_active = %s
                        WHERE id = (SELECT user_id FROM nutritionist_nutritionistprofile WHERE id = %s)
                        RETURNING id;
                    """, [is_active, pk])
                    return Response({"status": "success", "message": f"Account status updated to {'Active' if is_active else 'Inactive'}", "id": pk})

                else:
                    return Response({"error": f"Invalid action: '{action}'"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

