from django.urls import path

from .views import sync_mee6_xp

app_name = 'community_xp'

urlpatterns = [
    path('mee6/sync-and-apply/', sync_mee6_xp, name='mee6_sync_and_apply'),
]
