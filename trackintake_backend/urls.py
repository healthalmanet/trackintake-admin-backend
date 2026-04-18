from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


# Home route
def home(request):
    return HttpResponse("Django Backend Running")


# Swagger schema configuration
schema_view = get_schema_view(
    openapi.Info(
        title="TrackIntake API",
        default_version='v1',
        description="Swagger documentation for TrackIntake Backend",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('admin/', admin.site.urls),

    # Home
    path('', home, name='home'),

    # Users API
    path('api/users/', include('users.urls')),
<<<<<<< HEAD
    
=======
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c

    # Swagger Docs
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0),
            name='schema-json'),

    path('swagger/',
         schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),

    path('redoc/',
         schema_view.with_ui('redoc', cache_timeout=0),
         name='schema-redoc'),
    
    path("api/subscription/", include("subscription.urls")),
<<<<<<< HEAD
    path("api/dashboard/", include("dashboard.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/", include("meals.urls"))
=======
    path("api/dashboard/", include("dashboard.urls"))       
    ,path("api/", include("meals.urls"))
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c

]