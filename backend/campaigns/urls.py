from django.urls import re_path

from . import views

# Optional trailing slash so APPEND_SLASH never answers with a 301 through
# the Amplify proxy (redirect responses must stay 302 + no-store).
urlpatterns = [
    re_path(
        r'^redirect/(?P<role>[A-Za-z]+)/(?P<alias>[A-Za-z0-9\-]+)/?$',
        views.campaign_redirect,
        name='campaign_redirect',
    ),
]
