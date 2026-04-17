from django.db.models.signals import post_save
from django.dispatch import receiver

from users.models import UserProfile
from notifications.models import Notification

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


@receiver(post_save, sender=UserProfile)
def create_user_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            message=f"{instance.full_name} registered"
        )

        # -------- REAL-TIME SEND --------
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            "notifications",
            {
                "type": "send_notification",
                "data": {
                    "title": "New User Created",
                    "message": f"{instance.full_name} registered"
                }
            }
        )