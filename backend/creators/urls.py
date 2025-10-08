from django.urls import path
from .views import join_creator_view

urlpatterns = [
    path('join/', join_creator_view, name='creator-join'),
]