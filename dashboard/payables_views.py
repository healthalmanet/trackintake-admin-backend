import json
from datetime import datetime, timezone
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class PayablesListAPI(APIView):
    """
    List appointment payables (nutritionist payouts) and patient refunds
    with search, filters, pagination, and executive metrics.
    Pure parameterized raw SQL - Zero models.
    """
    def get(self, request):
        try:
            view_type = request.query_params.get("type", "all").strip().lower()  # all, payouts, refunds
            status_filter = request.query_params.get("status", "all").strip().upper()
            search = request.query_params.get("search", "").strip()
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = max(1, min(100, int(request.query_params.get("page_size", 15))))
            offset = (page - 1) * page_size

            with connection.cursor() as cursor:
                # 1. Executive Metrics
                cursor.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE payout_status = 'PENDING' OR (payment_status = 'PAID' AND (payout_status IS NULL OR payout_status = 'PENDING'))) as pending_payouts_count,
                        COALESCE(SUM(payout_amount) FILTER (WHERE payout_status = 'PENDING' OR (payment_status = 'PAID' AND (payout_status IS NULL OR payout_status = 'PENDING'))), 0) as pending_payouts_total,
                        COUNT(*) FILTER (WHERE payout_status = 'PAID') as paid_payouts_count,
                        COALESCE(SUM(payout_amount) FILTER (WHERE payout_status = 'PAID'), 0) as paid_payouts_total,
                        COUNT(*) FILTER (WHERE payment_status = 'PENDING_REFUND') as pending_refunds_count,
                        COALESCE(SUM(refund_amount) FILTER (WHERE payment_status = 'PENDING_REFUND'), 0) as pending_refunds_total,
                        COUNT(*) FILTER (WHERE payment_status = 'REFUNDED') as refunded_count,
                        COALESCE(SUM(refund_amount) FILTER (WHERE payment_status = 'REFUNDED'), 0) as refunded_total,
                        COUNT(*) as total_records
                    FROM appointments_appointment;
                """)
                m = cursor.fetchone()
                metrics = {
                    "pending_payouts_count": m[0] or 0,
                    "pending_payouts_total": float(m[1] or 0),
                    "paid_payouts_count": m[2] or 0,
                    "paid_payouts_total": float(m[3] or 0),
                    "pending_refunds_count": m[4] or 0,
                    "pending_refunds_total": float(m[5] or 0),
                    "refunded_count": m[6] or 0,
                    "refunded_total": float(m[7] or 0),
                    "total_records": m[8] or 0,
                }

                # 2. Build Filtered Query
                where_clauses = ["1=1"]
                params = []

                if view_type == "payouts":
                    where_clauses.append("(a.payout_amount > 0 OR a.payment_status = 'PAID')")
                elif view_type == "refunds":
                    where_clauses.append("(a.refund_amount > 0 OR a.payment_status IN ('PENDING_REFUND', 'REFUNDED') OR a.status = 'CANCELLED')")

                if status_filter != "ALL":
                    if status_filter in ["PAID", "PENDING", "CANCELLED", "HOLD"]:
                        where_clauses.append("UPPER(COALESCE(a.payout_status, 'PENDING')) = %s")
                        params.append(status_filter)
                    elif status_filter in ["PENDING_REFUND", "REFUNDED"]:
                        where_clauses.append("UPPER(a.payment_status) = %s")
                        params.append(status_filter)

                if search:
                    where_clauses.append("""
                        (p.full_name ILIKE %s OR p.email ILIKE %s OR 
                         n.full_name ILIKE %s OR n.email ILIKE %s OR 
                         CAST(a.id AS TEXT) ILIKE %s OR 
                         COALESCE(a.payout_transaction_ref, '') ILIKE %s)
                    """)
                    s = f"%{search}%"
                    params.extend([s, s, s, s, s, s])

                where_sql = " AND ".join(where_clauses)

                # Total count for pagination
                cursor.execute(f"""
                    SELECT COUNT(*)
                    FROM appointments_appointment a
                    LEFT JOIN user_user p ON a.patient_id = p.id
                    LEFT JOIN user_user n ON a.nutritionist_id = n.id
                    WHERE {where_sql};
                """, params)
                total_filtered = cursor.fetchone()[0]

                # Data query
                cursor.execute(f"""
                    SELECT 
                        a.id, a.slot_date, a.slot_start_time, a.appointment_category, a.appointment_type,
                        a.status, COALESCE(a.fee_amount, 0), a.payment_status,
                        COALESCE(a.payout_status, 'PENDING') as payout_status,
                        COALESCE(a.payout_amount, 0), a.payout_transaction_ref, a.payout_marked_at,
                        COALESCE(a.refund_amount, 0), a.refund_notes, a.refunded_at,
                        a.cancelled_by, a.cancellation_reason, a.created_at,
                        p.id as patient_id, COALESCE(p.full_name, 'Patient') as patient_name,
                        COALESCE(p.email, '') as patient_email, COALESCE(p.phone_number, '') as patient_phone,
                        n.id as nutri_id, COALESCE(n.full_name, 'Nutritionist') as nutri_name,
                        COALESCE(n.email, '') as nutri_email, COALESCE(n.phone_number, '') as nutri_phone
                    FROM appointments_appointment a
                    LEFT JOIN user_user p ON a.patient_id = p.id
                    LEFT JOIN user_user n ON a.nutritionist_id = n.id
                    WHERE {where_sql}
                    ORDER BY a.created_at DESC
                    LIMIT %s OFFSET %s;
                """, params + [page_size, offset])

                rows = cursor.fetchall()

            results = []
            for r in rows:
                results.append({
                    "id": r[0],
                    "slot_date": str(r[1]) if r[1] else None,
                    "slot_start_time": str(r[2]) if r[2] else None,
                    "appointment_category": r[3] or "IN_HOUSE",
                    "appointment_type": r[4] or "VIRTUAL",
                    "status": r[5] or "CONFIRMED",
                    "fee_amount": float(r[6]),
                    "payment_status": r[7] or "UNPAID",
                    "payout_status": r[8],
                    "payout_amount": float(r[9]),
                    "payout_transaction_ref": r[10] or "",
                    "payout_marked_at": r[11].isoformat() if r[11] else None,
                    "refund_amount": float(r[12]),
                    "refund_notes": r[13] or "",
                    "refunded_at": r[14].isoformat() if r[14] else None,
                    "cancelled_by": r[15],
                    "cancellation_reason": r[16],
                    "created_at": r[17].isoformat() if r[17] else None,
                    "patient": {
                        "id": r[18],
                        "name": r[19],
                        "email": r[20],
                        "phone": r[21],
                    },
                    "nutritionist": {
                        "id": r[22],
                        "name": r[23],
                        "email": r[24],
                        "phone": r[25],
                    }
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


class PayableDetailUpdateAPI(APIView):
    """
    Update payout or refund status for an appointment.
    Pure raw SQL.
    """
    def patch(self, request, pk):
        try:
            data = request.data
            now_utc = datetime.now(timezone.utc)
            updates = []
            params = []

            # Payout updates
            if "payout_status" in data:
                p_status = str(data["payout_status"]).strip().upper()
                updates.append("payout_status = %s")
                params.append(p_status)
                if p_status == "PAID":
                    updates.append("payout_marked_at = %s")
                    params.append(now_utc)

            if "payout_amount" in data:
                updates.append("payout_amount = %s")
                params.append(float(data["payout_amount"]))

            if "payout_transaction_ref" in data:
                updates.append("payout_transaction_ref = %s")
                params.append(str(data["payout_transaction_ref"]).strip())

            # Refund updates
            if "payment_status" in data:
                pay_status = str(data["payment_status"]).strip().upper()
                updates.append("payment_status = %s")
                params.append(pay_status)
                if pay_status == "REFUNDED":
                    updates.append("refunded_at = %s")
                    params.append(now_utc)

            if "refund_amount" in data:
                updates.append("refund_amount = %s")
                params.append(float(data["refund_amount"]))

            if "refund_notes" in data:
                updates.append("refund_notes = %s")
                params.append(str(data["refund_notes"]).strip())

            if not updates:
                return Response({"error": "No valid fields provided for update"}, status=status.HTTP_400_BAD_REQUEST)

            params.append(pk)
            query = f"UPDATE appointments_appointment SET {', '.join(updates)} WHERE id = %s RETURNING id;"

            with connection.cursor() as cursor:
                cursor.execute(query, params)
                row = cursor.fetchone()

            if not row:
                return Response({"error": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({
                "status": "success",
                "message": "Financial status updated successfully",
                "id": pk
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

