from decimal import Decimal
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


def _ensure_expert_pricing_columns(cursor):
    cursor.execute("""
        ALTER TABLE nutritionist_inhousepricingconfig
        ADD COLUMN IF NOT EXISTS expert_fixed_pricing_enabled BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS expert_online_price NUMERIC(10, 2) DEFAULT 999.00,
        ADD COLUMN IF NOT EXISTS expert_offline_price NUMERIC(10, 2) DEFAULT 999.00;
    """)


class InhousePricingSettingsAPI(APIView):
    """
    Administrative API to view and manage globally fixed In-House Consultation Rates,
    Expert Fixed/Variable Consultation Policy, Platform Commissions, and individual overrides.
    - Pure parameterized raw SQL (Zero ORM/DDL models)
    """

    def get(self, request):
        try:
            search = request.query_params.get("search", "").strip().lower()

            with connection.cursor() as cursor:
                _ensure_expert_pricing_columns(cursor)

                # 1. Fetch or initialize global pricing config
                cursor.execute("""
                    SELECT id, title, online_price, offline_price, auto_apply_to_all, updated_at,
                           COALESCE(platform_commission_percent, 5.00) as platform_commission_percent,
                           COALESCE(expert_commission_percent, 5.00) as expert_commission_percent,
                           COALESCE(expert_fixed_pricing_enabled, false) as expert_fixed_pricing_enabled,
                           COALESCE(expert_online_price, 999.00) as expert_online_price,
                           COALESCE(expert_offline_price, 999.00) as expert_offline_price
                    FROM nutritionist_inhousepricingconfig
                    ORDER BY id ASC
                    LIMIT 1;
                """)
                cfg_row = cursor.fetchone()

                if not cfg_row:
                    cursor.execute("""
                        INSERT INTO nutritionist_inhousepricingconfig 
                            (id, title, online_price, offline_price, auto_apply_to_all, platform_commission_percent, expert_commission_percent, expert_fixed_pricing_enabled, expert_online_price, expert_offline_price, updated_at)
                        VALUES 
                            (1, 'Platform Consultation Rates & Commission', 499.00, 499.00, true, 5.00, 5.00, false, 999.00, 999.00, NOW())
                        ON CONFLICT (id) DO NOTHING;
                    """)
                    cursor.execute("""
                        SELECT id, title, online_price, offline_price, auto_apply_to_all, updated_at,
                               COALESCE(platform_commission_percent, 5.00) as platform_commission_percent,
                               COALESCE(expert_commission_percent, 5.00) as expert_commission_percent,
                               COALESCE(expert_fixed_pricing_enabled, false) as expert_fixed_pricing_enabled,
                               COALESCE(expert_online_price, 999.00) as expert_online_price,
                               COALESCE(expert_offline_price, 999.00) as expert_offline_price
                        FROM nutritionist_inhousepricingconfig
                        WHERE id = 1;
                    """)
                    cfg_row = cursor.fetchone()

                config = {
                    "id": cfg_row[0],
                    "title": cfg_row[1] or "Platform Consultation Rates & Commission",
                    "online_price": float(cfg_row[2]) if cfg_row[2] is not None else 499.0,
                    "offline_price": float(cfg_row[3]) if cfg_row[3] is not None else 499.0,
                    "auto_apply_to_all": bool(cfg_row[4]),
                    "updated_at": cfg_row[5].isoformat() if cfg_row[5] else None,
                    "platform_commission_percent": float(cfg_row[6]) if len(cfg_row) > 6 and cfg_row[6] is not None else 5.0,
                    "expert_commission_percent": float(cfg_row[7]) if len(cfg_row) > 7 and cfg_row[7] is not None else 5.0,
                    "expert_fixed_pricing_enabled": bool(cfg_row[8]) if len(cfg_row) > 8 and cfg_row[8] is not None else False,
                    "expert_online_price": float(cfg_row[9]) if len(cfg_row) > 9 and cfg_row[9] is not None else 999.0,
                    "expert_offline_price": float(cfg_row[10]) if len(cfg_row) > 10 and cfg_row[10] is not None else 999.0,
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

                # 3. List of Practitioners (Both In-House and Expert)
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
                        np.updated_at,
                        LOWER(COALESCE(np.nutritionist_type, 'inhouse')) as nutritionist_type,
                        np.custom_commission_percent
                    FROM nutritionist_nutritionistprofile np
                    JOIN user_user u ON np.user_id = u.id
                    WHERE 1=1
                """
                params = []
                if search:
                    query += " AND (LOWER(u.full_name) LIKE %s OR LOWER(u.email) LIKE %s OR LOWER(COALESCE(np.current_organization, '')) LIKE %s)"
                    term = f"%{search}%"
                    params.extend([term, term, term])

                query += " ORDER BY u.full_name ASC;"
                cursor.execute(query, params)
                rows = cursor.fetchall()

                inhouse_practitioners = []
                expert_practitioners = []

                for r in rows:
                    online = float(r[7])
                    offline = float(r[8])
                    nutri_type = r[13]
                    custom_comm = float(r[14]) if r[14] is not None else None

                    if custom_comm is not None:
                        effective_comm = custom_comm
                        has_custom_comm = True
                    else:
                        effective_comm = config["expert_commission_percent"] if nutri_type == "expert" else config["platform_commission_percent"]
                        has_custom_comm = False

                    if nutri_type == "inhouse":
                        is_aligned = (online == config["online_price"] and offline == config["offline_price"])
                    elif config["expert_fixed_pricing_enabled"]:
                        is_aligned = (online == config["expert_online_price"] and offline == config["expert_offline_price"])
                    else:
                        is_aligned = True

                    item = {
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
                        "nutritionist_type": nutri_type,
                        "custom_commission_percent": custom_comm,
                        "effective_commission_percent": effective_comm,
                        "has_custom_commission": has_custom_comm,
                        "is_compliant": is_aligned,
                    }

                    if nutri_type == "expert":
                        expert_practitioners.append(item)
                    else:
                        inhouse_practitioners.append(item)

                return Response({
                    "status": "success",
                    "config": config,
                    "metrics": metrics,
                    "practitioners": inhouse_practitioners + expert_practitioners,
                    "inhouse_practitioners": inhouse_practitioners,
                    "expert_practitioners": expert_practitioners,
                    "total_count": len(rows),
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
            raw_commission = request.data.get("platform_commission_percent", 5.0)
            raw_expert_commission = request.data.get("expert_commission_percent", 5.0)
            auto_apply = request.data.get("auto_apply_to_all", True)
            apply_to_existing = request.data.get("apply_to_existing", True)

            expert_fixed_pricing_enabled = bool(request.data.get("expert_fixed_pricing_enabled", False))
            raw_expert_online = request.data.get("expert_online_price", 999.0)
            raw_expert_offline = request.data.get("expert_offline_price", 999.0)
            apply_expert_to_existing = bool(request.data.get("apply_expert_to_existing", False))

            if raw_online is None or raw_offline is None:
                return Response({
                    "status": "error",
                    "message": "Both online_price and offline_price are required."
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                online_price = Decimal(str(raw_online))
                offline_price = Decimal(str(raw_offline))
                commission_percent = Decimal(str(raw_commission if raw_commission is not None else 5.0))
                expert_commission_percent = Decimal(str(raw_expert_commission if raw_expert_commission is not None else 5.0))
                expert_online_price = Decimal(str(raw_expert_online if raw_expert_online is not None else 999.0))
                expert_offline_price = Decimal(str(raw_expert_offline if raw_expert_offline is not None else 999.0))
            except Exception:
                return Response({
                    "status": "error",
                    "message": "Consultation prices and commission percentages must be valid numeric values."
                }, status=status.HTTP_400_BAD_REQUEST)

            if online_price < 0 or offline_price < 0 or expert_online_price < 0 or expert_offline_price < 0:
                return Response({
                    "status": "error",
                    "message": "Prices cannot be negative."
                }, status=status.HTTP_400_BAD_REQUEST)

            if commission_percent < 0 or commission_percent > 100 or expert_commission_percent < 0 or expert_commission_percent > 100:
                return Response({
                    "status": "error",
                    "message": "Commission percentages must be between 0% and 100%."
                }, status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                _ensure_expert_pricing_columns(cursor)

                # 1. Update or Insert Config Record (id=1)
                cursor.execute("""
                    INSERT INTO nutritionist_inhousepricingconfig 
                        (id, title, online_price, offline_price, auto_apply_to_all, platform_commission_percent, expert_commission_percent, expert_fixed_pricing_enabled, expert_online_price, expert_offline_price, updated_at)
                    VALUES 
                        (1, 'Platform Consultation Rates & Commission', %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        online_price = EXCLUDED.online_price,
                        offline_price = EXCLUDED.offline_price,
                        auto_apply_to_all = EXCLUDED.auto_apply_to_all,
                        platform_commission_percent = EXCLUDED.platform_commission_percent,
                        expert_commission_percent = EXCLUDED.expert_commission_percent,
                        expert_fixed_pricing_enabled = EXCLUDED.expert_fixed_pricing_enabled,
                        expert_online_price = EXCLUDED.expert_online_price,
                        expert_offline_price = EXCLUDED.expert_offline_price,
                        updated_at = NOW();
                """, [
                    online_price, offline_price, bool(auto_apply),
                    commission_percent, expert_commission_percent,
                    expert_fixed_pricing_enabled, expert_online_price, expert_offline_price
                ])

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

                affected_experts_count = 0
                if expert_fixed_pricing_enabled and apply_expert_to_existing:
                    # 3. Bulk update all expert nutritionists when fixed pricing is enforced
                    cursor.execute("""
                        UPDATE nutritionist_nutritionistprofile
                        SET online_price = %s,
                            offline_price = %s,
                            updated_at = NOW()
                        WHERE LOWER(nutritionist_type) = 'expert';
                    """, [expert_online_price, expert_offline_price])
                    affected_experts_count = cursor.rowcount

            msg_parts = [f"Platform pricing & commissions saved (In-House: {commission_percent}%, Expert: {expert_commission_percent}%)."]
            if affected_count:
                msg_parts.append(f"Applied standard rates to {affected_count} in-house clinicians.")
            if expert_fixed_pricing_enabled:
                msg_parts.append(f"Expert fixed pricing enforced (Online: ₹{expert_online_price}, In-Clinic: ₹{expert_offline_price}).")
                if affected_experts_count:
                    msg_parts.append(f"Synced {affected_experts_count} expert specialists.")
            else:
                msg_parts.append("Expert pricing is set to variable (nutritionist-controlled).")

            return Response({
                "status": "success",
                "message": " ".join(msg_parts),
                "data": {
                    "online_price": float(online_price),
                    "offline_price": float(offline_price),
                    "platform_commission_percent": float(commission_percent),
                    "expert_commission_percent": float(expert_commission_percent),
                    "auto_apply_to_all": bool(auto_apply),
                    "expert_fixed_pricing_enabled": expert_fixed_pricing_enabled,
                    "expert_online_price": float(expert_online_price),
                    "expert_offline_price": float(expert_offline_price),
                    "affected_practitioners_count": affected_count,
                    "affected_experts_count": affected_experts_count,
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PractitionerPricingUpdateAPI(APIView):
    """
    Update appointment pricing and custom commission rate for an individual nutritionist (In-House or Expert).
    """

    def patch(self, request, pk):
        return self._update(request, pk)

    def put(self, request, pk):
        return self._update(request, pk)

    def _update(self, request, pk):
        try:
            data = request.data
            online_price = data.get("online_price")
            offline_price = data.get("offline_price")
            custom_commission = data.get("custom_commission_percent")
            use_default_commission = data.get("use_default_commission", False)

            with connection.cursor() as cursor:
                # Find by profile id or user_id
                cursor.execute("""
                    SELECT np.id, np.nutritionist_type, u.full_name
                    FROM nutritionist_nutritionistprofile np
                    JOIN user_user u ON np.user_id = u.id
                    WHERE np.id = %s OR np.user_id = %s;
                """, [pk, pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Nutritionist profile not found."}, status=status.HTTP_404_NOT_FOUND)

                profile_id = row[0]
                practitioner_name = row[2]

                updates = []
                params = []

                if online_price is not None:
                    p_on = Decimal(str(online_price))
                    if p_on < 0:
                        return Response({"status": "error", "message": "Online price cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
                    updates.append("online_price = %s")
                    params.append(p_on)

                if offline_price is not None:
                    p_off = Decimal(str(offline_price))
                    if p_off < 0:
                        return Response({"status": "error", "message": "Offline price cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
                    updates.append("offline_price = %s")
                    params.append(p_off)

                if use_default_commission:
                    updates.append("custom_commission_percent = NULL")
                elif custom_commission is not None and str(custom_commission).strip() != "":
                    c_val = Decimal(str(custom_commission))
                    if c_val < 0 or c_val > 100:
                        return Response({"status": "error", "message": "Commission percentage must be between 0% and 100%."}, status=status.HTTP_400_BAD_REQUEST)
                    updates.append("custom_commission_percent = %s")
                    params.append(c_val)

                if updates:
                    updates.append("updated_at = NOW()")
                    sql = f"UPDATE nutritionist_nutritionistprofile SET {', '.join(updates)} WHERE id = %s;"
                    params.append(profile_id)
                    cursor.execute(sql, params)

            return Response({
                "status": "success",
                "message": f"Successfully updated consultation pricing and commission for {practitioner_name}.",
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
