from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny


def parse_notification(row):
    nid, uid, msg, ntype, is_read, created_at = row
    lines = (msg or "").split('\n')
    title = lines[0].strip() if lines else "Notification"
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else (lines[0].strip() if lines else "")
    msg_lower = (msg or "").lower()

    if 'cancelled' in msg_lower or 'cancellation' in msg_lower:
        category = 'Appointment Cancelled'
    elif 'appointment' in msg_lower and ('failed' in msg_lower or 'conflict' in msg_lower):
        category = 'Appointment Failed'
    elif 'appointment' in msg_lower or 'consultation' in msg_lower or 'booked' in msg_lower:
        category = 'Appointment'
    elif 'payment failed' in msg_lower or ('payment' in msg_lower and 'failed' in msg_lower):
        category = 'Payment Failed'
    elif 'purchased' in msg_lower or 'purchase' in msg_lower or 'subscription' in msg_lower:
        category = 'Plan Purchase'
    elif 'registered' in msg_lower or 'registration' in msg_lower:
        category = 'Registration'
    elif 'assigned' in msg_lower or 'assignment' in msg_lower:
        category = 'Assignment'
    elif 'expir' in msg_lower:
        category = 'Expiry'
    else:
        category = 'General'

    return {
        "id": nid,
        "title": title,
        "message": body or title,
        "type": category,
        "notif_type": "ADMIN" if ntype == "admin" else "USER",
        "user_id": uid,
        "is_read": bool(is_read),
        "created_at": created_at.isoformat() if created_at else None
    }


class AdminNotificationAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        notif_type = request.query_params.get('type', 'admin')

        query = """
            SELECT id, user_id, message, type, is_read, created_at
            FROM user_notifications
            WHERE type = %s
            ORDER BY created_at DESC;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [notif_type])
            rows = cursor.fetchall()

        notifications = [parse_notification(r) for r in rows]
        unread_count = sum(1 for n in notifications if not n["is_read"])

        return Response({
            "type": notif_type,
            "total": len(notifications),
            "unread_count": unread_count,
            "notifications": notifications
        })


class MarkNotificationReadAPI(APIView):
    permission_classes = [AllowAny]

    def patch(self, request, notification_id):
        query = "UPDATE user_notifications SET is_read = true WHERE id = %s RETURNING id;"
        with connection.cursor() as cursor:
            cursor.execute(query, [notification_id])
            row = cursor.fetchone()

        if not row:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "message": "Notification marked as read",
            "id": notification_id
        }, status=status.HTTP_200_OK)


class MarkAllNotificationsReadAPI(APIView):
    permission_classes = [AllowAny]

    def patch(self, request):
        notif_type = request.query_params.get('type', 'admin')
        query = "UPDATE user_notifications SET is_read = true WHERE type = %s;"
        with connection.cursor() as cursor:
            cursor.execute(query, [notif_type])

        return Response({"message": f"All {notif_type} notifications marked as read"})


class TriggerNotificationEventAPI(APIView):
    """
    Endpoint to trigger, simulate, or webhook real-time WebSocket notifications for admin alerts:
    - nutritionist_registered
    - plan_purchased
    - payment_failed
    - appointment_booked
    - appointment_cancelled
    - appointment_failed
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from .utils import (
            notify_nutritionist_registered,
            notify_plan_purchased,
            notify_payment_failed,
            notify_appointment_booked,
            notify_appointment_cancelled,
            notify_appointment_failed,
        )

        event = request.data.get("event", "nutritionist_registered").lower().strip()
        data = request.data.get("data", {}) or request.data

        notif_id = None
        event_name = event

        if event in ["nutritionist_registered", "nutritionist", "new_nutritionist"]:
            user_id = data.get("user_id", 108)
            full_name = data.get("full_name", "Dr. Pooja Deshmukh")
            email = data.get("email", "dr.pooja@example.com")
            nutritionist_type = data.get("nutritionist_type", "expert")
            notif_id = notify_nutritionist_registered(
                user_id=user_id,
                full_name=full_name,
                email=email,
                nutritionist_type=nutritionist_type
            )

        elif event in ["plan_purchased", "subscription_purchased", "payment_success"]:
            user_id = data.get("user_id", 101)
            user_name = data.get("user_name", "Arjun Kapoor")
            plan_name = data.get("plan_name", "Pro Transformation Plan (6 Months)")
            amount = data.get("amount", 2999)
            payment_id = data.get("payment_id", "pay_live_9921a")
            notif_id = notify_plan_purchased(
                user_id=user_id,
                user_name=user_name,
                plan_name=plan_name,
                amount=amount,
                payment_id=payment_id
            )

        elif event in ["payment_failed", "plan_failed", "payment_error"]:
            user_id = data.get("user_id", 102)
            user_name = data.get("user_name", "Priya Sen")
            plan_name = data.get("plan_name", "Elite Nutrition Plan")
            amount = data.get("amount", 1999)
            error_reason = data.get("reason", "Card limit exceeded / Insufficient funds")
            notif_id = notify_payment_failed(
                user_id=user_id,
                user_name=user_name,
                plan_name=plan_name,
                amount=amount,
                error_reason=error_reason
            )

        elif event in ["appointment_booked", "appointment_created"]:
            appointment_id = data.get("appointment_id", 342)
            patient_name = data.get("patient_name", "Sameer Verma")
            nutritionist_name = data.get("nutritionist_name", "Dr. Rohit Mathur")
            slot_date = data.get("slot_date", "2026-11-20")
            slot_time = data.get("slot_time", "10:30 AM")
            fee = data.get("fee", 799)
            appt_type = data.get("appointment_type", "VIRTUAL")
            notif_id = notify_appointment_booked(
                appointment_id=appointment_id,
                patient_name=patient_name,
                nutritionist_name=nutritionist_name,
                slot_date=slot_date,
                slot_time=slot_time,
                fee=fee,
                appt_type=appt_type
            )

        elif event in ["appointment_cancelled", "consultation_cancelled"]:
            appointment_id = data.get("appointment_id", 342)
            patient_name = data.get("patient_name", "Sameer Verma")
            nutritionist_name = data.get("nutritionist_name", "Dr. Rohit Mathur")
            reason = data.get("reason", "Patient emergency rescheduling request")
            cancelled_by = data.get("cancelled_by", "Patient")
            notif_id = notify_appointment_cancelled(
                appointment_id=appointment_id,
                patient_name=patient_name,
                nutritionist_name=nutritionist_name,
                reason=reason,
                cancelled_by=cancelled_by
            )

        elif event in ["appointment_failed", "booking_failed"]:
            patient_name = data.get("patient_name", "Kavita Rao")
            nutritionist_name = data.get("nutritionist_name", "Dr. Ananya Roy")
            reason = data.get("reason", "Selected timeslot already locked by another user")
            notif_id = notify_appointment_failed(
                patient_name=patient_name,
                reason=reason,
                nutritionist_name=nutritionist_name
            )

        else:
            return Response(
                {"error": f"Unknown event '{event}'. Supported: nutritionist_registered, plan_purchased, payment_failed, appointment_booked, appointment_cancelled, appointment_failed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "success": True,
            "event": event_name,
            "notification_id": notif_id,
            "message": "Notification generated and saved to DB successfully for admin API retrieval."
        }, status=status.HTTP_201_CREATED)

