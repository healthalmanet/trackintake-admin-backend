from datetime import datetime, timezone
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class PatientAssignmentListAPI(APIView):
    """
    Administrative API to view and manage patient assignments to nutritionists.
    - Pure parameterized raw SQL (Zero ORM models)
    - Returns metrics, active nutritionists with current caseload counts,
      assigned patients list, and unassigned patients list.
    """

    def get(self, request):
        try:
            search = request.query_params.get("search", "").strip().lower()
            nutritionist_filter = request.query_params.get("nutritionist_id", "").strip()
            plan_filter = request.query_params.get("plan", "").strip().lower()
            tab = request.query_params.get("tab", "all").strip().lower()  # all, assigned, unassigned
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = max(1, min(100, int(request.query_params.get("page_size", 15))))
            offset = (page - 1) * page_size

            with connection.cursor() as cursor:
                # 1. Executive Metrics
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT u.id) as total_patients,
                        COUNT(DISTINCT pa.patient_id) as assigned_patients,
                        (SELECT COUNT(*) FROM user_user WHERE LOWER(role) = 'nutritionist') as total_nutritionists
                    FROM user_user u
                    LEFT JOIN nutritionist_patientassignment pa ON u.id = pa.patient_id
                    WHERE LOWER(u.role) NOT IN ('nutritionist', 'admin', 'owner');
                """)
                m = cursor.fetchone()
                total_patients = m[0] or 0
                assigned_patients = m[1] or 0
                unassigned_patients = max(0, total_patients - assigned_patients)
                total_nutritionists = m[2] or 0
                avg_caseload = round((assigned_patients / total_nutritionists), 1) if total_nutritionists > 0 else 0

                metrics = {
                    "total_patients": total_patients,
                    "assigned_patients": assigned_patients,
                    "unassigned_patients": unassigned_patients,
                    "total_nutritionists": total_nutritionists,
                    "avg_caseload": avg_caseload,
                }

                # 2. Nutritionists List with current Caseload
                cursor.execute("""
                    SELECT 
                        u.id, u.full_name, u.email, u.phone_number,
                        COALESCE(np.nutritionist_type, 'inhouse') as nutritionist_type,
                        COALESCE(np.qualification, '') as qualification,
                        COALESCE(np.current_organization, '') as current_organization,
                        COALESCE(np.is_verified, false) as is_verified,
                        COALESCE(np.online_price, 0) as online_price,
                        COALESCE(np.offline_price, 0) as offline_price,
                        COUNT(pa.id) as caseload_count
                    FROM user_user u
                    LEFT JOIN nutritionist_nutritionistprofile np ON u.id = np.user_id
                    LEFT JOIN nutritionist_patientassignment pa ON u.id = pa.nutritionist_id
                    WHERE LOWER(u.role) = 'nutritionist'
                    GROUP BY u.id, u.full_name, u.email, u.phone_number, np.nutritionist_type,
                             np.qualification, np.current_organization, np.is_verified,
                             np.online_price, np.offline_price
                    ORDER BY caseload_count DESC, u.full_name ASC;
                """)
                nutri_rows = cursor.fetchall()
                nutritionists = []
                for nr in nutri_rows:
                    nutritionists.append({
                        "id": nr[0],
                        "full_name": nr[1] or "Dr. Practitioner",
                        "email": nr[2] or "",
                        "phone_number": nr[3] or "",
                        "nutritionist_type": nr[4] or "inhouse",
                        "qualification": nr[5],
                        "current_organization": nr[6],
                        "is_verified": bool(nr[7]),
                        "online_price": float(nr[8]),
                        "offline_price": float(nr[9]),
                        "caseload_count": nr[10],
                    })

                # 3. Assigned Patients List (with pagination and search)
                assigned_where = ["LOWER(p.role) NOT IN ('nutritionist', 'admin', 'owner')"]
                assigned_params = []

                if nutritionist_filter:
                    assigned_where.append("pa.nutritionist_id = %s")
                    assigned_params.append(int(nutritionist_filter))

                if plan_filter:
                    assigned_where.append("LOWER(COALESCE(p.plan, 'basic')) = %s")
                    assigned_params.append(plan_filter)

                if search:
                    assigned_where.append("""
                        (LOWER(p.full_name) LIKE %s 
                         OR LOWER(p.email) LIKE %s 
                         OR LOWER(COALESCE(p.phone_number, '')) LIKE %s
                         OR LOWER(n.full_name) LIKE %s)
                    """)
                    term = f"%{search}%"
                    assigned_params.extend([term, term, term, term])

                assigned_where_sql = " AND ".join(assigned_where)

                # Total count for assigned
                cursor.execute(f"""
                    SELECT COUNT(*)
                    FROM nutritionist_patientassignment pa
                    JOIN user_user p ON pa.patient_id = p.id
                    JOIN user_user n ON pa.nutritionist_id = n.id
                    WHERE {assigned_where_sql};
                """, assigned_params)
                total_assigned_filtered = cursor.fetchone()[0] or 0

                # Fetch assigned records
                cursor.execute(f"""
                    SELECT 
                        pa.id as assignment_id, pa.assigned_at,
                        p.id as patient_id, p.full_name as patient_name, p.email as patient_email, p.phone_number as patient_phone,
                        p.plan, p.is_active as patient_is_active, p.date_joined as patient_date_joined,
                        COALESCE(hp.goal, '') as health_goal, COALESCE(hp.city, '') as city, COALESCE(hp.country, '') as country,
                        COALESCE(hp.diet_type, '') as diet_type,
                        n.id as nutritionist_id, n.full_name as nutritionist_name, n.email as nutritionist_email,
                        COALESCE(np.nutritionist_type, 'inhouse') as nutritionist_type,
                        COALESCE(np.current_organization, '') as nutritionist_organization,
                        COALESCE(np.is_verified, false) as nutritionist_is_verified
                    FROM nutritionist_patientassignment pa
                    JOIN user_user p ON pa.patient_id = p.id
                    JOIN user_user n ON pa.nutritionist_id = n.id
                    LEFT JOIN "userProfile_userprofile" hp ON p.id = hp.user_id
                    LEFT JOIN nutritionist_nutritionistprofile np ON n.id = np.user_id
                    WHERE {assigned_where_sql}
                    ORDER BY pa.assigned_at DESC, pa.id DESC
                    LIMIT %s OFFSET %s;
                """, assigned_params + [page_size, offset])
                assigned_rows = cursor.fetchall()

                assigned_list = []
                for r in assigned_rows:
                    assigned_list.append({
                        "assignment_id": r[0],
                        "assigned_at": str(r[1]) if r[1] else None,
                        "patient": {
                            "id": r[2],
                            "full_name": r[3] or "Patient",
                            "email": r[4] or "",
                            "phone_number": r[5] or "",
                            "plan": r[6] or "Basic",
                            "is_active": bool(r[7]),
                            "date_joined": r[8].isoformat() if r[8] else None,
                            "health_goal": r[9],
                            "city": r[10],
                            "country": r[11],
                            "diet_type": r[12],
                        },
                        "nutritionist": {
                            "id": r[13],
                            "full_name": r[14] or "Dr. Practitioner",
                            "email": r[15] or "",
                            "nutritionist_type": r[16],
                            "current_organization": r[17],
                            "is_verified": bool(r[18]),
                        }
                    })

                # 4. Unassigned Patients List
                unassigned_where = [
                    "LOWER(u.role) NOT IN ('nutritionist', 'admin', 'owner')",
                    "pa.id IS NULL"
                ]
                unassigned_params = []
                if search:
                    unassigned_where.append("(LOWER(u.full_name) LIKE %s OR LOWER(u.email) LIKE %s OR LOWER(COALESCE(u.phone_number, '')) LIKE %s)")
                    term = f"%{search}%"
                    unassigned_params.extend([term, term, term])

                unassigned_where_sql = " AND ".join(unassigned_where)

                cursor.execute(f"""
                    SELECT 
                        u.id, u.full_name, u.email, u.phone_number,
                        u.plan, u.is_active, u.date_joined,
                        COALESCE(hp.goal, '') as health_goal, COALESCE(hp.city, '') as city, COALESCE(hp.country, '') as country,
                        COALESCE(hp.diet_type, '') as diet_type
                    FROM user_user u
                    LEFT JOIN nutritionist_patientassignment pa ON u.id = pa.patient_id
                    LEFT JOIN "userProfile_userprofile" hp ON u.id = hp.user_id
                    WHERE {unassigned_where_sql}
                    ORDER BY u.date_joined DESC
                    LIMIT 100;
                """, unassigned_params)
                unassigned_rows = cursor.fetchall()

                unassigned_list = []
                for ur in unassigned_rows:
                    unassigned_list.append({
                        "id": ur[0],
                        "full_name": ur[1] or "Patient",
                        "email": ur[2] or "",
                        "phone_number": ur[3] or "",
                        "plan": ur[4] or "Basic",
                        "is_active": bool(ur[5]),
                        "date_joined": ur[6].isoformat() if ur[6] else None,
                        "health_goal": ur[7],
                        "city": ur[8],
                        "country": ur[9],
                        "diet_type": ur[10],
                    })

                # 5. Full Patient Candidates List (for assignment & transfer pickers)
                cursor.execute("""
                    SELECT 
                        u.id, u.full_name, u.email, u.phone_number,
                        COALESCE(u.plan, 'Basic') as plan, u.is_active,
                        COALESCE(hp.goal, '') as health_goal,
                        COALESCE(hp.diet_type, '') as diet_type,
                        COALESCE(hp.city, '') as city,
                        pa.nutritionist_id,
                        nu.full_name as assigned_nutritionist_name
                    FROM user_user u
                    LEFT JOIN nutritionist_patientassignment pa ON u.id = pa.patient_id
                    LEFT JOIN user_user nu ON pa.nutritionist_id = nu.id
                    LEFT JOIN "userProfile_userprofile" hp ON u.id = hp.user_id
                    WHERE LOWER(u.role) NOT IN ('nutritionist', 'admin', 'owner')
                    ORDER BY u.full_name ASC;
                """)
                candidate_rows = cursor.fetchall()
                all_patients = []
                for cr in candidate_rows:
                    all_patients.append({
                        "id": cr[0],
                        "full_name": cr[1] or "Patient",
                        "email": cr[2] or "",
                        "phone_number": cr[3] or "",
                        "plan": cr[4] or "Basic",
                        "is_active": bool(cr[5]),
                        "health_goal": cr[6] or "General Health",
                        "diet_type": cr[7] or "Standard",
                        "city": cr[8] or "",
                        "assigned_nutritionist_id": cr[9],
                        "assigned_nutritionist_name": cr[10] if cr[9] else None,
                    })

                total_pages = max(1, (total_assigned_filtered + page_size - 1) // page_size)

                return Response({
                    "status": "success",
                    "metrics": metrics,
                    "nutritionists": nutritionists,
                    "assignments": assigned_list,
                    "unassigned": unassigned_list,
                    "all_patients": all_patients,
                    "total_assigned": total_assigned_filtered,
                    "total_unassigned": len(unassigned_list),
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BatchAssignPatientsAPI(APIView):
    """
    Batch assign multiple patients to a designated nutritionist.
    Accepts: { "nutritionist_id": 217, "patient_ids": [101, 102, ...] }
    """

    def post(self, request):
        try:
            nutritionist_id = request.data.get("nutritionist_id")
            patient_ids = request.data.get("patient_ids", [])

            if not nutritionist_id:
                return Response({"status": "error", "message": "nutritionist_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            if not patient_ids or not isinstance(patient_ids, list):
                return Response({"status": "error", "message": "patient_ids must be a non-empty array of patient IDs"}, status=status.HTTP_400_BAD_REQUEST)

            # Clean and sanitize patient_ids
            try:
                patient_ids = [int(p) for p in patient_ids]
            except ValueError:
                return Response({"status": "error", "message": "All patient_ids must be valid integers"}, status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                # 1. Verify nutritionist exists and has role 'nutritionist'
                cursor.execute("""
                    SELECT id, full_name, email 
                    FROM user_user 
                    WHERE id = %s AND LOWER(role) = 'nutritionist';
                """, [nutritionist_id])
                nutri = cursor.fetchone()
                if not nutri:
                    return Response({"status": "error", "message": "Selected nutritionist was not found or is invalid."}, status=status.HTTP_404_NOT_FOUND)

                nutri_name = nutri[1] or "Practitioner"

                # 2. Verify all patients exist
                cursor.execute("""
                    SELECT id FROM user_user WHERE id = ANY(%s);
                """, [patient_ids])
                existing_pids = set(r[0] for r in cursor.fetchall())
                valid_pids = [pid for pid in patient_ids if pid in existing_pids]

                if not valid_pids:
                    return Response({"status": "error", "message": "No valid patient accounts found to assign."}, status=status.HTTP_400_BAD_REQUEST)

                # 3. Batch assign / reassign
                now_date = datetime.now(timezone.utc).date()
                assigned_count = 0

                for pid in valid_pids:
                    cursor.execute("""
                        SELECT id FROM nutritionist_patientassignment WHERE patient_id = %s;
                    """, [pid])
                    existing_assign = cursor.fetchone()

                    if existing_assign:
                        cursor.execute("""
                            UPDATE nutritionist_patientassignment
                            SET nutritionist_id = %s,
                                assigned_at = %s
                            WHERE id = %s;
                        """, [nutritionist_id, now_date, existing_assign[0]])
                    else:
                        cursor.execute("""
                            INSERT INTO nutritionist_patientassignment (patient_id, nutritionist_id, assigned_at)
                            VALUES (%s, %s, %s);
                        """, [pid, nutritionist_id, now_date])

                    assigned_count += 1

                return Response({
                    "status": "success",
                    "message": f"Successfully assigned {assigned_count} patients to {nutri_name}.",
                    "data": {
                        "nutritionist_id": nutritionist_id,
                        "nutritionist_name": nutri_name,
                        "assigned_count": assigned_count,
                        "patient_ids": valid_pids,
                    }
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UnassignPatientAPI(APIView):
    """
    Remove patient assignment.
    Accepts: { "patient_ids": [101, 102] } or { "patient_id": 101 }
    """

    def post(self, request):
        try:
            patient_ids = request.data.get("patient_ids")
            single_pid = request.data.get("patient_id")

            if patient_ids is None and single_pid is not None:
                patient_ids = [single_pid]

            if not patient_ids or not isinstance(patient_ids, list):
                return Response({"status": "error", "message": "patient_ids array is required."}, status=status.HTTP_400_BAD_REQUEST)

            patient_ids = [int(p) for p in patient_ids]

            with connection.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM nutritionist_patientassignment
                    WHERE patient_id = ANY(%s);
                """, [patient_ids])
                deleted_count = cursor.rowcount

            return Response({
                "status": "success",
                "message": f"Unassigned {deleted_count} patients successfully.",
                "deleted_count": deleted_count,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

