from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
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
    def get(self, request):
        plans = SubscriptionPlan.objects.all()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)

    # Create new plan
    @swagger_auto_schema(request_body=SubscriptionPlanSerializer)
    def post(self, request):

        serializer = SubscriptionPlanSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  UPDATE PLAN 

class UpdateSubscriptionPlanAPI(APIView):

    @swagger_auto_schema(request_body=SubscriptionPlanSerializer)
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
    
class SubscriptionUsageAPI(APIView):

    def get(self, request):

        search = request.query_params.get("search")
        plan_filter = request.query_params.get("plan")
        status_filter = request.query_params.get("status")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        subs = UserSubscription.objects.all()

        data = []

        for sub in subs:

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

            data.append({
                "user_id": sub.user_id,
                "plan_id": sub.plan_id,
                "start_date": sub.start_date,
                "end_date": sub.end_date,
                "status": status
            })

        return Response({
            "plans": data
        })        