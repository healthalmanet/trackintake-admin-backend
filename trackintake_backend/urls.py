from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse, JsonResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


# Home route
def home(request):
    return HttpResponse("Django Backend Running")


# Health check endpoint for Render monitoring
def health_check(request):
    return JsonResponse({
        "status": "healthy",
        "service": "TrackIntake Backend"
    })


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

    # Home & Health Check
    path('', home, name='home'),
    path('health/', health_check, name='health'),

    # Users API
    path('api/users/', include('users.urls')),
    

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
    path("api/dashboard/", include("dashboard.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("meals.urls")),
    path("api/nutritionist/", include("nutritionist.urls")),

]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
