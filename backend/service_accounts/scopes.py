AI_REVIEW_READ_SCOPE = 'ai_review:read'
AI_REVIEW_PROPOSE_SCOPE = 'ai_review:propose'

AI_REVIEW_SCOPES = (
    AI_REVIEW_READ_SCOPE,
    AI_REVIEW_PROPOSE_SCOPE,
)

# Granted to the Deckard Telegram support bot so it can redeem validator
# Telegram group bind codes (validators app).
TELEGRAM_BIND_REDEEM_SCOPE = 'telegram_bind:redeem'

ALLOWED_SERVICE_ACCOUNT_SCOPES = frozenset(
    AI_REVIEW_SCOPES + (TELEGRAM_BIND_REDEEM_SCOPE,)
)
