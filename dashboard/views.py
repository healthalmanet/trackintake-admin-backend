<<<<<<< HEAD
from psycopg2 import OperationalError
=======
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
<<<<<<< HEAD
from dashboard.models import UserPro
from django.contrib.auth import get_user_model
from users.models import UserProfile
from subscription.models import SubscriptionPayment, UserSubscription
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

=======

from users.models import UserProfile
from subscription.models import SubscriptionPayment, UserSubscription


#  TOTAL USERS

class TotalUsersAPI(APIView):

    def get(self, request):
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
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


<<<<<<< HEAD
# ---------------- ACTIVE USERS ----------------

class ActiveUsersAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get count of active users",
        responses={200: openapi.Response('Active users count')}
    )
    def get(self, request):

=======
#  ACTIVE USERS 

class ActiveUsersAPI(APIView):

    def get(self, request):
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
        date = request.GET.get("date")
        month = request.GET.get("month")
        year = request.GET.get("year")

        users = UserProfile.objects.filter(is_active=True)

        if date:
            users = users.filter(date_joined__date=date)
        elif month and year:
<<<<<<< HEAD
            users = users.filter(date_joined__month=int(month), date_joined__year=int(year))
        elif year:
            users = users.filter(date_joined__year=int(year))
=======
            users = users.filter(date_joined__month=month, date_joined__year=year)
        elif year:
            users = users.filter(date_joined__year=year)
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c

        return Response({
            "activeUsers": users.count()
        })


<<<<<<< HEAD

# ---------------- TOTAL REVENUE ----------------
=======
# TOTAL REVENUE -
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c

class TotalRevenueAPI(APIView):

    @swagger_auto_schema(
<<<<<<< HEAD
        operation_description="Get total revenue with optional filtering by date, month, year or date range",
=======
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
        manual_parameters=[
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Specific date (YYYY-MM-DD)",
<<<<<<< HEAD
                type=openapi.TYPE_STRING,
                required=False
=======
                type=openapi.TYPE_STRING
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
            ),
            openapi.Parameter(
                'month',
                openapi.IN_QUERY,
                description="Month number (1-12)",
<<<<<<< HEAD
                type=openapi.TYPE_INTEGER,
                required=False
=======
                type=openapi.TYPE_INTEGER
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description="Year (YYYY)",
<<<<<<< HEAD
                type=openapi.TYPE_INTEGER,
                required=False
=======
                type=openapi.TYPE_INTEGER
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
            ),
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description="Start date (YYYY-MM-DD)",
<<<<<<< HEAD
                type=openapi.TYPE_STRING,
                required=False
=======
                type=openapi.TYPE_STRING
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description="End date (YYYY-MM-DD)",
<<<<<<< HEAD
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={200: openapi.Response('Total revenue')}
=======
                type=openapi.TYPE_STRING
            ),
        ]
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
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
<<<<<<< HEAD
#print(SubscriptionPayment.objects.filter(status="success").count())    
# ---------------- PENDING APPOINTMENTS ----------------

class PendingAppointmentsAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get count of pending appointments",
        responses={200: openapi.Response('Pending appointments count')}
    )
=======

# PENDING APPOINTMENTS 

class PendingAppointmentsAPI(APIView):

>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
    def get(self, request):

        return Response({
            "pendingAppointments": 0
        })


<<<<<<< HEAD
# ---------------- USER GROWTH ----------------

class UserGrowthAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get user growth data over time",
        responses={200: openapi.Response('User growth statistics')}
    )
=======
#  USER GROWTH 

class UserGrowthAPI(APIView):

>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
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


<<<<<<< HEAD
# ---------------- PLAN DISTRIBUTION ----------------

class PlanDistributionAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get distribution of subscription plans among users",
        responses={200: openapi.Response('Plan distribution data')}
    )
=======
#  PLAN DISTRIBUTION 

class PlanDistributionAPI(APIView):

>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
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


<<<<<<< HEAD
# ---------------- RECENT ACTIVITY ----------------

class RecentActivityAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get recent user activity (signups and subscriptions)",
        responses={200: openapi.Response('Recent activity data')}
    )
=======
#  RECENT ACTIVITY 

class RecentActivityAPI(APIView):

>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
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


<<<<<<< HEAD
# ---------------- REVENUE BY PLAN ----------------

class RevenueByPlanAPI(APIView):

    @swagger_auto_schema(
        operation_description="Get revenue breakdown by subscription plan",
        responses={200: openapi.Response('Revenue by plan data')}
    )
=======
# REVENUE BY PLAN 

class RevenueByPlanAPI(APIView):

>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
    def get(self, request):

        revenue = list(
            SubscriptionPayment.objects
            .filter(status="success")
            .values("plan_id")
            .annotate(total_revenue=Sum("amount"))
            .order_by("-total_revenue")
        )

        return Response({
            "revenueByPlan": revenue
        })
        
        
class RevenueDetailsAPI(APIView):

<<<<<<< HEAD
    @swagger_auto_schema(
        operation_description="Get detailed payment records",
        responses={200: openapi.Response('Payment details')}
    )
=======
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
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
<<<<<<< HEAD
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
=======
        })        
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
