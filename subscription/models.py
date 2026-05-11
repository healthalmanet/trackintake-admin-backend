from django.db import models

class SubscriptionPlan(models.Model):
    PLAN_TYPE_CHOICES = (
        ("user", "User"),
        ("nutritionist", "Nutritionist"),
    )

    name = models.CharField(max_length=100)
    price = models.IntegerField()
    duration_days = models.IntegerField()

    Fat_Calculator_allowed = models.BooleanField(default=False)
    appointment_allowed = models.BooleanField(default=False)
    ai_diet_allowed = models.BooleanField(default=False)
    BMI_Calculator_allowed = models.BooleanField(default=False)

    inhouse_consults = models.IntegerField(default=0)
    expert_consults = models.IntegerField(default=0)

    meal_log_allowed = models.BooleanField(default=False)
    water_intake_allowed = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES)

    weight_tracker_allowed = models.BooleanField(default=False)
    nutrition_search_allowed = models.BooleanField(default=False)
    custom_reminder_allowed = models.BooleanField(default=False)
    chat_allowed = models.BooleanField(default=False)

    expert_consultation_fee = models.IntegerField(default=0)
    inhouse_consultation_fee = models.IntegerField(default=0)

    class Meta:
        db_table = "subscriptions_plan"
        managed = False

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    id = models.BigAutoField(primary_key=True)

    user_id = models.IntegerField()
    plan_id = models.IntegerField()

    start_date = models.DateField()
    end_date = models.DateField()

    remaining_inhouse = models.IntegerField(default=0)
    remaining_expert = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField()

    class Meta:
        db_table = "subscriptions_usersubscription"
        managed = False

    def __str__(self):
        return f"User {self.user_id} - Plan {self.plan_id}"


class SubscriptionPayment(models.Model):
    user_id = models.BigIntegerField()
    plan_id = models.BigIntegerField()

    amount = models.IntegerField()

    status = models.CharField(max_length=20)   # success / failed

    created_at = models.DateTimeField()

    class Meta:
        db_table = "subscriptions_payment"
        managed = False
