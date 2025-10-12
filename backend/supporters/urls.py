from django.urls import path
from .views import join_supporter_view

urlpatterns = [
    path('join/', join_supporter_view, name='supporter-join'),
]