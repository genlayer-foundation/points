"""
URL configuration for social connections.

This module provides two sets of URL patterns:
- auth_urlpatterns: OAuth flow endpoints (initiate, callback) under /api/auth/{platform}/
- api_urlpatterns: API endpoints (disconnect, etc.) under /api/v1/social/{platform}/
"""
from django.urls import path, include
from social_connections.github.urls import urlpatterns as github_auth_urls, api_urlpatterns as github_api_urls
from social_connections.twitter.urls import urlpatterns as twitter_auth_urls, api_urlpatterns as twitter_api_urls
from social_connections.discord.urls import urlpatterns as discord_auth_urls, api_urlpatterns as discord_api_urls

# OAuth flow endpoints (under /api/auth/)
auth_urlpatterns = [
    path('github/', include(github_auth_urls)),
    path('twitter/', include(twitter_auth_urls)),
    path('discord/', include(discord_auth_urls)),
]

# API endpoints (under /api/v1/social/)
api_urlpatterns = [
    path('github/', include(github_api_urls)),
    path('twitter/', include(twitter_api_urls)),
    path('discord/', include(discord_api_urls)),
]
