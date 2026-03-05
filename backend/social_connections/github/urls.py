from django.urls import path
from . import oauth

urlpatterns = [
    # OAuth endpoints (under /api/auth/github/)
    path('', oauth.github_oauth_initiate, name='github_oauth'),
    path('callback/', oauth.github_oauth_callback, name='github_callback'),
]

# API endpoints (under /api/v1/social/github/)
api_urlpatterns = [
    path('disconnect/', oauth.disconnect_github, name='github_disconnect'),
    path('check-star/', oauth.check_repo_star, name='github_check_star'),
]
