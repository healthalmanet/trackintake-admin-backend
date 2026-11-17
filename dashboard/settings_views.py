from decimal import Decimal
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class InhousePricingSettingsAPI(APIView):
    """
    Administrative API to view and manage globally fixed In-House Consultation Rates.
    - Pure parameterized raw SQL (Zero ORM/DDL models)
    - Updates nutritionist_inhousepricingconfig
    - Bulk enforces standard online_price and offline_price on all in-house nutritionists
    """

    def get(self, request):
        try:
            search = request.query_params.get("search", "").strip().lower()

            with connection.cursor() as cursor:
                # 1. Fetch or initialize global inhouse pricing config
                cursor.execute("""
                    SELECT id, title, online_price, offline_price, auto_apply_to_all, updated_at
                    FROM nutritionist_inhousepricingconfig
                    ORDER BY id ASC
                    LIMIT 1;
                """)
                cfg_row = cursor.fetchone()

                if not cfg_row:
                    cursor.execute("""
                        INSERT INTO nutritionist_inhousepricingconfig 
                            (id, title, online_price, offline_price, auto_apply_to_all, updated_at)
                        VALUES 
                            (1, 'Platform In-House Consultation Rates', 499.00, 499.00, true, NOW())
                        ON CONFLICT (id) DO NOTHING;
                    """)
                    cursor.execute("""
                        SELECT id, title, online_price, offline_price, auto_apply_to_all, updated_at
                        FROM nutritionist_inhousepricingconfig
                        WHERE id = 1;
                    """)
                    cfg_row = cursor.fetchone()

                config = {
                    "id": cfg_row[0],
                    "title": cfg_row[1] or "Platform In-House Consultation Rates",
                    "online_price": float(cfg_row[2]) if cfg_row[2] is not None else 499.0,
                    "offline_price": float(cfg_row[3]) if cfg_row[3] is not None else 499.0,
                    "auto_apply_to_all": bool(cfg_row[4]),
                    "updated_at": cfg_row[5].isoformat() if cfg_row[5] else None,
                }

                # 2. Executive Metrics & Alignment Analysis
                cursor.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE LOWER(nutritionist_type) = 'inhouse') as total_inhouse,
                        COUNT(*) FILTER (WHERE LOWER(nutritionist_type) = 'expert') as total_experts,
                        COUNT(*) FILTER (WHERE LOWER(nutritionist_type) = 'inhouse' AND online_price = %s) as matching_online,
                        COUNT(*) FILTER (WHERE LOWER(nutritionist_type) = 'inhouse' AND offline_price = %s) as matching_offline,
                        COUNT(*) FILTER (WHERE LOWER(nutritionist_type) = 'inhouse' AND online_price = %s AND offline_price = %s) as fully_compliant
                    FROM nutritionist_nutritionistprofile;
                """, [config["online_price"], config["offline_price"], config["online_price"], config["offline_price"]])
                m = cursor.fetchone()

                total_inhouse = m[0] or 0
                total_experts = m[1] or 0
                matching_online = m[2] or 0
                matching_offline = m[3] or 0
                fully_compliant = m[4] or 0
                compliance_pct = round((fully_compliant / total_inhouse * 100), 1) if total_inhouse > 0 else 100.0

                metrics = {
                    "total_inhouse": total_inhouse,
                    "total_experts": total_experts,
                    "matching_online": matching_online,
                    "matching_offline": matching_offline,
                    "fully_compliant": fully_compliant,
                    "non_compliant": total_inhouse - fully_compliant,
                    "compliance_percentage": compliance_pct,
                }

                # 3. List of In-House Practitioners
                query = """
                    SELECT 
                        np.id, np.user_id, u.full_name, u.email, u.phone_number,
                        COALESCE(np.qualification, '') as qualification,
                        COALESCE(np.current_organization, '') as current_organization,
                        COALESCE(np.online_price, 0) as online_price,
                        COALESCE(np.offline_price, 0) as offline_price,
                        COALESCE(np.is_verified, false) as is_verified,
                        COALESCE(np.is_online_available, true) as is_online_available,
                        COALESCE(np.is_offline_available, true) as is_offline_available,
                        np.updated_at
                    FROM nutritionist_nutritionistprofile np
                    JOIN user_user u ON np.user_id = u.id
                    WHERE LOWER(np.nutritionist_type) = 'inhouse'
                """
                params = []
                if search:
                    query += " AND (LOWER(u.full_name) LIKE %s OR LOWER(u.email) LIKE %s OR LOWER(COALESCE(np.current_organization, '')) LIKE %s)"
                    term = f"%{search}%"
                    params.extend([term, term, term])

                query += " ORDER BY u.full_name ASC;"
                cursor.execute(query, params)
                rows = cursor.fetchall()

                practitioners = []
                for r in rows:
                    online = float(r[7])
                    offline = float(r[8])
                    is_aligned = (online == config["online_price"] and offline == config["offline_price"])
                    practitioners.append({
                        "id": r[0],
                        "user_id": r[1],
                        "full_name": r[2] or "Unnamed Practitioner",
                        "email": r[3] or "",
                        "phone_number": r[4] or "",
                        "qualification": r[5],
                        "current_organization": r[6],
                        "online_price": online,
                        "offline_price": offline,
                        "is_verified": bool(r[9]),
                        "is_online_available": bool(r[10]),
                        "is_offline_available": bool(r[11]),
                        "updated_at": r[12].isoformat() if r[12] else None,
                        "is_compliant": is_aligned,
                    })

                return Response({
                    "status": "success",
                    "config": config,
                    "metrics": metrics,
                    "practitioners": practitioners,
                    "total_count": len(practitioners),
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        return self._save_settings(request)

    def put(self, request):
        return self._save_settings(request)

    def patch(self, request):
        return self._save_settings(request)

    def _save_settings(self, request):
        try:
            raw_online = request.data.get("online_price")
            raw_offline = request.data.get("offline_price")
            auto_apply = request.data.get("auto_apply_to_all", True)
            apply_to_existing = request.data.get("apply_to_existing", True)

            if raw_online is None or raw_offline is None:
                return Response({
                    "status": "error",
                    "message": "Both online_price and offline_price are required."
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                online_price = Decimal(str(raw_online))
                offline_price = Decimal(str(raw_offline))
            except Exception:
                return Response({
                    "status": "error",
                    "message": "Consultation prices must be valid numeric values."
                }, status=status.HTTP_400_BAD_REQUEST)

            if online_price < 0 or offline_price < 0:
                return Response({
                    "status": "error",
                    "message": "Prices cannot be negative."
                }, status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                # 1. Update or Insert Config Record (id=1)
                cursor.execute("""
                    INSERT INTO nutritionist_inhousepricingconfig 
                        (id, title, online_price, offline_price, auto_apply_to_all, updated_at)
                    VALUES 
                        (1, 'Platform In-House Consultation Rates', %s, %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        online_price = EXCLUDED.online_price,
                        offline_price = EXCLUDED.offline_price,
                        auto_apply_to_all = EXCLUDED.auto_apply_to_all,
                        updated_at = NOW();
                """, [online_price, offline_price, bool(auto_apply)])

                affected_count = 0
                if apply_to_existing:
                    # 2. Bulk update all in-house nutritionists
                    cursor.execute("""
                        UPDATE nutritionist_nutritionistprofile
                        SET online_price = %s,
                            offline_price = %s,
                            updated_at = NOW()
                        WHERE LOWER(nutritionist_type) = 'inhouse';
                    """, [online_price, offline_price])
                    affected_count = cursor.rowcount

            return Response({
                "status": "success",
                "message": f"Global in-house consultation pricing updated successfully. Applied to {affected_count} in-house clinicians.",
                "data": {
                    "online_price": float(online_price),
                    "offline_price": float(offline_price),
                    "auto_apply_to_all": bool(auto_apply),
                    "affected_practitioners_count": affected_count,
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

