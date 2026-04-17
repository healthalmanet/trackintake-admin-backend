from django.db.models.signals import post_save
from django.dispatch import receiver

from subscription.models import SubscriptionPayment
from notifications.models import Notification

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


@receiver(post_save, sender=SubscriptionPayment)
def payment_notification(sender, instance, created, **kwargs):

    if created and instance.status.lower() == "success":

        Notification.objects.create(
            message=f"User {instance.user_id} purchased plan {instance.plan_id}"
        )

        # real-time send
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            "notifications",
            {
                "type": "send_notification",
                "data": {
                    "title": "Plan Purchased",
                    "message": f"User {instance.user_id} purchased plan"
                }
            }
        )