from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from users.models import UserProfile
from .serializers import UserSerializer, UserWriteSerializer
from django.core.paginator import Paginator, EmptyPage

class UserListCreateView(APIView):

    @swagger_auto_schema(
        operation_description="Get all users with search, filters and pagination",
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('role', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('email', openapi.IN_QUERY, type=openapi.TYPE_STRING),

        ],
        responses={200: UserSerializer(many=True)}
    )
    def get(self, request):

        search = request.query_params.get('search')
        role = request.query_params.get('role')
        status_filter = request.query_params.get('status')
        email = request.query_params.get('email')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        users = UserProfile.objects.all()

        # search by id or name
        # search by id, name, email, city
        if search:
          users = users.filter(
            Q(id__icontains=search) |
            Q(full_name__icontains=search) |
            Q(email__icontains=search) |
            Q(city__icontains=search)
        )
        # role filter
        if role:
            users = users.filter(role__iexact=role)

        # status filter
        if status_filter:
            if status_filter.lower() == "active":
                users = users.filter(is_active=True)
            elif status_filter.lower() == "inactive":
                users = users.filter(is_active=False)

        paginator = Paginator(users, page_size)

        try:
            users_page = paginator.page(page)
        except EmptyPage:
            return Response({
                "total": paginator.count,
                "page": page,
                "page_size": page_size,
                "results": []
            })

        serializer = UserSerializer(users_page, many=True)

        return Response({
            "total": paginator.count,
            "page": page,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "results": serializer.data
        })

class UserDetailView(APIView):

    def get_object(self, pk):
        try:
            return UserProfile.objects.get(pk=pk)
        except UserProfile.DoesNotExist:
            return None


    def get(self, request, pk):

        user = self.get_object(pk)

        if not user:
            return Response({'error': 'User not found'}, status=404)

        return Response(UserSerializer(user).data)


    @swagger_auto_schema(
        operation_description="Update user",
        request_body=UserWriteSerializer
    )
    def put(self, request, pk):

        user = self.get_object(pk)

        if not user:
            return Response({'error': 'User not found'}, status=404)

        serializer = UserWriteSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'User updated successfully'})

        return Response(serializer.errors, status=400)


    @swagger_auto_schema(
        operation_description="Partial update user",
        request_body=UserWriteSerializer
    )
    def patch(self, request, pk):

        user = self.get_object(pk)

        if not user:
            return Response({'error': 'User not found'}, status=404)

        serializer = UserWriteSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'User partially updated successfully'})

        return Response(serializer.errors, status=400)


    def delete(self, request, pk):

        user = self.get_object(pk)

        if not user:
            return Response({'error': 'User not found'}, status=404)

        user.delete()
        return Response({'message': 'User deleted successfully'})


class UserStatusView(APIView):

    @swagger_auto_schema(
        operation_description="Update user status",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_BOOLEAN)
            }
        )
    )
    def patch(self, request, pk):

        try:
            user = UserProfile.objects.get(pk=pk)

            user.is_active = request.data.get('status', user.is_active)
            user.save()

            return Response({'message': 'Status updated'})

        except UserProfile.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)


class DashboardStatsView(APIView):

    def get(self, request):

        total_users = UserProfile.objects.count()
        active_users = UserProfile.objects.filter(is_active=True).count()
        inactive_users = UserProfile.objects.filter(is_active=False).count()

        return Response({
            "totalUsers": total_users,
            "activeUsers": active_users,
            "inactiveUsers": inactive_users
        })