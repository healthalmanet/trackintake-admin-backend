from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.utils import timezone


class AppointmentListAPI(APIView):
    """
    Retrieve appointments list with search, status filtering, category filtering,
    date filtering (from_date, to_date), timeline filtering (ongoing, upcoming, completed, past),
    and summary statistics using direct read queries on existing production tables.
    """

    def get(self, request):
        search = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '').strip()
        category_filter = request.GET.get('category', '').strip()
        type_filter = request.GET.get('type', '').strip()
        from_date = request.GET.get('from_date', '').strip()
        to_date = request.GET.get('to_date', '').strip()
        time_frame = request.GET.get('time_frame', '').strip().lower()

        try:
            page = max(1, int(request.GET.get('page', 1)))
            page_size = max(1, min(100, int(request.GET.get('page_size', 15))))
        except ValueError:
            page = 1
            page_size = 15

        offset = (page - 1) * page_size

        # Overall Stats
        stats_query = """
        SELECT 
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE UPPER(status) = 'CONFIRMED') AS confirmed,
            COUNT(*) FILTER (WHERE UPPER(status) IN ('PENDING_REVIEW', 'AWAITING_PAYMENT')) AS pending,
            COUNT(*) FILTER (WHERE UPPER(status) = 'COMPLETED') AS completed,
            COUNT(*) FILTER (WHERE UPPER(status) = 'CANCELLED') AS cancelled,
            COUNT(*) FILTER (WHERE (COALESCE(slot_date, CAST(created_at AS date)) = CURRENT_DATE OR UPPER(status) = 'IN_PROGRESS') AND UPPER(status) != 'CANCELLED') AS ongoing,
            COUNT(*) FILTER (WHERE COALESCE(slot_date, CAST(created_at AS date)) > CURRENT_DATE AND UPPER(status) NOT IN ('COMPLETED', 'CANCELLED')) AS upcoming,
            COUNT(*) FILTER (WHERE COALESCE(slot_date, CAST(created_at AS date)) < CURRENT_DATE OR UPPER(status) IN ('COMPLETED', 'CANCELLED')) AS past,
            COALESCE(SUM(fee_amount) FILTER (WHERE UPPER(payment_status) = 'PAID'), 0) AS total_revenue,
            COALESCE(SUM(refund_amount) FILTER (WHERE UPPER(payment_status) = 'REFUNDED'), 0) AS total_refunded,
            COUNT(*) FILTER (WHERE UPPER(appointment_category) = 'IN_HOUSE') AS inhouse,
            COUNT(*) FILTER (WHERE UPPER(appointment_category) = 'EXPERT') AS expert
        FROM appointments_appointment;
        """

        # Filtered query
        where_clauses = ["1=1"]
        params = []

        if search:
            where_clauses.append("""
                (p.full_name ILIKE %s OR p.email ILIKE %s OR 
                 n.full_name ILIKE %s OR n.email ILIKE %s OR 
                 CAST(a.id AS TEXT) ILIKE %s)
            """)
            s = f"%{search}%"
            params.extend([s, s, s, s, s])

        if status_filter and status_filter.upper() != 'ALL':
            where_clauses.append("UPPER(a.status) = %s")
            params.append(status_filter.upper())

        if category_filter and category_filter.upper() != 'ALL':
            where_clauses.append("UPPER(a.appointment_category) = %s")
            params.append(category_filter.upper())

        if type_filter and type_filter.upper() != 'ALL':
            where_clauses.append("UPPER(a.appointment_type) = %s")
            params.append(type_filter.upper())

        # Date Filters
        if from_date:
            where_clauses.append("COALESCE(a.slot_date, CAST(a.created_at AS date)) >= %s")
            params.append(from_date)

        if to_date:
            where_clauses.append("COALESCE(a.slot_date, CAST(a.created_at AS date)) <= %s")
            params.append(to_date)

        # Timeline / Timeframe Filter
        if time_frame == 'ongoing':
            where_clauses.append("((COALESCE(a.slot_date, CAST(a.created_at AS date)) = CURRENT_DATE OR UPPER(a.status) = 'IN_PROGRESS') AND UPPER(a.status) != 'CANCELLED')")
        elif time_frame == 'upcoming':
            where_clauses.append("(COALESCE(a.slot_date, CAST(a.created_at AS date)) > CURRENT_DATE AND UPPER(a.status) NOT IN ('COMPLETED', 'CANCELLED'))")
        elif time_frame == 'completed':
            where_clauses.append("UPPER(a.status) = 'COMPLETED'")
        elif time_frame == 'past':
            where_clauses.append("((COALESCE(a.slot_date, CAST(a.created_at AS date)) < CURRENT_DATE) OR UPPER(a.status) IN ('COMPLETED', 'CANCELLED'))")

        where_sql = " AND ".join(where_clauses)

        count_query = f"""
        SELECT COUNT(*)
        FROM appointments_appointment a
        LEFT JOIN user_user p ON a.patient_id = p.id
        LEFT JOIN user_user n ON a.nutritionist_id = n.id
        WHERE {where_sql};
        """

        data_query = f"""
        SELECT 
            a.id,
            a.slot_date,
            a.slot_start_time,
            a.slot_end_time,
            a.appointment_category,
            a.appointment_type,
            a.status,
            a.meeting_link,
            COALESCE(a.fee_amount, 0) AS fee_amount,
            a.payment_status,
            a.payout_status,
            COALESCE(a.payout_amount, 0) AS payout_amount,
            a.payout_transaction_ref,
            COALESCE(a.refund_amount, 0) AS refund_amount,
            a.cancellation_reason,
            a.cancelled_by,
            p.id AS patient_id,
            COALESCE(p.full_name, 'Patient') AS patient_name,
            p.email AS patient_email,
            n.id AS nutritionist_id,
            COALESCE(n.full_name, 'Nutritionist') AS nutritionist_name,
            n.email AS nutritionist_email,
            a.created_at,
            COALESCE(a.slot_date, CAST(a.created_at AS date)) AS effective_date,
            CASE 
                WHEN UPPER(a.status) = 'CANCELLED' THEN 'CANCELLED'
                WHEN UPPER(a.status) = 'COMPLETED' THEN 'COMPLETED'
                WHEN UPPER(a.status) = 'IN_PROGRESS' OR COALESCE(a.slot_date, CAST(a.created_at AS date)) = CURRENT_DATE THEN 'ONGOING'
                WHEN COALESCE(a.slot_date, CAST(a.created_at AS date)) > CURRENT_DATE THEN 'UPCOMING'
                ELSE 'PAST'
            END AS timeline_status
        FROM appointments_appointment a
        LEFT JOIN user_user p ON a.patient_id = p.id
        LEFT JOIN user_user n ON a.nutritionist_id = n.id
        WHERE {where_sql}
        ORDER BY COALESCE(a.slot_date, CAST(a.created_at AS date)) DESC, a.created_at DESC
        LIMIT %s OFFSET %s;
        """

        with connection.cursor() as cursor:
            # 1. Stats
            cursor.execute(stats_query)
            st_row = cursor.fetchone() or (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            stats_dict = {
                "total": st_row[0] or 0,
                "confirmed": st_row[1] or 0,
                "pending": st_row[2] or 0,
                "completed": st_row[3] or 0,
                "cancelled": st_row[4] or 0,
                "ongoing": st_row[5] or 0,
                "upcoming": st_row[6] or 0,
                "past": st_row[7] or 0,
                "total_revenue": float(st_row[8] or 0),
                "total_refunded": float(st_row[9] or 0),
                "inhouse": st_row[10] or 0,
                "expert": st_row[11] or 0,
            }

            # 2. Total filtered
            cursor.execute(count_query, params)
            total_filtered = cursor.fetchone()[0]

            # 3. Data rows
            cursor.execute(data_query, params + [page_size, offset])
            rows = cursor.fetchall()

            results = []
            for r in rows:
                results.append({
                    "id": r[0],
                    "slot_date": str(r[1]) if r[1] else None,
                    "slot_start_time": str(r[2]) if r[2] else None,
                    "slot_end_time": str(r[3]) if r[3] else None,
                    "appointment_category": r[4],
                    "appointment_type": r[5],
                    "status": r[6],
                    "meeting_link": r[7],
                    "fee_amount": float(r[8]),
                    "payment_status": r[9],
                    "payout_status": r[10],
                    "payout_amount": float(r[11]),
                    "payout_transaction_ref": r[12],
                    "refund_amount": float(r[13]),
                    "cancellation_reason": r[14],
                    "cancelled_by": r[15],
                    "patient": {
                        "id": r[16],
                        "name": r[17],
                        "email": r[18],
                    },
                    "nutritionist": {
                        "id": r[19],
                        "name": r[20],
                        "email": r[21],
                    },
                    "created_at": r[22].isoformat() if r[22] else None,
                    "effective_date": str(r[23]) if r[23] else None,
                    "timeline_status": r[24] or "PAST",
                })

        total_pages = (total_filtered + page_size - 1) // page_size if total_filtered > 0 else 1

        return Response({
            "results": results,
            "total": total_filtered,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "stats": stats_dict
        }, status=status.HTTP_200_OK)


class AppointmentDetailAPI(APIView):
    """
    Update appointment status, meeting link, slot scheduling, cancellation reason or notes.
    """

    def get(self, request, pk):
        query = """
        SELECT 
            a.id, a.slot_date, a.slot_start_time, a.slot_end_time,
            a.appointment_category, a.appointment_type, a.status,
            a.meeting_link, COALESCE(a.fee_amount, 0), a.payment_status,
            a.payout_status, COALESCE(a.payout_amount, 0), a.payout_transaction_ref,
            COALESCE(a.refund_amount, 0), a.cancellation_reason, a.cancelled_by,
            p.id, COALESCE(p.full_name, 'Patient'), p.email,
            n.id, COALESCE(n.full_name, 'Nutritionist'), n.email,
            a.instructions, a.notes, a.created_at,
            COALESCE(a.slot_date, CAST(a.created_at AS date)) AS effective_date
        FROM appointments_appointment a
        LEFT JOIN user_user p ON a.patient_id = p.id
        LEFT JOIN user_user n ON a.nutritionist_id = n.id
        WHERE a.id = %s;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [pk])
            r = cursor.fetchone()
            if not r:
                return Response({"error": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)

            data = {
                "id": r[0],
                "slot_date": str(r[1]) if r[1] else None,
                "slot_start_time": str(r[2]) if r[2] else None,
                "slot_end_time": str(r[3]) if r[3] else None,
                "appointment_category": r[4],
                "appointment_type": r[5],
                "status": r[6],
                "meeting_link": r[7],
                "fee_amount": float(r[8]),
                "payment_status": r[9],
                "payout_status": r[10],
                "payout_amount": float(r[11]),
                "payout_transaction_ref": r[12],
                "refund_amount": float(r[13]),
                "cancellation_reason": r[14],
                "cancelled_by": r[15],
                "patient": {"id": r[16], "name": r[17], "email": r[18]},
                "nutritionist": {"id": r[19], "name": r[20], "email": r[21]},
                "instructions": r[22],
                "notes": r[23],
                "created_at": r[24].isoformat() if r[24] else None,
                "effective_date": str(r[25]) if r[25] else None,
            }
            return Response(data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        status_val = request.data.get('status')
        meeting_link = request.data.get('meeting_link')
        cancellation_reason = request.data.get('cancellation_reason')
        cancelled_by = request.data.get('cancelled_by', 'ADMIN')
        slot_date = request.data.get('slot_date')
        slot_start_time = request.data.get('slot_start_time')
        slot_end_time = request.data.get('slot_end_time')
        notes = request.data.get('notes')

        updates = []
        params = []

        if status_val:
            updates.append("status = %s")
            params.append(status_val.upper())
            if status_val.upper() == 'CANCELLED':
                updates.append("cancelled_by = %s")
                params.append(cancelled_by)
                updates.append("cancelled_at = %s")
                params.append(timezone.now())
                if cancellation_reason:
                    updates.append("cancellation_reason = %s")
                    params.append(cancellation_reason)

        if meeting_link is not None:
            updates.append("meeting_link = %s")
            params.append(meeting_link)

        if slot_date is not None:
            updates.append("slot_date = %s")
            params.append(slot_date if slot_date else None)

        if slot_start_time is not None:
            updates.append("slot_start_time = %s")
            params.append(slot_start_time if slot_start_time else None)

        if slot_end_time is not None:
            updates.append("slot_end_time = %s")
            params.append(slot_end_time if slot_end_time else None)

        if notes is not None:
            updates.append("notes = %s")
            params.append(notes)

        if not updates:
            return Response({"message": "No changes provided"}, status=status.HTTP_400_BAD_REQUEST)

        params.append(pk)
        sql = f"UPDATE appointments_appointment SET {', '.join(updates)} WHERE id = %s RETURNING id, status;"

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            res = cursor.fetchone()
            if not res:
                return Response({"error": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)

            # If appointment cancelled, fire real-time WebSocket notification to admin
            if status_val and status_val.upper() == 'CANCELLED':
                try:
                    cursor.execute("""
                        SELECT COALESCE(p.full_name, 'Patient'), COALESCE(n.full_name, 'Practitioner')
                        FROM appointments_appointment a
                        LEFT JOIN user_user p ON a.patient_id = p.id
                        LEFT JOIN user_user n ON a.nutritionist_id = n.id
                        WHERE a.id = %s;
                    """, [pk])
                    names_row = cursor.fetchone()
                    patient_name = names_row[0] if names_row and names_row[0] else "Patient"
                    nutritionist_name = names_row[1] if names_row and names_row[1] else "Nutritionist"

                    from notifications.utils import notify_appointment_cancelled
                    notify_appointment_cancelled(
                        appointment_id=pk,
                        patient_name=patient_name,
                        nutritionist_name=nutritionist_name,
                        reason=cancellation_reason or "Cancelled via Admin panel",
                        cancelled_by=cancelled_by or "ADMIN"
                    )
                except Exception as ex:
                    print(f"[Notify Appointment Cancelled Warning]: {ex}")

        return Response({"message": "Appointment updated successfully", "id": res[0], "status": res[1]}, status=status.HTTP_200_OK)

