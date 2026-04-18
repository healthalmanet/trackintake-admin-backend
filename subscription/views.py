from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
<<<<<<< HEAD
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
=======
from subscription.models import SubscriptionPayment
from .models import SubscriptionPlan,UserSubscription
from .serializers import SubscriptionPlanSerializer
from django.db.models import F, Sum, Count 
from users.models import UserProfile
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
#  GET ALL PLANS + CREATE PLAN 

class SubscriptionPlanAPI(APIView):

    # Get all plans
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
    def get(self, request):
        plans = SubscriptionPlan.objects.all()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)

<<<<<<< HEAD
    @swagger_auto_schema(
        operation_description="Create a new subscription plan",
        request_body=SubscriptionPlanSerializer,
        responses={
            201: openapi.Response('Plan created successfully', SubscriptionPlanSerializer),
            400: 'Validation error'
        }
    )
=======
    # Create new plan
    @swagger_auto_schema(request_body=SubscriptionPlanSerializer)
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
    def post(self, request):

        serializer = SubscriptionPlanSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


<<<<<<< HEAD
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
=======
#  UPDATE PLAN 

class UpdateSubscriptionPlanAPI(APIView):

    @swagger_auto_schema(request_body=SubscriptionPlanSerializer)
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
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
<<<<<<< HEAD


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
=======
    
class SubscriptionUsageAPI(APIView):

    def get(self, request):

        search = request.query_params.get("search")
        plan_filter = request.query_params.get("plan")
        status_filter = request.query_params.get("status")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
        subs = UserSubscription.objects.all()

        data = []

        for sub in subs:

<<<<<<< HEAD
            if sub.end_date < today:
                status = "expired"
            elif sub.end_date <= today + timedelta(days=3):
                status = "expiring_soon"
            else:
                status = "active"
=======
            user = UserProfile.objects.filter(id=sub.user_id).first()
            plan = SubscriptionPlan.objects.filter(id=sub.plan_id).first()

            payment = SubscriptionPayment.objects.filter(
                user_id=sub.user_id,
                plan_id=sub.plan_id
            ).first()

            record = {
                "user_name": user.full_name if user else None,
                "email": user.email if user else None,
                "plan_name": plan.name if plan else None,
                "payment_id": payment.razorpay_payment_id if payment else None,
                "payment_status": payment.status if payment else "free",
                "payment_date": payment.created_at if payment else sub.start_date,
                "start_date": sub.start_date,
                "end_date": sub.end_date
            }

            data.append(record)

        #  SEARCH 
        if search:
            data = [
                d for d in data
                if search.lower() in (d["user_name"] or "").lower()
                or search.lower() in (d["email"] or "").lower()
            ]

        # PLAN FILTER 
        if plan_filter:
            data = [
                d for d in data
                if d["plan_name"] and d["plan_name"].lower() == plan_filter.lower()
            ]

        # STATUS FILTER 
        if status_filter:
            data = [
                d for d in data
                if d["payment_status"] and d["payment_status"].lower() == status_filter.lower()
            ]

        #  DATE FILTER 
        date_filter = request.query_params.get("date")
        month_filter = request.query_params.get("month")
        year_filter = request.query_params.get("year")
        
        if date_filter:
            data = [d for d in data if str(d["payment_date"])[:10] == date_filter]
        elif month_filter and year_filter:
            data = [d for d in data if str(d["payment_date"])[5:7] == str(month_filter).zfill(2) and str(d["payment_date"])[:4] == str(year_filter)]
        elif year_filter:
            data = [d for d in data if str(d["payment_date"])[:4] == str(year_filter)]
            
        if start_date:
            data = [d for d in data if str(d["start_date"])[:10] >= start_date]

        if end_date:
            data = [d for d in data if str(d["start_date"])[:10] <= end_date]

        #  PAGINATION 
        paginator = Paginator(data, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            "total": paginator.count,
            "page": page,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "results": list(page_obj)
        })
        
class PaymentAnalyticsAPI(APIView):

    def get(self, request):

        filter_type = request.query_params.get("filter")  # date / week / month
        plan = request.query_params.get("plan")
        spec_date = request.query_params.get("date")
        spec_month = request.query_params.get("month")
        spec_year = request.query_params.get("year")

        payments = SubscriptionPayment.objects.all()

        #  DATE FILTER 

        today = timezone.now().date()

        if spec_date:
            payments = payments.filter(created_at__date=spec_date)
        elif spec_month and spec_year:
            payments = payments.filter(created_at__month=spec_month, created_at__year=spec_year)
        elif spec_year:
            payments = payments.filter(created_at__year=spec_year)
        else:
            if filter_type == "date":
                payments = payments.filter(created_at__date=today)
            elif filter_type == "week":
                start_week = today - timedelta(days=7)
                payments = payments.filter(created_at__date__gte=start_week)
            elif filter_type == "month":
                payments = payments.filter(created_at__month=today.month)

        #  PLAN FILTER 

        if plan:
            payments = payments.filter(plan_id=plan)

        #  METRICS 

        total_payments = payments.count()

        total_revenue = payments.filter(
            status="success"
        ).aggregate(total=Sum("amount"))["total"] or 0

        success = payments.filter(status="success").count()
        failed = payments.filter(status="failed").count()

        revenue_by_plan = list(
            payments.filter(status="success")
            .values("plan_id")
            .annotate(revenue=Sum("amount"))
        )

        return Response({
            "totalPayments": total_payments,
            "totalRevenue": total_revenue,
            "successPayments": success,
            "failedPayments": failed,
            "revenuePerPlan": revenue_by_plan
        })
        
class PlanDurationTrackingAPI(APIView):

    def get(self, request):

        today = timezone.now().date()

        subs = UserSubscription.objects.all()

        data = []

        for sub in subs:

            status = "active"

            if sub.end_date < today:
                status = "expired"

            elif sub.end_date <= today + timedelta(days=3):
                status = "expiring_soon"
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c

            data.append({
                "user_id": sub.user_id,
                "plan_id": sub.plan_id,
<<<<<<< HEAD
                "status": status
            })

        return Response(data)
=======
                "start_date": sub.start_date,
                "end_date": sub.end_date,
                "status": status
            })

        return Response({
            "plans": data
        })        
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
