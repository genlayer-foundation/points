"""
URL configuration for tally project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views import View


@csrf_exempt
def health_check(request):
    """Simple health check endpoint that bypasses host validation"""
    return JsonResponse({"status": "healthy", "service": "tally-backend"})


@ensure_csrf_cookie
def csrf_token(request):
    """Expose the active CSRF cookie name and ensure the cookie is set."""
    return JsonResponse({
        "csrfToken": get_token(request),
        "csrfCookieName": settings.CSRF_COOKIE_NAME,
    })

# Schema view for Swagger documentation.
# Open in development; staff-only in production so the full API surface
# (including internal/steward endpoints) is not published to anonymous users.
schema_view = get_schema_view(
    openapi.Info(
        title="Tally API",
        default_version='v1',
        description="API for the GenLayer Foundation's Testnet Program",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=settings.DEBUG,
    permission_classes=[permissions.AllowAny] if settings.DEBUG else [permissions.IsAdminUser],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Health check endpoint
    path('health/', health_check, name='health_check'),

    # CSRF bootstrap endpoint for the SPA
    path('api/csrf/', csrf_token, name='csrf_token'),
    
    # API endpoints
    path('api/v1/', include('api.urls')),

    # Ethereum Authentication
    path('api/auth/', include('ethereum_auth.urls')),

    # Social connections (GitHub, Twitter, Discord OAuth)
    path('', include('social_connections.urls')),

    # Contributions app (includes both API and staff views)
    path('contributions/', include('contributions.urls')),
    
    # API documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
