from django.db import models
from users.models import UserProfile


class NutritionistProfile(models.Model):

    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE
    )

    nutritionist_type = models.CharField(
        max_length=100,
        default='general'
    )

    is_virtual_enabled = models.BooleanField(default=False)

    is_verified = models.BooleanField(default=False)

    # NEW FIELDS
    experience_years = models.IntegerField(
        null=True,
        blank=True
    )

    degree = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    license_number = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    certificate = models.FileField(
        upload_to='nutritionist_certificates/',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'nutritionist_nutritionistprofile'
        managed = False


class PatientAssignment(models.Model):

    nutritionist_id = models.IntegerField()  # FK to user_user.id

    patient_id = models.IntegerField()  # FK to user_user.id

    assigned_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = 'nutritionist_patientassignment'
        managed = False