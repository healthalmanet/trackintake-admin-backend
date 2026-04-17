from django.db import models
from users.models import UserProfile


class NutritionistProfile(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    nutritionist_type = models.CharField(max_length=100, default='general')
    is_virtual_enabled = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = 'nutritionist_nutritionistprofile'
        managed = False


class PatientAssignment(models.Model):
    nutritionist_id = models.IntegerField()  # FK to user_user.id (nutritionist's user ID)
    patient_id = models.IntegerField()  # FK to user_user.id (patient's user ID)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nutritionist_patientassignment'
        managed = False