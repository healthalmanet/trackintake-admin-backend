from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from subscription.models import SubscriptionPayment
from .models import SubscriptionPlan, UserSubscription
from .serializers import SubscriptionPlanSerializer
from django.db.models import Sum
from users.models import UserProfile
from notifications.models import Notification
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from .utils import get_user_plan_and_upgrade
from django.contrib.auth.decorators import login_required

# ✅ WebSocket imports
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


# --------- USER PLAN CHECK ---------
@login_required
def get_subscription_plan(request):
    data = get_user_plan_and_upgrade(request.user.id)

    return JsonResponse({
        "status": True,
        "plan": data["plan"],
        "upgrade": data["upgrade"]
    })


# --------- GET ALL PLANS + CREATE PLAN ---------
class SubscriptionPlanAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get all subscription plans",
        responses={200: openapi.Response('List of subscription plans', SubscriptionPlanSerializer(many=True))}
    )
    def get(self, request):
        plans = SubscriptionPlan.objects.all()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Create a new subscription plan",
        request_body=SubscriptionPlanSerializer,
        responses={
            201: openapi.Response('Plan created successfully', SubscriptionPlanSerializer),
            400: 'Validation error'
        }
    )
    def post(self, request):

        serializer = SubscriptionPlanSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --------- UPDATE PLAN ---------
class UpdateSubscriptionPlanAPI(APIView):

    @swagger_auto_schema(
        operation_description="Update a subscription plan",
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description='Plan ID', type=openapi.TYPE_INTEGER, required=True)
        ],
        request_body=SubscriptionPlanSerializer,
        responses={
            200: openapi.Response('Plan updated successfully', SubscriptionPlanSerializer),
            400: 'Validation error',
            404: 'Plan not found'
        }
    )
    def put(self, request, pk):

        try:
            plan = SubscriptionPlan.objects.get(id=pk)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Plan not found"}, status=404)

        serializer = SubscriptionPlanSerializer(
            plan,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Plan updated successfully",
                "data": serializer.data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --------- PAYMENT SUCCESS HANDLER (🔥 IMPORTANT) ---------
def handle_payment_success(payment):

    # ✅ Save notification for admin
    Notification.objects.create(
        user=None,
        type="admin",
        message=f"User purchased a plan. Payment ID: {payment.id}, Amount: {payment.amount}"
    )

    # ✅ Save notification for user
    user = UserProfile.objects.filter(id=payment.user_id).first()
    if user:
        plan = SubscriptionPlan.objects.filter(id=payment.plan_id).first()
        plan_name = plan.name if plan else f"Plan #{payment.plan_id}"
        Notification.objects.create(
            user=user,
            type="user",
            message=f"Your payment for {plan_name} plan has been processed successfully."
        )

    # ✅ Real-time WebSocket notification
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        "notifications",
        {
            "type": "send_notification",
            "message": f"Payment received from user {payment.user_id} 💳"
        }
    )


