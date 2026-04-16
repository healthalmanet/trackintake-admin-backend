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
    nutritionist = models.ForeignKey(
        NutritionistProfile,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    patient = models.ForeignKey(UserProfile, on_delete=models.CASCADE)

    class Meta:
        db_table = 'nutritionist_patientassignment'
        managed = False