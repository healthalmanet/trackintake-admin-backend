from datetime import datetime, timezone
from django.db import connection


def create_notification(message, notification_type='admin', user_id=None, title=None, category=None, metadata=None):
    """
    Persists an admin notification to PostgreSQL user_notifications for retrieval via REST API.
    """
    now_utc = datetime.now(timezone.utc)
    computed_title = title
    if not computed_title:
        lines = (message or "").split('\n')
        computed_title = lines[0] if lines else "New Alert"

    # Store with title on first line for consistent split/parsing
    db_message = f"{computed_title}\n{message}" if (computed_title and not message.startswith(computed_title)) else message

    # Validate foreign key user_id exists in user_user to prevent constraint failure
    valid_user_id = None
    if user_id:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM user_user WHERE id = %s;", [user_id])
                if cursor.fetchone():
                    valid_user_id = user_id
        except Exception:
            valid_user_id = None

    query = """
        INSERT INTO user_notifications (message, type, user_id, is_read, created_at)
        VALUES (%s, %s, %s, false, %s)
        RETURNING id;
    """
    notif_id = None
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, [db_message, notification_type, valid_user_id, now_utc])
            notif_id = cursor.fetchone()[0]
    except Exception as e:
        print(f"[Create Notification DB Error]: {e}")

    return notif_id


def _clean_dr_name(name):
    if not name:
        return "Practitioner"
    n = name.strip()
    return n if n.startswith("Dr.") else f"Dr. {n}"


# 1. NEW NUTRITIONIST REGISTRATION
def notify_nutritionist_registered(user_id, full_name, email="", nutritionist_type="inhouse"):
    """
    Alerts admin when a new clinical nutritionist or specialist registers.
    """
    type_label = "In-House" if str(nutritionist_type).lower() in ["inhouse", "in_house"] else "Expert Specialist"
    doc_name = _clean_dr_name(full_name)
    return create_notification(
        title="New Nutritionist Registration",
        message=f"{doc_name} ({email or 'No email'}) registered as an {type_label} practitioner. Clinical credentials & profile awaiting review.",
        notification_type='admin',
        user_id=user_id,
        category="Registration",
        metadata={
            "action": "review_profile",
            "page": "approvals",
            "user_id": user_id,
            "full_name": full_name,
            "nutritionist_type": nutritionist_type
        }
    )


# 2. PLAN PURCHASED & FAILED PAYMENTS
def notify_plan_purchased(user_id, user_name, plan_name, amount, payment_id=""):
    """
    Alerts admin when a patient successfully purchases a subscription plan.
    """
    return create_notification(
        title="Subscription Plan Purchased",
        message=f"{user_name} purchased {plan_name} for ₹{amount} (Payment ID: #{payment_id}).",
        notification_type='admin',
        user_id=user_id,
        category="Plan Purchase",
        metadata={
            "action": "view_payment",
            "page": "payments",
            "user_id": user_id,
            "plan_name": plan_name,
            "amount": amount,
            "payment_id": payment_id
        }
    )


def notify_payment_failed(user_id, user_name, plan_name, amount, error_reason="Payment authorization failed"):
    """
    Alerts admin when a subscription or appointment payment attempt fails.
    """
    return create_notification(
        title="Payment Failed Alert",
        message=f"Payment of ₹{amount} failed for {user_name} on {plan_name}. Reason: {error_reason}.",
        notification_type='admin',
        user_id=user_id,
        category="Payment Failed",
        metadata={
            "action": "view_payment",
            "page": "payments",
            "user_id": user_id,
            "amount": amount,
            "error": error_reason
        }
    )


# 3. APPOINTMENT BOOKING NOTIFICATIONS (BOOKED, CANCELLED, FAILED)
def notify_appointment_booked(appointment_id, patient_name, nutritionist_name, slot_date, slot_time="", fee=0, appt_type="VIRTUAL"):
    """
    Alerts admin when a new appointment booking is created.
    """
    mode_text = "Virtual Video Session" if appt_type.upper() == "VIRTUAL" else "In-Clinic Consultation"
    time_text = f" at {slot_time}" if slot_time else ""
    doc_name = _clean_dr_name(nutritionist_name)
    return create_notification(
        title="New Appointment Booked",
        message=f"{patient_name} booked a {mode_text} with {doc_name} on {slot_date}{time_text} (Fee: ₹{fee}).",
        notification_type='admin',
        category="Appointment",
        metadata={
            "action": "view_appointment",
            "page": "appointments",
            "appointment_id": appointment_id,
            "patient": patient_name,
            "nutritionist": nutritionist_name,
            "slot_date": str(slot_date),
            "fee": fee
        }
    )


def notify_appointment_cancelled(appointment_id, patient_name, nutritionist_name, reason="No reason provided", cancelled_by="Patient"):
    """
    Alerts admin when an appointment is cancelled.
    """
    doc_name = _clean_dr_name(nutritionist_name)
    return create_notification(
        title="Appointment Cancelled",
        message=f"Consultation #{appointment_id} ({patient_name} with {doc_name}) was cancelled by {cancelled_by}. Reason: {reason}.",
        notification_type='admin',
        category="Appointment Cancelled",
        metadata={
            "action": "view_appointment",
            "page": "appointments",
            "appointment_id": appointment_id,
            "patient": patient_name,
            "nutritionist": nutritionist_name,
            "reason": reason,
            "cancelled_by": cancelled_by
        }
    )


def notify_appointment_failed(patient_name, reason="Slot conflict or payment gateway error", nutritionist_name="Practitioner"):
    """
    Alerts admin when an appointment booking attempt fails.
    """
    doc_name = _clean_dr_name(nutritionist_name)
    return create_notification(
        title="Appointment Booking Failed",
        message=f"Consultation booking with {doc_name} failed for {patient_name}. Reason: {reason}.",
        notification_type='admin',
        category="Appointment Failed",
        metadata={
            "action": "view_appointments",
            "page": "appointments",
            "patient": patient_name,
            "reason": reason
        }
    )


# Standard legacy aliases
def create_registration_notification(user_name):
    return create_notification(
        message=f"New User Registration\n{user_name} registered a new account.",
        notification_type='admin',
        category="Registration"
    )


def create_plan_purchase_notification(user_name, plan_name, payment_id):
    return create_notification(
        message=f"Plan Purchased\n{user_name} purchased {plan_name} (ID: {payment_id}).",
        notification_type='admin',
        category="Plan Purchase"
    )


def create_assignment_notification(user_name, nutritionist_name, specialization="general care"):
    return create_notification(
        message=f"Nutritionist Assigned\n{nutritionist_name} assigned to {user_name} for {specialization}.",
        notification_type='admin',
        category="Assignment"
    )
