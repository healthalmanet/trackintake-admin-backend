from django.db import models

class UserProfile(models.Model):

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_user"   # existing table name
        managed = False

    def __str__(self):
        return self.full_name   