# --------- CREATE PAYMENT ---------
class CreatePaymentAPI(APIView):
    @swagger_auto_schema(
        operation_description="Create a payment for a subscription plan",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="User ID"),
                "plan_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Plan ID"),
                "amount": openapi.Schema(type=openapi.TYPE_INTEGER, description="Payment amount"),
                "status": openapi.Schema(type=openapi.TYPE_STRING, description="Payment status (success/failed)", default="success"),
            },
            required=["user_id", "plan_id", "amount"]
        ),
        responses={
            201: 'Payment created successfully',
            400: 'Validation error',
            404: 'User or plan not found'
        }
    )
    def post(self, request):
        try:
            user_id = request.data.get("user_id")
            plan_id = request.data.get("plan_id")
            amount = request.data.get("amount")
            payment_status = request.data.get("status", "success")

            if not user_id or not plan_id or not amount:
                return Response({"error": "user_id, plan_id, and amount are required"}, status=status.HTTP_400_BAD_REQUEST)

            # Verify user exists
            user = UserProfile.objects.filter(id=user_id).first()
            if not user:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            # Verify plan exists
            plan = SubscriptionPlan.objects.filter(id=plan_id).first()
            if not plan:
                return Response({"error": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)

            # Create payment using raw SQL to handle razorpay_order_id
            from django.db import connection
            import uuid
            
            razorpay_order_id = f"order_{uuid.uuid4().hex[:12]}"
            
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO subscriptions_payment 
                    (user_id, plan_id, amount, status, created_at, razorpay_order_id) 
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    [user_id, plan_id, amount, payment_status, timezone.now(), razorpay_order_id]
                )
            
            # Fetch the created payment
            payment = SubscriptionPayment.objects.filter(
                user_id=user_id,
                plan_id=plan_id,
                amount=amount
            ).order_by('-created_at').first()

            # Create subscription if payment is successful
            if payment_status == "success":
                start_date = timezone.now().date()
                end_date = start_date + timedelta(days=plan.duration_days)
                
                UserSubscription.objects.create(
                    user_id=user_id,
                    plan_id=plan_id,
                    start_date=start_date,
                    end_date=end_date,
                    remaining_inhouse=plan.inhouse_consults,
                    remaining_expert=plan.expert_consults,
                    is_active=True,
                    created_at=timezone.now()
                )
                
                # Send notifications
                handle_payment_success(payment)

            return Response({
                "message": "Payment created successfully",
                "data": {
                    "payment_id": payment.id,
                    "user_id": user_id,
                    "plan_id": plan_id,
                    "amount": amount,
                    "status": payment_status
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            print("PAYMENT ERROR:", traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --------- USAGE API ---------
class SubscriptionUsageAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get subscription usage details for all users",
        responses={200: openapi.Response('Subscription usage details')}
    )
    def get(self, request):
        try:
            payments = SubscriptionPayment.objects.all().order_by("-created_at")

            date = request.query_params.get("date")
            month = request.query_params.get("month")
            year = request.query_params.get("year")

            if date:
                payments = payments.filter(created_at__date=date)
            elif month and year:
                payments = payments.filter(created_at__month=month, created_at__year=year)
            elif year:
                payments = payments.filter(created_at__year=year)

            status_filter = request.query_params.get("status")
            if status_filter and status_filter != "all":
                payments = payments.filter(status=status_filter)

            search = request.query_params.get("search", "").strip()
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))

            all_data = []
            for payment in payments:
                user = UserProfile.objects.filter(id=payment.user_id).first()
                user_name = user.full_name if user else f"User #{payment.user_id}"
                email = user.email if user else ""

                if search:
                    q = search.lower()
                    if q not in user_name.lower() and q not in email.lower():
                        continue

                plan = SubscriptionPlan.objects.filter(id=payment.plan_id).first()
                sub = UserSubscription.objects.filter(
                    user_id=payment.user_id,
                    plan_id=payment.plan_id
                ).first()

                all_data.append({
                    "user_name": user_name,
                    "email": email,
                    "plan_name": plan.name if plan else f"Plan #{payment.plan_id}",
                    "payment_id": payment.id,
                    "payment_status": payment.status,
                    "start_date": sub.start_date if sub else None,
                    "end_date": sub.end_date if sub else None,
                })

            total = len(all_data)
            start = (page - 1) * page_size
            paginated = all_data[start:start + page_size]

            return Response({
                "results": paginated,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": max(1, (total + page_size - 1) // page_size),
            })
        except Exception as e:
            return Response({"error": str(e), "results": [], "total": 0, "page": 1, "page_size": 10, "total_pages": 1}, status=500)


# --------- PAYMENT ANALYTICS ---------
class PaymentAnalyticsAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get payment analytics summary",
        responses={200: openapi.Response('Payment analytics data')}
    )
    def get(self, request):

        month = request.query_params.get("month")
        year = request.query_params.get("year")
        date = request.query_params.get("date")

        payments = SubscriptionPayment.objects.all()

        if date:
            payments = payments.filter(created_at__date=date)
        elif month and year:
            payments = payments.filter(created_at__month=month, created_at__year=year)
        elif year:
            payments = payments.filter(created_at__year=year)

        total_payments = payments.count()
        total_revenue = payments.filter(status="success").aggregate(total=Sum("amount"))["total"] or 0

        # Revenue per plan
        from django.db.models import Sum as _Sum
        revenue_per_plan_qs = (
            payments.filter(status="success")
            .values("plan_id")
            .annotate(revenue=_Sum("amount"))
        )
        revenue_per_plan = [{"plan_id": r["plan_id"], "revenue": r["revenue"]} for r in revenue_per_plan_qs]

        return Response({
            "totalPayments": total_payments,
            "totalRevenue": total_revenue,
            "successPayments": payments.filter(status="success").count(),
            "failedPayments": payments.filter(status="failed").count(),
            "revenuePerPlan": revenue_per_plan,
        })


# --------- PLAN STATUS ---------
class PlanDurationTrackingAPI(APIView):

    def get(self, request):

        today = timezone.now().date()
        subs = UserSubscription.objects.all()

        data = []

        for sub in subs:

            if sub.end_date < today:
                status = "expired"
            elif sub.end_date <= today + timedelta(days=3):
                status = "expiring_soon"
            else:
                status = "active"

            data.append({
                "user_id": sub.user_id,
                "plan_id": sub.plan_id,
                "status": status
            })

        return Response(data)
