from datetime import date
from .models import UserSubscription, SubscriptionPlan


def get_user_plan_and_upgrade(user_id):
    
    subscription = UserSubscription.objects.filter(
        user_id=user_id,
        is_active=True
    ).first()

    if not subscription:
        return {
            "plan": "free",
            "upgrade": {
                "show": True,
                "message": "Start Basic Plan 🚀"
            }
        }

    if subscription.end_date and subscription.end_date < date.today():
        subscription.is_active = False
        subscription.save()

        return {
            "plan": "free",
            "upgrade": {
                "show": True,
                "message": "Your plan expired. Upgrade again 🚀"
            }
        }

    plan = SubscriptionPlan.objects.filter(id=subscription.plan_id).first()
    plan_name = plan.name.lower() if plan else "free"

    upgrade = None

    if plan_name == "basic":
        upgrade = {
            "show": True,
            "message": "Upgrade to Pro 🚀"
        }

    elif plan_name == "pro":
        upgrade = {
            "show": False,
            "message": None
        }

    return {
        "plan": plan_name,
        "upgrade": upgrade
    }