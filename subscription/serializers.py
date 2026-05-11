from rest_framework import serializers
from .models import SubscriptionPlan
from django.db import connection


class SubscriptionPlanSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubscriptionPlan
        fields = "__all__"
        read_only_fields = ["id"]
    
    def create(self, validated_data):
        """Custom create method to handle raw SQL insert for managed=False model"""
        try:
            from django.db import transaction
            
            # Extract all fields with proper type conversion
            name = str(validated_data.get("name", "")).strip()
            price = int(validated_data.get("price", 0))
            duration_days = int(validated_data.get("duration_days", 0))
            plan_type = str(validated_data.get("plan_type", "user")).strip()
            is_active = bool(validated_data.get("is_active", True))
            
            appointment_allowed = bool(validated_data.get("appointment_allowed", False))
            ai_diet_allowed = bool(validated_data.get("ai_diet_allowed", False))
            weight_tracker_allowed = bool(validated_data.get("weight_tracker_allowed", False))
            nutrition_search_allowed = bool(validated_data.get("nutrition_search_allowed", False))
            custom_reminder_allowed = bool(validated_data.get("custom_reminder_allowed", False))
            chat_allowed = bool(validated_data.get("chat_allowed", False))
            
            inhouse_consults = int(validated_data.get("inhouse_consults", 0))
            expert_consults = int(validated_data.get("expert_consults", 0))
            
            Fat_Calculator_allowed = bool(validated_data.get("Fat_Calculator_allowed", False))
            BMI_Calculator_allowed = bool(validated_data.get("BMI_Calculator_allowed", False))
            meal_log_allowed = bool(validated_data.get("meal_log_allowed", False))
            water_intake_allowed = bool(validated_data.get("water_intake_allowed", False))
            
            expert_consultation_fee = int(validated_data.get("expert_consultation_fee", 0))
            inhouse_consultation_fee = int(validated_data.get("inhouse_consultation_fee", 0))
            
            # Validate required fields
            if not name:
                raise serializers.ValidationError("Plan name is required")
            if price < 0:
                raise serializers.ValidationError("Price cannot be negative")
            if duration_days <= 0:
                raise serializers.ValidationError("Duration must be greater than 0")
            
            # Use transaction to ensure atomicity
            with transaction.atomic():
                # Insert using raw SQL with quoted identifiers for PostgreSQL
                with connection.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO subscriptions_plan 
                        (name, price, duration_days, plan_type, is_active, 
                         appointment_allowed, ai_diet_allowed, weight_tracker_allowed, 
                         nutrition_search_allowed, custom_reminder_allowed, chat_allowed,
                         inhouse_consults, expert_consults, "Fat_Calculator_allowed",
                         "BMI_Calculator_allowed", meal_log_allowed, water_intake_allowed,
                         expert_consultation_fee, inhouse_consultation_fee)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        [name, price, duration_days, plan_type, is_active,
                         appointment_allowed, ai_diet_allowed, weight_tracker_allowed,
                         nutrition_search_allowed, custom_reminder_allowed, chat_allowed,
                         inhouse_consults, expert_consults, Fat_Calculator_allowed,
                         BMI_Calculator_allowed, meal_log_allowed, water_intake_allowed,
                         expert_consultation_fee, inhouse_consultation_fee]
                    )
                
                # Fetch the created plan by name (most recent)
                plan = SubscriptionPlan.objects.filter(name=name).order_by('-id').first()
                
                if not plan:
                    raise serializers.ValidationError("Failed to create plan - could not retrieve from database")
                
                return plan
            
        except serializers.ValidationError:
            raise
        except Exception as e:
            import traceback
            error_msg = f"Failed to create plan: {str(e)}"
            print("SERIALIZER CREATE ERROR:", traceback.format_exc())
            raise serializers.ValidationError(error_msg)