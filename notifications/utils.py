"""
Notification utilities for creating dynamic notifications
Works with existing database schema (no new columns)
"""
from .models import Notification


def create_notification(message, notification_type='admin', user_id=None):
    """
    Create a notification dynamically using existing fields only
    
    Args:
        message: Notification message (includes title and details)
        notification_type: 'admin', 'user', or 'nutritionist'
        user_id: User ID (optional)
    
    Returns:
        Notification object
    """
    notification = Notification.objects.create(
        message=message,
        type=notification_type,
        is_read=False,
    )
    return notification


def create_registration_notification(user_name):
    """Create a notification for new user registration"""
    return create_notification(
        message=f"New User Registration\n{user_name} registered a new account.",
        notification_type='admin'
    )


def create_plan_purchase_notification(user_name, plan_name, payment_id):
    """Create a notification for plan purchase"""
    return create_notification(
        message=f"Plan Purchased\n{user_name} purchased {plan_name} (ID: {payment_id}).",
        notification_type='admin'
    )


def create_assignment_notification(user_name, nutritionist_name, specialization):
    """Create a notification for nutritionist assignment"""
    return create_notification(
        message=f"Nutritionist Assigned\n{nutritionist_name} assigned to {user_name} for {specialization}.",
        notification_type='admin'
    )


def create_expiry_notification(user_name, plan_name, days_remaining):
    """Create a notification for plan expiry"""
    return create_notification(
        message=f"Plan Expiry Alert\n{user_name}'s {plan_name} expires in {days_remaining} days.",
        notification_type='admin'
    )


def create_assignment_request_notification(user_name):
    """Create a notification requesting nutritionist assignment"""
    return create_notification(
        message=f"Nutritionist Assignment Needed\nPlease assign a nutritionist to {user_name}.",
        notification_type='admin'
    )
