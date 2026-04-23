from psycopg2 import OperationalError
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from dashboard.models import UserPro
from django.contrib.auth import get_user_model
from users.models import UserProfile
from subscription.models import SubscriptionPayment, UserSubscription, SubscriptionPlan
from django.db import connection
User=get_user_model()
def check_db_connection():
    """Check if database is connected"""
    try:
        connection.ensure_connection()
        print("Database connection successful")
        return True
    except OperationalError:
        return False
# ---------------- TOTAL USERS ----------------

class TotalUsersAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get total count of users",
        responses={200: openapi.Response('Total users count')}
    )
    def get(self, request):

        date = request.GET.get("date")
        month = request.GET.get("month")
        year = request.GET.get("year")

        users = UserProfile.objects.all()

        if date:
            users = users.filter(date_joined__date=date)
        elif month and year:
            users = users.filter(date_joined__month=month, date_joined__year=year)
        elif year:
            users = users.filter(date_joined__year=year)

        return Response({
            "totalUsers": users.count()
        })


# ---------------- ACTIVE USERS ----------------

class ActiveUsersAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get count of active users",
        responses={200: openapi.Response('Active users count')}
    )
    def get(self, request):

        date = request.GET.get("date")
        month = request.GET.get("month")
        year = request.GET.get("year")

        users = UserProfile.objects.filter(is_active=True)

        if date:
            users = users.filter(date_joined__date=date)
        elif month and year:
            users = users.filter(date_joined__month=int(month), date_joined__year=int(year))
        elif year:
            users = users.filter(date_joined__year=int(year))

        return Response({
            "activeUsers": users.count()
        })



# ---------------- TOTAL REVENUE ----------------

class TotalRevenueAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get total revenue with optional filtering by date, month, year or date range",
        manual_parameters=[
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Specific date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'month',
                openapi.IN_QUERY,
                description="Month number (1-12)",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description="Year (YYYY)",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description="Start date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description="End date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={200: openapi.Response('Total revenue')}
    )
    def get(self, request):

        date = request.GET.get("date")
        month = request.GET.get("month")
        year = request.GET.get("year")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        payments = SubscriptionPayment.objects.filter(status="success")

        if date:
            payments = payments.filter(created_at__date=date)

        elif month and year:
            payments = payments.filter(
                created_at__month=month,
                created_at__year=year
            )

        elif year:
            payments = payments.filter(created_at__year=year)

        elif start_date and end_date:
            payments = payments.filter(
                created_at__date__range=[start_date, end_date]
            )

        total_revenue = payments.aggregate(
            total=Sum("amount")
        )["total"] or 0

        return Response({
            "totalRevenue": total_revenue
        })
#print(SubscriptionPayment.objects.filter(status="success").count())    
# ---------------- PENDING APPOINTMENTS ----------------

class PendingAppointmentsAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get count of pending appointments",
        responses={200: openapi.Response('Pending appointments count')}
    )
    def get(self, request):

        return Response({
            "pendingAppointments": 0
        })


# ---------------- USER GROWTH ----------------

class UserGrowthAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get user growth data over time",
        responses={200: openapi.Response('User growth statistics')}
    )
    def get(self, request):

        user_growth = list(
            UserProfile.objects
            .annotate(date=TruncDate("date_joined"))
            .values("date")
            .annotate(users=Count("id"))
            .order_by("date")
        )

        return Response({
            "userGrowth": user_growth
        })


# ---------------- PLAN DISTRIBUTION ----------------

class PlanDistributionAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get distribution of subscription plans among users",
        responses={200: openapi.Response('Plan distribution data')}
    )
    def get(self, request):

        plans = list(
            SubscriptionPayment.objects
            .filter(status="success")
            .values("plan_id")
            .annotate(users=Count("user_id"))
            .order_by("-users")
        )

        return Response({
            "planDistribution": plans
        })


# ---------------- RECENT ACTIVITY ----------------

class RecentActivityAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get recent user activity (signups and subscriptions)",
        responses={200: openapi.Response('Recent activity data')}
    )
    def get(self, request):

        recent_signups = list(
            UserProfile.objects
            .order_by("-date_joined")[:5]
            .values("id", "full_name", "email", "date_joined")
        )

        for user in recent_signups:
            user["activity"] = "User signed up"

        recent_subscriptions = list(
            UserSubscription.objects
            .order_by("-created_at")[:5]
            .values("user_id", "plan_id", "created_at")
        )

        for sub in recent_subscriptions:
            sub["activity"] = "User purchased subscription"

        return Response({
            "recentSignups": recent_signups,
            "recentSubscriptions": recent_subscriptions
        })


# ---------------- REVENUE BY PLAN ----------------

class RevenueByPlanAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get revenue breakdown by subscription plan",
        responses={200: openapi.Response('Revenue by plan data')}
    )
    def get(self, request):

        revenue_data = list(
            SubscriptionPayment.objects
            .filter(status="success")
            .values("plan_id")
            .annotate(total_revenue=Sum("amount"))
            .order_by("-total_revenue")
        )

        # Add plan names to the response
        for item in revenue_data:
            plan = SubscriptionPlan.objects.filter(id=item["plan_id"]).first()
            item["plan_name"] = plan.name if plan else f"Plan {item['plan_id']}"

        return Response({
            "revenueByPlan": revenue_data
        })
        
        
class RevenueDetailsAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get detailed payment records",
        responses={200: openapi.Response('Payment details')}
    )
    def get(self, request):

        payments = SubscriptionPayment.objects.filter(
            status="success"
        ).values(
            "id",
            "user_id",
            "plan_id",
            "amount",
            "created_at"
        ).order_by("-created_at")

        return Response({
            "payments": list(payments)
        })        
        
        
class UsersWithPaymentNoProfileAPI(APIView):

    @swagger_auto_schema(
        operation_description="Find users who have made payments but don't have a profile",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description='Filter by payment status (success/failed)', type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: openapi.Response('List of users with payment details')}
    )
    def get(self, request):
        try:
            if not check_db_connection():
                return Response({
                    "error": "Database connection failed"
                }, status=503)

            status_filter = request.query_params.get('status')

            # Get all payments
            payments_query = SubscriptionPayment.objects.all()
            if status_filter:
                payments_query = payments_query.filter(status=status_filter)
            
            # Get all user profiles
            existing_user_ids = set(UserPro.objects.values_list('id', flat=True))
            
            # Get payment user IDs
            payment_user_ids = set(payments_query.values_list('user_id', flat=True))
            
            # Find users with payments but no profile
            missing_user_ids = payment_user_ids - existing_user_ids

            # Get all payments for missing users
            user_payments = payments_query.filter(
                user_id__in=missing_user_ids
            ).values('user_id', 'amount', 'plan_id', 'status', 'created_at').order_by('-created_at')

            return Response({
                "count": len(list(user_payments)),
                "status_filter": status_filter or "all",
                "total_missing_users": len(missing_user_ids),
                "missing_user_ids": sorted(list(missing_user_ids)),
                "users_data": list(user_payments)
            })
        except Exception as e:
            return Response({
                "error": str(e),
                "message": "Error retrieving payment data"
            }, status=500)
