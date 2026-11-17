from datetime import date
from django.db import connection


def get_user_plan_and_upgrade(user_id):
    query = """
        SELECT s.id, s.end_date, pl.name
        FROM subscriptions_usersubscription s
        LEFT JOIN subscriptions_plan pl ON s.plan_id = pl.id
        WHERE s.user_id = %s AND s.is_active = true
        ORDER BY s.created_at DESC
        LIMIT 1;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [user_id])
        row = cursor.fetchone()

    if not row:
        return {
            "plan": "free",
            "upgrade": {
                "show": True,
                "message": "Start Basic Plan 🚀"
            }
        }

    sub_id, end_date, plan_name = row
    if end_date and end_date < date.today():
        return {
            "plan": "free",
            "upgrade": {
                "show": True,
                "message": "Your plan expired. Upgrade again 🚀"
            }
        }

    pname = (plan_name or "free").lower()
    return {
        "plan": pname,
        "upgrade": {
            "show": pname == "basic",
            "message": "Upgrade to Pro 🚀" if pname == "basic" else None
        }
    }
