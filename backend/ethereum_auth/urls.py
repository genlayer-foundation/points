from django.urls import path
from . import views

urlpatterns = [
    path('nonce/', views.get_nonce, name='nonce'),
    path('login/', views.login, name='login'),
    # Add a URL pattern without trailing slash as well
    path('login', views.login, name='login_no_slash'),
    path('verify/', views.verify_auth, name='verify'),
    path('logout/', views.logout, name='logout'),
    path('refresh/', views.refresh_session, name='refresh'),
]