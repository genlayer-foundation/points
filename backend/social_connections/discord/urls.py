from django.urls import path
from . import oauth

urlpatterns = [
    # OAuth endpoints (under /api/auth/discord/)
    path('', oauth.discord_oauth_initiate, name='discord_oauth'),
    path('callback/', oauth.discord_oauth_callback, name='discord_callback'),
]

# API endpoints (under /api/v1/social/discord/)
api_urlpatterns = [
    path('disconnect/', oauth.disconnect_discord, name='discord_disconnect'),
    path('check-guild/', oauth.check_guild_membership, name='discord_check_guild'),
]
