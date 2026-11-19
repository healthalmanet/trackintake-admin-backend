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
    mode_text = "Virtual Video Session" if str(appt_type).upper() == "VIRTUAL" else "In-Clinic Consultation"
    time_text = f" at {slot_time}" if slot_time else ""
    doc_name = _clean_dr_name(nutritionist_name)
    return create_notification(
        title="New Appointment Booked",
        message=f"Consultation #{appointment_id}: {patient_name} booked a {mode_text} with {doc_name} on {slot_date}{time_text} (Fee: ₹{fee}).",
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


# 4. AUTO-DETECTION & SYNC FROM LIVE DATABASE TABLES
def sync_database_events_to_notifications(limit_per_category=5):
    """
    Automatically detects new registrations, appointments (booked/cancelled),
    and subscription payments from the database tables and generates
    corresponding admin notifications in user_notifications if not already present.
    """
    synced_counts = {
        "nutritionists": 0,
        "appointments_booked": 0,
        "appointments_cancelled": 0,
        "payments": 0
    }

    # 1. Newly Registered Nutritionists (user_user where role = 'nutritionist')
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.full_name, u.email, u.nutritionist_type, u.date_joined
                FROM user_user u
                WHERE u.role = 'nutritionist'
                  AND u.date_joined >= NOW() - INTERVAL '30 days'
                  AND NOT EXISTS (
                      SELECT 1 FROM user_notifications un
                      WHERE un.type = 'admin'
                        AND (
                            un.user_id = u.id
                            OR (u.email IS NOT NULL AND u.email != '' AND un.message ILIKE '%%' || u.email || '%%')
                            OR (u.full_name IS NOT NULL AND u.full_name != '' AND un.message ILIKE '%%' || u.full_name || '%%' AND un.message ILIKE '%%register%%')
                        )
                  )
                ORDER BY u.id DESC
                LIMIT %s;
            """, [limit_per_category])
            rows = cursor.fetchall()
            for r in rows:
                uid, name, email, ntype, djoined = r
                nid = notify_nutritionist_registered(
                    user_id=uid,
                    full_name=name or f"Nutritionist #{uid}",
                    email=email or "",
                    nutritionist_type=ntype or "inhouse"
                )
                if nid:
                    synced_counts["nutritionists"] += 1
    except Exception as e:
        print(f"[Sync Nutritionists Error]: {e}")

    # 2. Booked Appointments (appointments_appointment where status != 'CANCELLED')
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT a.id, a.patient_id, COALESCE(p.full_name, 'Patient #' || a.patient_id) as patient_name,
                       a.nutritionist_id, COALESCE(n.full_name, 'Practitioner #' || a.nutritionist_id) as nutritionist_name,
                       a.slot_date, a.slot_start_time, a.fee_amount, a.appointment_type, a.created_at
                FROM appointments_appointment a
                LEFT JOIN user_user p ON a.patient_id = p.id
                LEFT JOIN user_user n ON a.nutritionist_id = n.id
                WHERE (a.status IS NULL OR UPPER(a.status) NOT IN ('CANCELLED', 'CANCELED'))
                  AND a.created_at >= NOW() - INTERVAL '30 days'
                  AND NOT EXISTS (
                      SELECT 1 FROM user_notifications un
                      WHERE un.type = 'admin'
                        AND un.message LIKE '%%#' || a.id || '%%'
                        AND (un.message ILIKE '%%booked%%' OR un.message ILIKE '%%Appointment Booked%%')
                  )
                ORDER BY a.id DESC
                LIMIT %s;
            """, [limit_per_category])
            rows = cursor.fetchall()
            for r in rows:
                aid, pid, pname, nid, nname, sdate, stime, fee, atype, cat = r
                notif_id = notify_appointment_booked(
                    appointment_id=aid,
                    patient_name=pname,
                    nutritionist_name=nname,
                    slot_date=sdate or "Upcoming",
                    slot_time=str(stime) if stime else "",
                    fee=int(fee or 0),
                    appt_type=atype or "VIRTUAL"
                )
                if notif_id:
                    synced_counts["appointments_booked"] += 1
    except Exception as e:
        print(f"[Sync Booked Appointments Error]: {e}")

    # 3. Cancelled Appointments (appointments_appointment where status = 'CANCELLED')
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT a.id, a.patient_id, COALESCE(p.full_name, 'Patient #' || a.patient_id) as patient_name,
                       a.nutritionist_id, COALESCE(n.full_name, 'Practitioner #' || a.nutritionist_id) as nutritionist_name,
                       a.cancellation_reason, a.cancelled_by, a.cancelled_at
                FROM appointments_appointment a
                LEFT JOIN user_user p ON a.patient_id = p.id
                LEFT JOIN user_user n ON a.nutritionist_id = n.id
                WHERE UPPER(a.status) IN ('CANCELLED', 'CANCELED')
                  AND (a.cancelled_at IS NULL OR a.cancelled_at >= NOW() - INTERVAL '30 days' OR a.created_at >= NOW() - INTERVAL '30 days')
                  AND NOT EXISTS (
                      SELECT 1 FROM user_notifications un
                      WHERE un.type = 'admin'
                        AND un.message LIKE '%%#' || a.id || '%%'
                        AND (un.message ILIKE '%%cancel%%' OR un.message ILIKE '%%Cancelled%%')
                  )
                ORDER BY a.id DESC
                LIMIT %s;
            """, [limit_per_category])
            rows = cursor.fetchall()
            for r in rows:
                aid, pid, pname, nid, nname, reason, cby, cat = r
                notif_id = notify_appointment_cancelled(
                    appointment_id=aid,
                    patient_name=pname,
                    nutritionist_name=nname,
                    reason=reason or "Cancellation requested",
                    cancelled_by=cby or "Patient"
                )
                if notif_id:
                    synced_counts["appointments_cancelled"] += 1
    except Exception as e:
        print(f"[Sync Cancelled Appointments Error]: {e}")

    # 4. Plan Purchases (subscriptions_payment where status = 'SUCCESS' or 'CAPTURED')
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.user_id, COALESCE(u.full_name, 'User #' || p.user_id) as user_name,
                       p.amount, p.razorpay_payment_id, p.created_at
                FROM subscriptions_payment p
                LEFT JOIN user_user u ON p.user_id = u.id
                WHERE UPPER(p.status) IN ('SUCCESS', 'CAPTURED', 'PAID')
                  AND p.created_at >= NOW() - INTERVAL '30 days'
                  AND NOT EXISTS (
                      SELECT 1 FROM user_notifications un
                      WHERE un.type = 'admin'
                        AND (
                            (p.razorpay_payment_id IS NOT NULL AND p.razorpay_payment_id != '' AND un.message LIKE '%%' || p.razorpay_payment_id || '%%')
                            OR un.message LIKE '%%Payment ID: #' || p.id || '%%'
                        )
                  )
                ORDER BY p.id DESC
                LIMIT %s;
            """, [limit_per_category])
            rows = cursor.fetchall()
            for r in rows:
                pid, uid, uname, amt, pay_id, cat = r
                notif_id = notify_plan_purchased(
                    user_id=uid,
                    user_name=uname,
                    plan_name="Subscription Plan",
                    amount=int(amt or 0),
                    payment_id=pay_id or str(pid)
                )
                if notif_id:
                    synced_counts["payments"] += 1
    except Exception as e:
        print(f"[Sync Payments Error]: {e}")

    return synced_counts


