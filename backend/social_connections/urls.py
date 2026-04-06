from django.urls import path

from .github_oauth import github_oauth_initiate, github_oauth_callback, disconnect_github, check_repo_star
from .twitter_oauth import twitter_oauth_initiate, twitter_oauth_callback, disconnect_twitter
from .discord_oauth import discord_oauth_initiate, discord_oauth_callback, disconnect_discord, check_discord_guild

urlpatterns = [
    # GitHub OAuth
    path('api/auth/github/', github_oauth_initiate, name='github_oauth'),
    path('api/auth/github/callback/', github_oauth_callback, name='github_callback'),
    path('api/v1/users/github/disconnect/', disconnect_github, name='github_disconnect'),
    path('api/v1/users/github/check-star/', check_repo_star, name='github_check_star'),

    # Twitter OAuth
    path('api/auth/twitter/', twitter_oauth_initiate, name='twitter_oauth'),
    path('api/auth/twitter/callback/', twitter_oauth_callback, name='twitter_callback'),
    path('api/v1/users/twitter/disconnect/', disconnect_twitter, name='twitter_disconnect'),

    # Discord OAuth
    path('api/auth/discord/', discord_oauth_initiate, name='discord_oauth'),
    path('api/auth/discord/callback/', discord_oauth_callback, name='discord_callback'),
    path('api/v1/users/discord/disconnect/', disconnect_discord, name='discord_disconnect'),
    path('api/v1/users/discord/check-guild/', check_discord_guild, name='discord_check_guild'),
]
