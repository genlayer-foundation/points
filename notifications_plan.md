# Email Notification & Verification System - Implementation Plan

## Issues Addressed

- **#208**: Notify users about submission state changes (accepted/rejected/more info needed)
- **#180**: Add email verification for user accounts

---

## Technology Stack

- **Django Email Backend**: Django's built-in SMTP email system
- **Mailtrap.io**: Development/testing email capture
- **Django Signals**: Auto-trigger notifications on submission state changes
- **REST Framework**: Notification API endpoints

---

## File Structure

```
backend/
├── notifications/              # NEW app
│   ├── models.py              # Notification model
│   ├── views.py               # API endpoints
│   ├── serializers.py
│   ├── signals.py             # Auto-trigger on submission state change
│   └── email_service.py       # Email sending
├── users/
│   ├── models.py              # MODIFY: Add verification token fields
│   └── views.py               # MODIFY: Add verification endpoints
├── tally/settings.py          # MODIFY: Email config
├── templates/emails/          # NEW: Email templates
└── .env                       # MODIFY: SMTP credentials

frontend/ (Phase 1 - Email Verification Only)
└── src/routes/
    ├── VerifyEmail.svelte    # NEW page
    └── ProfileEdit.svelte    # MODIFY: Add email verification UI

frontend/ (Phase 2 - Future)
├── src/lib/notificationStore.js           # NEW store
├── src/components/NotificationBell.svelte # NEW
└── src/routes/
    ├── Notifications.svelte               # NEW page
    └── MySubmissions.svelte               # MODIFY: Add indicators
```

---

## Backend Implementation

### 1. Notification Model

**Location**: `backend/notifications/models.py`

```
- user (ForeignKey to User)
- notification_type (CharField: 'submission_accepted', 'submission_rejected', 'submission_more_info')
- title (CharField)
- message (TextField)
- read (BooleanField, default=False)
- read_at (DateTimeField, null)
- related_submission (ForeignKey to SubmittedContribution, null)
- action_url (URLField) - Link to submission detail page
- created_at, updated_at (from BaseModel)
```

### 2. Email Configuration

**`backend/tally/settings.py`**: Django SMTP email backend with Mailtrap credentials from env vars

**`backend/.env`**: Add `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (Mailtrap for dev)

### 3. Email Templates

**Location**: `backend/templates/emails/`

**Templates**: HTML + plain text for each:

- `submission_accepted` - Congratulations + points
- `submission_rejected` - Feedback + resubmit encouragement
- `submission_more_info` - What's needed
- `email_verification` - Verification link
- `base_email` - Shared layout

### 4. Email Verification

**User Model** (`backend/users/models.py`): Add `email_verification_token`, `email_verification_sent_at`

**API Endpoints** (`backend/users/views.py`):

- `POST /api/v1/users/request-email-verification/`
- `POST /api/v1/users/verify-email/`
- `POST /api/v1/users/resend-verification/`

**Flow**: Generate UUID4 token → Send email with link → Verify token (24h expiry) → Mark verified

### 5. Notification Triggers

**Django Signal** (`backend/notifications/signals.py`): `post_save` on `SubmittedContribution`

- Detect state changes (pending → accepted/rejected/more_info_needed)
- Create Notification object
- Send email (only if user has verified email)

### 6. Email Service

**File**: `backend/notifications/email_service.py`

- `send_submission_notification_email(submission)` - Routes to correct template
- `send_verification_email(user)` - Sends verification link
- Error handling: Log failures, don't crash

---

## Backend Implementation Phases

**Phase 1 (Initial):**
- Sections 1-6 above (Notification model, email config, templates, verification, triggers, email service)
- Notifications created in database but no API yet
- Emails sent on submission state changes

**Phase 2 (Future - when building notification UI):**
- Notification API (`backend/notifications/views.py`, `serializers.py`, `urls.py`)
- Endpoints: list, unread-count, mark-read, mark-all-read
- Connect existing notifications to frontend

---

## Frontend Implementation

### Phase 1: Email Verification UI (Initial Implementation)

**Profile Edit** (`frontend/src/routes/ProfileEdit.svelte`):

- Verification status badge
- "Verify Email" button (if not verified)
- "Resend Verification" button
- Toast notification on email sent

**New Route** (`frontend/src/routes/VerifyEmail.svelte`):

- Handle `/verify-email?token=XXX` from email link
- Call verification API
- Show success/error message
- Redirect to profile

### Phase 2: Notification UI (Future Implementation)

**Will be added after email system is working properly:**

1. **Notification Store** (`frontend/src/lib/notificationStore.js`): State management with polling
2. **Notification Bell** (`frontend/src/components/NotificationBell.svelte`): Header component with unread badge
3. **Notifications Page** (`frontend/src/routes/Notifications.svelte`): Full notification list (GitHub-style)
4. **MySubmissions Integration**: Notification indicators on submissions

---

## Key Behaviors

**Email sending**: Only to verified users (`is_email_verified=True`), in-app notifications always created

**Token security**: UUID4, 24h expiry, one-time use

**Testing**: Mailtrap.io for dev, production SMTP for live (SendGrid/SES/Mailgun)

**Migrations**: Create `notifications` app, add Notification model, add verification fields to User

**Dependencies**: None (Django email built-in)
