from rest_framework import serializers


class SubscriptionPlanSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True, required=False)
    name = serializers.CharField(required=True)
    price = serializers.IntegerField(required=True)
    duration_days = serializers.IntegerField(required=True)
    plan_type = serializers.CharField(default="patient")
    is_active = serializers.BooleanField(default=True)

    # Patient features
    appointment_allowed = serializers.BooleanField(default=False)
    ai_diet_allowed = serializers.BooleanField(default=False)
    weight_tracker_allowed = serializers.BooleanField(default=False)
    nutrition_search_allowed = serializers.BooleanField(default=False)
    custom_reminder_allowed = serializers.BooleanField(default=False)
    chat_allowed = serializers.BooleanField(default=False)
    Fat_Calculator_allowed = serializers.BooleanField(default=False)
    BMI_Calculator_allowed = serializers.BooleanField(default=False)
    meal_log_allowed = serializers.BooleanField(default=False)
    water_intake_allowed = serializers.BooleanField(default=False)

    inhouse_consults = serializers.IntegerField(default=0)
    expert_consults = serializers.IntegerField(default=0)
    expert_consultation_fee = serializers.IntegerField(default=0)
    inhouse_consultation_fee = serializers.IntegerField(default=0)

    # Nutritionist features
    nutri_ai_diet_allowed = serializers.BooleanField(default=False)
    nutri_manual_diet_allowed = serializers.BooleanField(default=False)
    nutri_bulk_upload_allowed = serializers.BooleanField(default=False)
    nutri_lab_reports_allowed = serializers.BooleanField(default=False)
    nutri_smart_assistant_allowed = serializers.BooleanField(default=False)
    nutri_online_appointment_allowed = serializers.BooleanField(default=False)
    nutri_offline_appointment_allowed = serializers.BooleanField(default=False)
    nutri_chat_allowed = serializers.BooleanField(default=False)
    nutri_export_reports_allowed = serializers.BooleanField(default=False)
    nutri_max_patients = serializers.IntegerField(default=0)


class PaymentDetailSerializer(serializers.Serializer):
    """Serializer for payment records with customer, plan, and gateway info"""
    payment_id = serializers.IntegerField(source='id')
    user_name = serializers.CharField(allow_null=True, required=False)
    email = serializers.CharField(allow_null=True, required=False)
    plan_name = serializers.CharField(allow_null=True, required=False)
    payment_status = serializers.CharField(source='status')
    amount = serializers.IntegerField(default=0)
    razorpay_order_id = serializers.CharField(allow_null=True, required=False)
    razorpay_payment_id = serializers.CharField(allow_null=True, required=False)
    pending_email = serializers.CharField(allow_null=True, required=False)
    payment_type = serializers.CharField(allow_null=True, required=False)
    created_at = serializers.DateTimeField(allow_null=True, required=False)
    start_date = serializers.CharField(allow_null=True, required=False)
    end_date = serializers.CharField(allow_null=True, required=False)
