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

    # ✅ Save notification
    Notification.objects.create(
        user_id=payment.user_id,
        message=f"Payment received from user {payment.user_id} 💳"
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


# --------- USAGE API ---------
class SubscriptionUsageAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get subscription usage details for all users",
        responses={200: openapi.Response('Subscription usage details')}
    )
    def get(self, request):

        subs = UserSubscription.objects.all()
        data = []

        for sub in subs:

            user = UserProfile.objects.filter(id=sub.user_id).first()
            plan = SubscriptionPlan.objects.filter(id=sub.plan_id).first()

            payment = SubscriptionPayment.objects.filter(
                user_id=sub.user_id,
                plan_id=sub.plan_id
            ).first()

            # Only include users who have an actual payment (not free)
            if not payment or payment.status not in ["success", "failed", "pending"]:
                continue

            data.append({
                "user_name": user.full_name if user else None,
                "email": user.email if user else None,
                "plan_name": plan.name if plan else None,
                "payment_status": payment.status,
                "start_date": sub.start_date,
                "end_date": sub.end_date
            })

        return Response(data)


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

        return Response({
            "totalPayments": total_payments,
            "totalRevenue": total_revenue,
            "successPayments": payments.filter(status="success").count(),
            "failedPayments": payments.filter(status="failed").count(),
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