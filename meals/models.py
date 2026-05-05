from django.db import models


class Meal(models.Model):

    CATEGORY_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
        ("snacks", "Snacks")
    ]

    meal_name = models.CharField(max_length=255)

    calories = models.IntegerField()
    protein = models.FloatField()
    carbohydrates = models.FloatField()
    fat = models.FloatField()

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.meal_name
  

class DietRecommendation(models.Model):
    for_week_starting = models.DateField()
    meals = models.JSONField()
    status = models.CharField(max_length=50)
    nutritionist_comment = models.TextField(null=True, blank=True)
    user_profile_snapshot = models.JSONField(null=True, blank=True)
    original_ai_plan = models.JSONField(null=True, blank=True)
    approved_for_retraining = models.BooleanField(default=False)
    nutritionist_retraining_notes = models.TextField(null=True, blank=True)
    was_used_for_retraining = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    reviewed_by_id = models.IntegerField(null=True, blank=True)
    user_id = models.IntegerField()
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "diet_dietrecommendation"
        managed = False
