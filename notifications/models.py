from django.db import models
from users.models import UserProfile

class Notification(models.Model):
    TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
        ('nutritionist', 'Nutritionist'),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='admin')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_notifications"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.message[:50]} - {self.type}"