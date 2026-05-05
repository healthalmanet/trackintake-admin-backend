from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q, Count
from django.db.models.functions import Lower
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from subscription.models import SubscriptionPayment, UserSubscription, SubscriptionPlan
from users.models import UserProfile, UserHealthProfile
from notifications.models import Notification
from .serializers import AssignNutritionistSerializer, UserSerializer, UserWriteSerializer
from django.core.paginator import Paginator, EmptyPage
from django.db import connection
from django.db.utils import OperationalError
from nutritionist.models import NutritionistProfile, PatientAssignment
from django.utils.timezone import now
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import UserProfile
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes





User = get_user_model()
def check_db_connection():
    """Check if database is connected"""
    try:
        connection.ensure_connection()
        print("Database connection successful")
        return True
    except OperationalError:
        return False





# ====================================================================ASSIGNED NUTRITIONIST======================================================================#                 
class AssignNutritionistAPI(APIView):
    @swagger_auto_schema(
    operation_description="Assign a nutritionist to a user",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "user_id": openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="ID of the user"
            ),
            "nutritionist_id": openapi.Schema(  # ✔ fixed
                type=openapi.TYPE_INTEGER,
                description="ID of the nutritionist"
            )
        },
        required=["user_id", "nutritionist_id"]  # ✔ fixed
    ),
    responses={
        200: 'Nutritionist assigned successfully',
        400: 'Validation error',
        404: 'User or nutritionist not found',
        500: 'Error assigning nutritionist'
    }
)

    def post(self, request):
        try:
            user_id = request.data.get("user_id")
            nutritionist_id = request.data.get("nutritionist_id")

            if not user_id or not nutritionist_id:
                return Response({"error": "user_id and nutritionist_id are required"}, status=status.HTTP_400_BAD_REQUEST)

            if int(user_id) == int(nutritionist_id):
                return Response({"error": "User and nutritionist cannot be same"}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch patient (UserProfile)
            patient = UserProfile.objects.filter(id=user_id).first()
            if not patient:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            # Fetch nutritionist UserProfile
            nutritionist_user = UserProfile.objects.filter(id=nutritionist_id).first()
            if not nutritionist_user:
                return Response({"error": "Nutritionist not found"}, status=status.HTTP_404_NOT_FOUND)

            if nutritionist_user.role.lower() != "nutritionist":
                return Response({"error": "Selected user is not a nutritionist"}, status=status.HTTP_400_BAD_REQUEST)

            # Get the NutritionistProfile for this user
            nutritionist_profile = NutritionistProfile.objects.filter(user_id=nutritionist_id).first()
            if not nutritionist_profile:
                return Response({"error": "Nutritionist profile not found"}, status=status.HTTP_404_NOT_FOUND)

            with transaction.atomic():
                # Prevent duplicate assignment
                already = PatientAssignment.objects.filter(
                    nutritionist_id=nutritionist_id,
                    patient_id=user_id
                ).exists()
                if already:
                    return Response({"error": "Patient already assigned to this nutritionist"}, status=status.HTTP_400_BAD_REQUEST)

                PatientAssignment.objects.create(
                    nutritionist_id=nutritionist_id,
                    patient_id=user_id
                )

                # Create notifications for admin, user, and nutritionist
                # Admin notification
                Notification.objects.create(
                    user=None,
                    type="admin",
                    message=f"Nutritionist {nutritionist_user.full_name} has been assigned to patient {patient.full_name}."
                )
                
                # User notification
                Notification.objects.create(
                    user=patient,
                    type="user",
                    message=f"Nutritionist {nutritionist_user.full_name} has been assigned to you."
                )
                
                # Nutritionist notification
                Notification.objects.create(
                    user=nutritionist_user,
                    type="nutritionist",
                    message=f"You have been assigned to patient {patient.full_name}."
                )

            return Response({
                "message": "Nutritionist assigned successfully",
                "data": {"user_id": patient.id, "nutritionist_id": nutritionist_user.id}
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            print("ASSIGN ERROR:", traceback.format_exc())
            return Response({"error": str(e), "message": "Something went wrong while assigning nutritionist"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
#=====================================================================================NUTRITIONIST LIST WITH PATIENT COUNT======================================================================#            
class NutritionistListAPIView(APIView):
    @swagger_auto_schema(
          operation_summary="Nutritionist List",
        operation_description="Get all nutritionists with patient count",
        responses={200: "Success"}
    )
    def get(self, request):
        nutritionists = NutritionistProfile.objects.all()

        data = []
        for n in nutritionists:
            user = UserProfile.objects.filter(id=n.user_id).first()
            patient_count = PatientAssignment.objects.filter(nutritionist_id=n.user_id).count()
            data.append({
                "id": n.id,
                "user_id": n.user_id,
                "user_name": user.full_name if user else f"User #{n.user_id}",
                "email": user.email if user else None,
                "nutritionist_type": n.nutritionist_type,
                "is_virtual_enabled": n.is_virtual_enabled,
                "is_verified": n.is_verified,
                "patient_count": patient_count
            })

        return Response({
            "success": True,
            "data": data
        })

#=====================================================================================USERS WITH PAYMENT BUT NO PROFILE======================================================================#
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
            
            # Get all user IDs that have a health profile (userProfile_userprofile table)
            existing_user_ids = set(
                uid for uid in UserHealthProfile.objects.values_list('user_id', flat=True) if uid is not None
            )
            
            # Get payment user IDs
            payment_user_ids = set(payments_query.values_list('user_id', flat=True))
            
            # Find users with payments but no profile
            missing_user_ids = payment_user_ids - existing_user_ids

            # Get all payments for missing users
            user_payments = payments_query.filter(
                user_id__in=missing_user_ids
            ).values('user_id', 'amount', 'plan_id', 'status', 'created_at').order_by('-created_at')

            # Enrich with user names
            user_map = {u.id: u.full_name for u in UserProfile.objects.filter(id__in=missing_user_ids)}
            enriched = []
            for p in user_payments:
                enriched.append({
                    "user_id": p['user_id'],
                    "user_name": user_map.get(p['user_id'], f"User #{p['user_id']}"),
                    "plan_id": p['plan_id'],
                    "amount": p['amount'],
                    "status": p['status'],
                    "created_at": p['created_at'],
                })

            return Response({
                "count": len(enriched),
                "status_filter": status_filter or "all",
                "total_missing_users": len(missing_user_ids),
                "missing_user_ids": sorted([uid for uid in missing_user_ids if uid is not None]),
                "users_data": enriched
            })
        except Exception as e:
            return Response({
                "error": str(e),
                "message": "Error retrieving payment data"
            }, status=500)

#============================user detail view with full CRUD operations====================================================================#
class UserDetailView(APIView):

    @swagger_auto_schema(
        operation_description="Retrieve a specific user by ID",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_PATH,
                description='User ID',
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response('User details', UserSerializer),
            404: 'User not found'
        }
    )
    def get(self, request, user_id):
        """Retrieve a specific user by ID"""
        try:
            if not check_db_connection():
                return Response({
                    "error": "Database connection failed"
                }, status=503)
                
            user = UserProfile.objects.get(id=user_id)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        except Exception as e:
            return Response({
                "error": str(e),
                "message": "Error retrieving user"
            }, status=500)

    @swagger_auto_schema(
        operation_description="Update a user (full update)",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_PATH,
                description='User ID',
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        request_body=UserWriteSerializer,
        responses={
            200: openapi.Response('User updated successfully', UserSerializer),
            400: 'Validation error',
            404: 'User not found'
        }
    )
    def put(self, request, user_id):
        """Update a user (full update)"""
        try:
            if not check_db_connection():
                return Response({
                    "error": "Database connection failed"
                }, status=503)
                
            user = UserProfile.objects.get(id=user_id)
            serializer = UserWriteSerializer(user, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "message": "User updated successfully",
                    "data": UserSerializer(user).data
                })
            return Response(serializer.errors, status=400)
        except UserProfile.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        except Exception as e:
            return Response({
                "error": str(e),
                "message": "Error updating user"
            }, status=500)

    @swagger_auto_schema(
        operation_description="Partially update a user",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_PATH,
                description='User ID',
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        request_body=UserWriteSerializer,
        responses={
            200: openapi.Response('User updated successfully', UserSerializer),
            400: 'Validation error',
            404: 'User not found'
        }
    )
    def patch(self, request, user_id):
        """Partially update a user"""
        try:
            if not check_db_connection():
                return Response({
                    "error": "Database connection failed"
                }, status=503)
                
            user = UserProfile.objects.get(id=user_id)
            serializer = UserWriteSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "message": "User updated successfully",
                    "data": UserSerializer(user).data
                })
            return Response(serializer.errors, status=400)
        except UserProfile.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        except Exception as e:
            return Response({
                "error": str(e),
                "message": "Error updating user"
            }, status=500)

    @swagger_auto_schema(
        operation_description="Delete a user",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_PATH,
                description='User ID',
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: 'User deleted successfully',
            404: 'User not found'
        }
    )
    def delete(self, request, user_id):
        """Delete a user"""
        try:
            if not check_db_connection():
                return Response({
                    "error": "Database connection failed"
                }, status=503)
                
            user = UserProfile.objects.get(id=user_id)
            user.delete()
            return Response({"message": "User deleted successfully"})
        except UserProfile.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        except Exception as e:
            return Response({
                "error": str(e),
                "message": "Error deleting user"
            }, status=500)
            