# 5. GENERATE ALL TEST EVENTS
def generate_all_test_events():
    """
    Generates a full suite of test events (nutritionist, booking, cancellation, purchase, payment failure, booking failure)
    for simulation and instant verification.
    """
    ts = int(datetime.now(timezone.utc).timestamp()) % 100000
    results = {}
    results["nutritionist"] = notify_nutritionist_registered(
        user_id=None,
        full_name="Dr. Pooja Deshmukh",
        email=f"dr.pooja_{ts}@example.com",
        nutritionist_type="expert"
    )
    results["appointment_booked"] = notify_appointment_booked(
        appointment_id=400 + (ts % 500),
        patient_name="Sameer Verma",
        nutritionist_name="Dr. Rohit Mathur",
        slot_date="2026-11-20",
        slot_time="10:30 AM",
        fee=799,
        appt_type="VIRTUAL"
    )
    results["appointment_cancelled"] = notify_appointment_cancelled(
        appointment_id=400 + (ts % 500),
        patient_name="Sameer Verma",
        nutritionist_name="Dr. Rohit Mathur",
        reason="Patient emergency rescheduling request",
        cancelled_by="Patient"
    )
    results["plan_purchased"] = notify_plan_purchased(
        user_id=None,
        user_name="Arjun Kapoor",
        plan_name="Pro Transformation Plan (6 Months)",
        amount=2999,
        payment_id=f"pay_live_{ts}"
    )
    results["payment_failed"] = notify_payment_failed(
        user_id=None,
        user_name="Priya Sen",
        plan_name="Elite Nutrition Plan",
        amount=1999,
        error_reason="Card limit exceeded / Insufficient funds"
    )
    results["appointment_failed"] = notify_appointment_failed(
        patient_name="Kavita Rao",
        reason="Selected timeslot already locked by another user",
        nutritionist_name="Dr. Ananya Roy"
    )
    return results

