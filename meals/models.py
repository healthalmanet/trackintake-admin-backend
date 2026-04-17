from django.db import models


class Meal(models.Model):

    CATEGORY_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner")
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

    class Meta:
        managed = False
        db_table = 'meals_meal'