# ==========================================================================USER PLAN RENEWAL & UPDATE NOTIFICATION====================================================================#

class UserPlanNotificationAPI(APIView):

    @swagger_auto_schema(
        operation_description="Notify users about plan renewal and upgrade",
        responses={
            200: "Notifications sent successfully",
            500: "Error sending notifications"
        }
    )
    def get(self, request):
        try:
            today = timezone.now().date()
            upcoming_date = today + timedelta(days=3)

            expiring_soon = UserSubscription.objects.filter(
                end_date__range=[today, upcoming_date]
            )
            expired = UserSubscription.objects.filter(
                end_date__lt=today
            )

            notified_users = set()
            admins = UserProfile.objects.filter(role__iexact="admin")

            # Expiring soon
            for sub in expiring_soon:
                user = UserProfile.objects.filter(id=sub.user_id).first()
                user_name = user.full_name if user else f"User #{sub.user_id}"

                Notification.objects.get_or_create(
                    user_id=sub.user_id,
                    type="user",
                    message="⚠️ Your plan will expire soon. Upgrade your plan now to continue uninterrupted services."
                )
                
                # for admin in admins:
                #     Notification.objects.get_or_create(
                #         user=admin,
                #         type="admin",
                #         message=f"⚠️ {user_name}'s plan is expiring in 3 days. Please follow up."
                #         )
                notified_users.add(sub.user_id)
                

            # Expired
            for sub in expired:
                user = UserProfile.objects.filter(id=sub.user_id).first()
                user_name = user.full_name if user else f"User #{sub.user_id}"

                Notification.objects.get_or_create(
                    user_id=sub.user_id,
                    type="user",
                    message="❌ Your plan has expired. Please renew or upgrade your plan to regain access."
                )
                for admin in admins:
                    Notification.objects.get_or_create(
                        user=admin,
                        type="admin",
                        message=f"❌ {user_name}'s plan has expired. Please follow up."
                        )
                notified_users.add(sub.user_id)
                
            return Response({
                "message": "Notifications sent successfully",
                "total_users_notified": len(notified_users),
                "users": list(notified_users)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "error": str(e),
                "message": "Something went wrong while sending notifications"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            
            
# ==========================================================================USER LOGIN POST MESSAGE TO ADMIN====================================================================#
    


class UserHealthProfileAPI(APIView):

    @swagger_auto_schema(
        operation_summary="Get User Health Profile",
        operation_description="Fetch user health profile by user ID",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_PATH,
                description='User ID',
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: "User health profile fetched successfully",
            404: "Health profile not found"
        },
        tags=["users"]
    )
    def get(self, request, user_id):
        try:
            profile = UserHealthProfile.objects.filter(user_id=user_id).first()
            if not profile:
                return Response({"error": "Health profile not found"}, status=404)

            return Response({
                "user_id": profile.user_id,
                "date_of_birth": profile.date_of_birth,
                "country": profile.country,
                "mobile_number": profile.mobile_number,
                "gender": profile.gender,
                "occupation": profile.occupation,
                "height_cm": profile.height_cm,
                "weight_kg": profile.weight_kg,
                "activity_level": profile.activity_level,
                "goal": profile.goal,
                "diet_type": profile.diet_type,
                "allergies": profile.allergies,
                "is_diabetic": profile.is_diabetic,
                "is_hypertensive": profile.is_hypertensive,
                "has_heart_condition": profile.has_heart_condition,
                "has_thyroid_disorder": profile.has_thyroid_disorder,
                "has_arthritis": profile.has_arthritis,
                "has_gastric_issues": profile.has_gastric_issues,
                "other_chronic_condition": profile.other_chronic_condition,
                "family_history": profile.family_history,
                "due_date": profile.due_date,
                "is_breastfeeding": profile.is_breastfeeding,
                "is_pregnant": profile.is_pregnant,
                "city": profile.city,
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class SubscribedUsersAPI(APIView):

    @swagger_auto_schema(
        operation_summary="Get Subscribed Users",
        operation_description="Fetch all users who have successful subscription payments",
        responses={
            200: UserSerializer(many=True)
        },
        tags=["users"]
    )
    def get(self, request):
        try:
            paid_user_ids = set(
                SubscriptionPayment.objects.filter(
                    status="success"
                ).values_list('user_id', flat=True)
            )

            users = UserProfile.objects.filter(
                id__in=paid_user_ids
            ).order_by("full_name")

            serializer = UserSerializer(users, many=True)

            return Response({
                "results": serializer.data
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class UserListCreateView(APIView):

    @swagger_auto_schema(
        operation_description="List all users",
        responses={200: openapi.Response('List of users', UserSerializer(many=True))}
    )
    def get(self, request):
        try:
            if not check_db_connection():
                return Response({"error": "Database connection failed"}, status=503)

            search = request.query_params.get("search", "")
            role = request.query_params.get("role", "")
            status_filter = request.query_params.get("status", "")
            date_filter = request.query_params.get("date", "")
            month_filter = request.query_params.get("month", "")
            year_filter = request.query_params.get("year", "")
            city_filter = request.query_params.get("city", "")
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))

            users = UserProfile.objects.all().order_by("-date_joined")

            if search:
                users = users.filter(Q(full_name__icontains=search) | Q(email__icontains=search))
            if role:
                users = users.filter(role__iexact=role)
            if status_filter == "active":
                users = users.filter(is_active=True)
            elif status_filter == "inactive":
                users = users.filter(is_active=False)
            if date_filter:
                users = users.filter(date_joined__date=date_filter)
            elif month_filter and year_filter:
                users = users.filter(date_joined__month=month_filter, date_joined__year=year_filter)
            elif year_filter:
                users = users.filter(date_joined__year=year_filter)
            if city_filter:
                city_user_ids = UserHealthProfile.objects.filter(
                    city__icontains=city_filter
                ).values_list('user_id', flat=True)
                users = users.filter(id__in=city_user_ids)

            country_filter = request.query_params.get("country", "")
            if country_filter:
                country_user_ids = UserHealthProfile.objects.filter(
                    country__icontains=country_filter
                ).values_list('user_id', flat=True)
                users = users.filter(id__in=country_user_ids)

            total = users.count()
            start = (page - 1) * page_size
            user_list = list(users[start:start + page_size])

            result = []
            for u in user_list:
                try:
                    hp = UserHealthProfile.objects.filter(user_id=u.id).first()
                    city = hp.city if hp else None
                except Exception:
                    city = None

                # Get active subscription plan
                try:
                    from subscription.models import UserSubscription, SubscriptionPlan
                    sub = UserSubscription.objects.filter(user_id=u.id, is_active=True).first()
                    plan_name = None
                    if sub:
                        plan = SubscriptionPlan.objects.filter(id=sub.plan_id).first()
                        plan_name = plan.name if plan else None
                except Exception:
                    plan_name = None

                result.append({
                    "id": u.id,
                    "full_name": u.full_name,
                    "email": u.email,
                    "role": u.role,
                    "plan": plan_name,
                    "city": city,
                    "is_active": u.is_active,
                    "date_joined": u.date_joined,
                })

            return Response({
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
                "results": result
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @swagger_auto_schema(
        operation_description="Create a new user",
        request_body=UserWriteSerializer,
        responses={
            201: openapi.Response('User created successfully', UserSerializer),
            400: 'Validation error',
            503: 'Database connection error'
        }
    )
    def post(self, request):
        try:
            # DB check
            if not check_db_connection():
                return Response({
                    "error": "Database connection failed",
                    "message": "Unable to connect to the database"
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            #  Serializer
            serializer = UserWriteSerializer(data=request.data)

            if not serializer.is_valid():
                return Response({
                    "error": "Validation failed",
                    "details": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            #  Save user
            user = serializer.save()

            #  Admin Notification
            try:
                Notification.objects.create(
                    user=None, 
                    type="admin",
                    message=f"New user {user.full_name} registered. Please assign a nutritionist."
                    )
            except Exception as e:
                print(f"Admin notification error: {e}")

            #  WebSocket Notification
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "notifications",
                    {
                        "type": "send_notification",
                        "message": f"New user {user.full_name} created 🚀"
                    }
                )
            except Exception as e:
                print(f"WebSocket error: {e}")

            #  Response
            return Response({
                "message": "User created successfully",
                "data": UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "error": str(e),
                "message": "Error creating user"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



#==========================================AVAILABLE NUTRITIONISTS FOR PATIENT===========================================#

PLAN_NUTRITIONIST_MAP = {
    'free': [],
    'basic': ['inhouse', 'expert'],
    'silver': ['inhouse', 'expert'],
    'premium': ['inhouse', 'expert'],
    'hero': ['inhouse', 'expert'],
    'nutritionist full access': ['inhouse', 'expert'],
}

class AvailableNutritionistsView(APIView):

    @swagger_auto_schema(
        operation_summary="Get available nutritionists for a patient",
        operation_description="""
        Patient ke subscription plan ke basis par available nutritionists return karta hai.

        **Plan Rules:**
        - basic → Inhouse Expert only
        - silver → Expert only
        - premium → Both Inhouse Expert + Expert

        Saare nutritionists ka plan hero hota hai.
        """,
        manual_parameters=[
            openapi.Parameter(
                name='patient_id',
                in_=openapi.IN_QUERY,
                description="Patient ka User ID",
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: openapi.Response(
                description="Available nutritionists list",
                examples={
                    "application/json": {
                        "patient_id": 2,
                        "patient_plan": "basic",
                        "allowed_nutritionist_types": ["inhouse_expert"],
                        "total": 1,
                        "nutritionists": [
                            {
                                "id": 3,
                                "full_name": "Dr. Abhay",
                                "email": "nutritionist@gmail.com",
                                "nutritionist_type": "inhouse_expert",
                                "plan": "hero"
                            }
                        ]
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request",
                examples={
                    "application/json": {
                        "error": "patient_id is required."
                    }
                }
            ),
            404: openapi.Response(
                description="Patient Not Found",
                examples={
                    "application/json": {
                        "error": "Patient not found."
                    }
                }
            ),
        },
        tags=["users"]
    )
    def get(self, request):
        patient_id = request.query_params.get('patient_id')

        if not patient_id:
            return Response({"error": "patient_id is required."}, status=400)

        try:
            patient = UserProfile.objects.get(id=patient_id, role='user')
        except UserProfile.DoesNotExist:
            return Response({"error": "Patient not found."}, status=404)

        # 🔥 Plan fetch (IMPORTANT)
        from subscription.models import UserSubscription, SubscriptionPlan

# Get active subscription
        subscription = UserSubscription.objects.filter(
            user_id=patient.id,
            is_active=True
        ).first()

        if not subscription:
            return Response({"error": "No active subscription"}, status=400)

        plan = SubscriptionPlan.objects.filter(id=subscription.plan_id).first()
        if not plan:
            return Response({"error": "Plan not found"}, status=400)

        patient_plan = plan.name.lower().strip()
        if not patient_plan:
            return Response({"error": "Patient ka koi plan assign nahi hai."}, status=400)
        

        allowed_types = PLAN_NUTRITIONIST_MAP.get(patient_plan)

        if allowed_types is None:
            return Response({
                "error": f"Invalid plan '{patient_plan}'"
            }, status=400)

        # ✅ MAIN FILTER
        nutritionists = UserProfile.objects.filter(
            role='nutritionist',
            nutritionist_type__in=allowed_types,
            is_active=True
        ).values(
            'id', 'full_name', 'email', 'nutritionist_type'
        )

        return Response({
            "patient_id": int(patient_id),
            "patient_plan": patient_plan,
            "allowed_nutritionist_types": allowed_types,
            "total": nutritionists.count(),
            "nutritionists": list(nutritionists)
        })



#==========================================ELIGIBLE USERS FOR NUTRITIONIST ASSIGNMENT===========================================#

class EligibleUsersForNutritionistAPI(APIView):
    """
    Get users eligible for nutritionist assignment based on:
    1. User has a subscription (purchased a plan)
    2. User is not already assigned to a nutritionist
    3. Filter by nutritionist type (inhouse_expert or expert)
    """

    @swagger_auto_schema(
        operation_summary="Get eligible users for nutritionist assignment",
        operation_description="""
        Returns users who:
        - Have purchased a subscription plan
        - Are not already assigned to a nutritionist
        - Match the nutritionist type based on their plan
        
        Query Parameters:
        - nutritionist_type: 'inhouse_expert' or 'expert' (optional, returns all if not specified)
        """,
        manual_parameters=[
            openapi.Parameter(
                name='nutritionist_type',
                in_=openapi.IN_QUERY,
                description="Filter by nutritionist type: 'inhouse_expert' or 'expert'",
                type=openapi.TYPE_STRING,
                required=False
            )
        ],
        responses={
            200: openapi.Response('List of eligible users'),
            400: 'Invalid nutritionist type'
        }
    )
    def get(self, request):
        try:
            nutritionist_type = request.query_params.get('nutritionist_type', '').lower().strip()
            
            # Get all users with subscriptions (active or not, just need to have purchased)
            all_subscriptions = UserSubscription.objects.all().values_list('user_id', 'plan_id')
            
            user_ids_with_plans = [sub[0] for sub in all_subscriptions]
            plan_ids = {sub[0]: sub[1] for sub in all_subscriptions}
            
            print(f"[DEBUG] Total users with subscriptions: {len(user_ids_with_plans)}")
            
            # Get all users with subscriptions
            users_with_plans = UserProfile.objects.filter(
                id__in=user_ids_with_plans,
                role='user',
                is_active=True
            )
            
            print(f"[DEBUG] Active users with subscriptions: {users_with_plans.count()}")
            
            # Get already assigned users
            assigned_users = PatientAssignment.objects.all().values_list('patient_id', flat=True)
            
            print(f"[DEBUG] Already assigned users: {len(assigned_users)}")
            
            # Filter out already assigned users
            eligible_users = users_with_plans.exclude(id__in=assigned_users)
            
            print(f"[DEBUG] Eligible users (not assigned): {eligible_users.count()}")
            
            # Build response with plan information
            result = []
            for user in eligible_users:
                plan_id = plan_ids.get(user.id)
                plan = SubscriptionPlan.objects.filter(id=plan_id).first()
                
                if not plan:
                    print(f"[DEBUG] Plan not found for user {user.id}, plan_id: {plan_id}")
                    continue
                
                plan_name = plan.name.lower().strip()
                allowed_types = list(PLAN_NUTRITIONIST_MAP.get(plan_name, []))
                
                # If plan not found in map, try to infer from inhouse_consults and expert_consults
                if not allowed_types:
                    if plan.inhouse_consults > 0:
                        allowed_types.append('inhouse')
                    if plan.expert_consults > 0:
                        allowed_types.append('expert')
                
                print(f"[DEBUG] User {user.id} ({user.full_name}): plan_obj.name={plan.name}, plan_name={plan_name}, inhouse={plan.inhouse_consults}, expert={plan.expert_consults}, allowed_types={allowed_types}")
                
                # Filter by nutritionist type if specified
                if nutritionist_type:
                    if nutritionist_type not in allowed_types:
                        print(f"[DEBUG] User {user.id} filtered out: {nutritionist_type} not in {allowed_types}")
                        continue
                    user_allowed_types = [nutritionist_type]
                else:
                    user_allowed_types = allowed_types
                
                subscription = UserSubscription.objects.filter(
                    user_id=user.id,
                    plan_id=plan_id
                ).first()
                
                result.append({
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'plan_name': plan_name,
                    'plan_id': plan_id,
                    'allowed_nutritionist_types': user_allowed_types,
                    'subscription_end_date': subscription.end_date if subscription else None
                })
            
            print(f"[DEBUG] Final result count: {len(result)}")
            
            return Response({
                'total': len(result),
                'nutritionist_type_filter': nutritionist_type or 'all',
                'users': result
            })
            
        except Exception as e:
            import traceback
            print(f"[ERROR] {str(e)}")
            print(traceback.format_exc())
            return Response({
                'error': str(e),
                'total': 0,
                'users': []
            }, status=status.HTTP_400_BAD_REQUEST)



#==========================================DEBUG ENDPOINT FOR SUBSCRIPTIONS===========================================#

class DebugSubscriptionsAPI(APIView):
    """Debug endpoint to check subscriptions and assignments"""
    
    def get(self, request):
        try:
            from subscription.models import UserSubscription, SubscriptionPlan
            
            total_users = UserProfile.objects.filter(role='user').count()
            total_subscriptions = UserSubscription.objects.count()
            
            # Try to get assignments - handle if table doesn't exist
            try:
                from nutritionist.models import PatientAssignment
                total_assignments = PatientAssignment.objects.count()
            except:
                total_assignments = 0
            
            # Get sample subscriptions
            sample_subs = UserSubscription.objects.all()[:5]
            subs_data = []
            for sub in sample_subs:
                user = UserProfile.objects.filter(id=sub.user_id).first()
                plan = SubscriptionPlan.objects.filter(id=sub.plan_id).first()
                
                # Check if assigned
                try:
                    from nutritionist.models import PatientAssignment
                    assigned = PatientAssignment.objects.filter(patient_id=sub.user_id).exists()
                except:
                    assigned = False
                
                subs_data.append({
                    'user_id': sub.user_id,
                    'user_name': user.full_name if user else 'Unknown',
                    'plan_id': sub.plan_id,
                    'plan_name': plan.name if plan else 'Unknown',
                    'plan_inhouse': plan.inhouse_consults if plan else 0,
                    'plan_expert': plan.expert_consults if plan else 0,
                    'is_active': sub.is_active,
                    'end_date': str(sub.end_date),
                    'already_assigned': assigned
                })
            
            return Response({
                'total_users': total_users,
                'total_subscriptions': total_subscriptions,
                'total_active_assignments': total_assignments,
                'sample_subscriptions': subs_data
            })
        except Exception as e:
            import traceback
            return Response({
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=400)


# ===================== PASSWORD RESET REQUEST ===================== #
@csrf_exempt
def forgot_password(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    email = data.get("email", "").strip()
    if not email:
        return JsonResponse({"error": "Email is required"}, status=400)

    user = User.objects.filter(email__iexact=email).first()

    if not user:
        return JsonResponse({"message": "If this email exists, a reset link has been sent"})

    uid   = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    reset_link = f"http://127.0.0.1:8000/api/users/reset-password/{uid}/{token}/"

    # Copy this from Django console and paste into Postman
    print(f"\n✅ RESET LINK: {reset_link}\n")
    print(f"   UID:   {uid}")
    print(f"   TOKEN: {token}\n")

    return JsonResponse({
        "message": "Reset link sent",
        # ⚠️ Remove this in production — only for local testing
        "debug_uid":   uid,
        "debug_token": token,
        "debug_reset_link": reset_link
    })


# ===================== PASSWORD RESET ===================== #
@csrf_exempt
def reset_password(request, uidb64, token):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    password = data.get("password", "").strip()
    if not password:
        return JsonResponse({"error": "Password is required"}, status=400)

    # Decode UID
    try:
        uid  = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        return JsonResponse({"error": "Invalid user"}, status=400)

    # Validate token
    if not default_token_generator.check_token(user, token):
        return JsonResponse({"error": "Invalid or expired token"}, status=400)

    # Set new password
    user.set_password(password)
    user.save()

    return JsonResponse({"message": "Password reset successful"})