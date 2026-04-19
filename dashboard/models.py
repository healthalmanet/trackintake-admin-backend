from django.db import models
from django.contrib.auth import get_user_model
User=get_user_model()

class UserPro(models.Model):

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "userProfile_userprofile"
        managed = False

    def __str__(self):
        return self.full_name
    
    
