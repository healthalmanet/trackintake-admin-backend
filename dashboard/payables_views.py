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
                        COALESCE(n.email, '') as nutri_email, COALESCE(n.phone_number, '') as nutri_phone,
                        COALESCE(a.commission_rate, 5.00) as commission_rate,
                        COALESCE(a.commission_amount, 0.00) as commission_amount
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
                fee = float(r[6])
                payout = float(r[9])
                comm_rate = float(r[26]) if len(r) > 26 and r[26] is not None else 5.0
                comm_amount = float(r[27]) if len(r) > 27 and r[27] is not None else 0.0
                if comm_amount <= 0 and fee > 0 and payout > 0 and fee > payout:
                    comm_amount = round(fee - payout, 2)
                elif comm_amount <= 0 and fee > 0 and payout == fee:
                    comm_amount = round(fee * (comm_rate / 100.0), 2)
                    payout = max(0.0, round(fee - comm_amount, 2))

                results.append({
                    "id": r[0],
                    "slot_date": str(r[1]) if r[1] else None,
                    "slot_start_time": str(r[2]) if r[2] else None,
                    "appointment_category": r[3] or "IN_HOUSE",
                    "appointment_type": r[4] or "VIRTUAL",
                    "status": r[5] or "CONFIRMED",
                    "fee_amount": fee,
                    "payment_status": r[7] or "UNPAID",
                    "payout_status": r[8],
                    "payout_amount": payout,
                    "commission_rate": comm_rate,
                    "commission_amount": comm_amount,
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


class NutritionistPayablesHistoryAPI(APIView):
    """
    Get all payment and consultation records for a specific nutritionist,
    including total earnings, commission cut, pending payout balance, and patient refunds.
    Pure raw SQL.
    """
    def get(self, request, nutri_id):
        try:
            with connection.cursor() as cursor:
                # 1. Fetch Nutritionist Info
                cursor.execute("""
                    SELECT id, full_name, email, phone_number, nutritionist_type, is_nutritionist_approved
                    FROM user_user
                    WHERE id = %s;
                """, [nutri_id])
                nutri_row = cursor.fetchone()
                if not nutri_row:
                    return Response({"error": "Nutritionist not found"}, status=status.HTTP_404_NOT_FOUND)

                nutritionist_info = {
                    "id": nutri_row[0],
                    "name": nutri_row[1] or f"Doctor #{nutri_row[0]}",
                    "email": nutri_row[2] or "",
                    "phone": nutri_row[3] or "",
                    "type": nutri_row[4] or "inhouse",
                    "is_approved": bool(nutri_row[5]),
                }

                # 2. Fetch All Appointments & Payment Records
                cursor.execute("""
                    SELECT 
                        a.id, a.slot_date, a.slot_start_time, a.appointment_category, a.appointment_type,
                        a.status, COALESCE(a.fee_amount, 0) as fee_amount, a.payment_status,
                        COALESCE(a.payout_status, 'PENDING') as payout_status,
                        COALESCE(a.payout_amount, 0) as payout_amount, a.payout_transaction_ref, a.payout_marked_at,
                        COALESCE(a.refund_amount, 0) as refund_amount, a.refund_notes, a.refunded_at,
                        a.cancelled_by, a.cancellation_reason, a.created_at,
                        p.id as patient_id, COALESCE(p.full_name, 'Patient') as patient_name,
                        COALESCE(p.email, '') as patient_email, COALESCE(p.phone_number, '') as patient_phone,
                        COALESCE(a.commission_rate, 5.00) as commission_rate,
                        COALESCE(a.commission_amount, 0.00) as commission_amount
                    FROM appointments_appointment a
                    LEFT JOIN user_user p ON a.patient_id = p.id
                    WHERE a.nutritionist_id = %s
                    ORDER BY a.created_at DESC;
                """, [nutri_id])
                rows = cursor.fetchall()

            records = []
            total_fees = 0.0
            total_commission = 0.0
            total_payout_amount = 0.0
            pending_payout_total = 0.0
            paid_payout_total = 0.0
            pending_payout_count = 0
            paid_payout_count = 0
            pending_refund_total = 0.0
            refunded_total = 0.0

            for r in rows:
                fee = float(r[6])
                payout = float(r[9])
                comm_rate = float(r[22]) if len(r) > 22 and r[22] is not None else 5.0
                comm_amount = float(r[23]) if len(r) > 23 and r[23] is not None else 0.0
                payout_st = str(r[8] or "PENDING").upper()
                pay_st = str(r[7] or "UNPAID").upper()
                ref_amount = float(r[12])

                if comm_amount <= 0 and fee > 0 and payout > 0 and fee > payout:
                    comm_amount = round(fee - payout, 2)
                elif comm_amount <= 0 and fee > 0 and payout == fee:
                    comm_amount = round(fee * (comm_rate / 100.0), 2)
                    payout = max(0.0, round(fee - comm_amount, 2))

                total_fees += fee
                total_commission += comm_amount
                total_payout_amount += payout

                if payout_st == "PAID":
                    paid_payout_total += payout
                    paid_payout_count += 1
                else:
                    pending_payout_total += payout
                    pending_payout_count += 1

                if pay_st == "REFUNDED":
                    refunded_total += ref_amount
                elif pay_st == "PENDING_REFUND" or (str(r[5]).upper() == "CANCELLED" and ref_amount > 0):
                    pending_refund_total += ref_amount

                records.append({
                    "id": r[0],
                    "slot_date": str(r[1]) if r[1] else None,
                    "slot_start_time": str(r[2]) if r[2] else None,
                    "appointment_category": r[3] or "IN_HOUSE",
                    "appointment_type": r[4] or "VIRTUAL",
                    "status": r[5] or "CONFIRMED",
                    "fee_amount": fee,
                    "payment_status": pay_st,
                    "payout_status": payout_st,
                    "payout_amount": payout,
                    "commission_rate": comm_rate,
                    "commission_amount": comm_amount,
                    "payout_transaction_ref": r[10] or "",
                    "payout_marked_at": r[11].isoformat() if r[11] else None,
                    "refund_amount": ref_amount,
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
                    }
                })

            summary = {
                "total_appointments": len(records),
                "total_fees_collected": round(total_fees, 2),
                "total_commission_cut": round(total_commission, 2),
                "total_payout_amount": round(total_payout_amount, 2),
                "pending_payout_total": round(pending_payout_total, 2),
                "pending_payout_count": pending_payout_count,
                "paid_payout_total": round(paid_payout_total, 2),
                "paid_payout_count": paid_payout_count,
                "pending_refund_total": round(pending_refund_total, 2),
                "refunded_total": round(refunded_total, 2),
            }

            return Response({
                "status": "success",
                "nutritionist": nutritionist_info,
                "summary": summary,
                "records": records
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BulkPayableActionAPI(APIView):
    """
    Settle payouts or process refunds in one go for multiple appointments.
    Pure raw SQL.
    """
    def post(self, request):
        try:
            data = request.data
            appointment_ids = data.get("appointment_ids", [])
            action = str(data.get("action", "PAYOUT")).strip().upper()
            target_status = str(data.get("status", "PAID" if action == "PAYOUT" else "REFUNDED")).strip().upper()
            transaction_ref = str(data.get("transaction_ref", "")).strip()
            notes = str(data.get("notes", "")).strip()
            now_utc = datetime.now(timezone.utc)

            if not appointment_ids or not isinstance(appointment_ids, list):
                return Response({"error": "No appointment_ids provided"}, status=status.HTTP_400_BAD_REQUEST)

            int_ids = [int(i) for i in appointment_ids if str(i).isdigit()]
            if not int_ids:
                return Response({"error": "Invalid appointment_ids"}, status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                if action == "PAYOUT":
                    query = """
                        UPDATE appointments_appointment
                        SET payout_status = %s,
                            payout_marked_at = %s,
                            payout_transaction_ref = COALESCE(NULLIF(%s, ''), payout_transaction_ref)
                        WHERE id = ANY(%s)
                        RETURNING id, COALESCE(payout_amount, fee_amount, 0);
                    """
                    cursor.execute(query, [target_status, now_utc, transaction_ref, int_ids])
                    rows = cursor.fetchall()
                    total_amount = sum(float(r[1]) for r in rows)

                elif action == "REFUND":
                    query = """
                        UPDATE appointments_appointment
                        SET payment_status = %s,
                            refunded_at = %s,
                            refund_notes = COALESCE(NULLIF(%s, ''), refund_notes)
                        WHERE id = ANY(%s)
                        RETURNING id, COALESCE(refund_amount, fee_amount, 0);
                    """
                    cursor.execute(query, [target_status, now_utc, notes or transaction_ref, int_ids])
                    rows = cursor.fetchall()
                    total_amount = sum(float(r[1]) for r in rows)

                else:
                    return Response({"error": f"Unsupported action '{action}'. Supported: PAYOUT, REFUND"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                "status": "success",
                "action": action,
                "target_status": target_status,
                "updated_count": len(rows),
                "total_amount": round(total_amount, 2),
                "updated_ids": [r[0] for r in rows],
                "message": f"Successfully processed {len(rows)} record(s) in one go (Total: ₹{round(total_amount, 2)})"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

