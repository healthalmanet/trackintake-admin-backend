from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()


class UserProfile(models.Model):
    NUTRITIONIST_TYPE_CHOICES = [
        ('inhouse_expert', 'Inhouse Expert'),
        ('expert', 'Expert'),
    ]

    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('silver', 'Silver'),
        ('premium', 'Premium'),
        ('hero', 'Hero'),  # nutritionist plan
    ]

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False) 
    is_superuser = models.BooleanField(default=False)

    # Patient ka plan (basic/silver/premium)
    # Nutritionist ka plan (hero)
    plan = models.CharField(max_length=100, null=True, blank=True, choices=PLAN_CHOICES)

    # Sirf nutritionists ke liye (patients ke liye NULL rahega)
    nutritionist_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=NUTRITIONIST_TYPE_CHOICES
    )

    class Meta:
        db_table = "user_user"
        managed = False

    def __str__(self):
        return self.full_name


class UserHealthProfile(models.Model):
    user_id = models.BigIntegerField()
    date_of_birth = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    occupation = models.CharField(max_length=100, null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    activity_level = models.CharField(max_length=50, null=True, blank=True)
    goal = models.CharField(max_length=20, null=True, blank=True)
    diet_type = models.CharField(max_length=20, null=True, blank=True)
    allergies = models.TextField(null=True, blank=True)
    is_diabetic = models.BooleanField(default=False)
    is_hypertensive = models.BooleanField(default=False)
    has_heart_condition = models.BooleanField(default=False)
    has_thyroid_disorder = models.BooleanField(default=False)
    has_arthritis = models.BooleanField(default=False)
    has_gastric_issues = models.BooleanField(default=False)
    other_chronic_condition = models.TextField(null=True, blank=True)
    family_history = models.TextField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_breastfeeding = models.BooleanField(default=False)
    is_pregnant = models.BooleanField(default=False)
    city = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = '"userProfile_userprofile"'
        managed = False


