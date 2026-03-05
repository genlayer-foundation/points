from django.urls import path
from . import oauth

urlpatterns = [
    # OAuth endpoints (under /api/auth/twitter/)
    path('', oauth.twitter_oauth_initiate, name='twitter_oauth'),
    path('callback/', oauth.twitter_oauth_callback, name='twitter_callback'),
]

# API endpoints (under /api/v1/social/twitter/)
api_urlpatterns = [
    path('disconnect/', oauth.disconnect_twitter, name='twitter_disconnect'),
]
