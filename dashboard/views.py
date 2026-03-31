from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from users.models import UserProfile
from subscription.models import SubscriptionPayment, UserSubscription


# ---------------- TOTAL USERS ----------------

class TotalUsersAPI(APIView):

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

    def get(self, request):
        date = request.GET.get("date")
        month = request.GET.get("month")
        year = request.GET.get("year")

        users = UserProfile.objects.filter(is_active=True)

        if date:
            users = users.filter(date_joined__date=date)
        elif month and year:
            users = users.filter(date_joined__month=month, date_joined__year=year)
        elif year:
            users = users.filter(date_joined__year=year)

        return Response({
            "activeUsers": users.count()
        })


# ---------------- TOTAL REVENUE ----------------

class TotalRevenueAPI(APIView):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Specific date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'month',
                openapi.IN_QUERY,
                description="Month number (1-12)",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description="Year (YYYY)",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description="Start date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description="End date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING
            ),
        ]
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

# ---------------- PENDING APPOINTMENTS ----------------

class PendingAppointmentsAPI(APIView):

    def get(self, request):

        return Response({
            "pendingAppointments": 0
        })


# ---------------- USER GROWTH ----------------

class UserGrowthAPI(APIView):

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