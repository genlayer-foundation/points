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

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

# Import GitHub OAuth views
from users.github_oauth import github_oauth_initiate, github_oauth_callback, disconnect_github, check_repo_star

@csrf_exempt
def health_check(request):
    """Simple health check endpoint that bypasses host validation"""
    return JsonResponse({"status": "healthy", "service": "tally-backend"})

# Schema view for Swagger documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Tally API",
        default_version='v1',
        description="API for the GenLayer Foundation's Testnet Program",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Health check endpoint
    path('health/', health_check, name='health_check'),
    
    # API endpoints
    path('api/v1/', include('api.urls')),

    # Ethereum Authentication
    path('api/auth/', include('ethereum_auth.urls')),

    # GitHub OAuth
    path('api/auth/github/', github_oauth_initiate, name='github_oauth'),
    path('api/auth/github/callback/', github_oauth_callback, name='github_callback'),
    path('api/v1/users/github/disconnect/', disconnect_github, name='github_disconnect'),
    path('api/v1/users/github/check-star/', check_repo_star, name='github_check_star'),

    # Contributions app (includes both API and staff views)
    path('contributions/', include('contributions.urls')),
    
    # API documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
