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
    path('signup/email/start/', views.signup_email_start, name='signup_email_start'),
    path('signup/email/resend/', views.signup_email_resend, name='signup_email_resend'),
    path('signup/email/confirm/', views.signup_email_confirm, name='signup_email_confirm'),
    path('email/start/', views.email_start, name='email_start'),
    path('email/resend/', views.email_resend, name='email_resend'),
    path('email/confirm/', views.email_confirm, name='email_confirm'),
]
