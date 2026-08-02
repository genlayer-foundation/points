from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TelegramBindCodeRedeemView,
    TelegramBindCodeViewSet,
    ValidatorViewSet,
    ValidatorWalletViewSet,
)

router = DefaultRouter()
router.register(r'wallets', ValidatorWalletViewSet, basename='validator-wallet')
router.register(r'telegram-bind-codes', TelegramBindCodeViewSet, basename='telegram-bind-code')
router.register(r'', ValidatorViewSet, basename='validator')

urlpatterns = [
    # Service-account (Deckard bot) redemption; must precede the router so the
    # viewset's detail route never swallows 'redeem'.
    path(
        'telegram-bind-codes/redeem/',
        TelegramBindCodeRedeemView.as_view(),
        name='telegram-bind-code-redeem',
    ),
    path('', include(router.urls)),
]
