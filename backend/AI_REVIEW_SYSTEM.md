# Automated Submission Review System

## Overview

Two-tier automated review of user submissions. Tier 1 applies deterministic rules for instant rejection of obvious spam. Tier 2 sends remaining submissions to an LLM (Claude via OpenRouter) which proposes actions that require human steward approval. An external AI agent can also access submissions via token-authenticated API endpoints.

---

## Core Files

### Management Command
| File | Description |
|------|-------------|
| `contributions/management/commands/review_submissions.py` | Main entry point. Runs Tier 1 deterministic rules then Tier 2 AI classification. Tracks cost per run. |

### Tier 1 — Deterministic Rules (defined in review_submissions.py)
Nine rules evaluated in order, first match wins → auto-reject:
1. No evidence + no notes
2. No evidence + short notes (≤10 chars)
3. Spam notes (hardcoded set: "nothing", "ok", "test", "airdrop", etc.)
4. Duplicate pending from same user (identical notes)
5. Resubmitted previously-rejected URL
6. Same URL in older pending submission by same user
7. Blocklisted URLs (generic platform pages like genlayer.com, studio.genlayer.com)
8. Cross-user duplicate URL (copy-paste gaming)
9. Cross-user identical notes >20 chars (farming template)

### Tier 2 — AI Classification (defined in review_submissions.py)
Calls OpenRouter API with submission details, user history, review templates, and calibration examples. Returns a JSON proposal (accept/reject/more_info with points, confidence, reasoning). All proposals require human approval.

---

## AI Review API (External Agent Endpoints)

| File | Description |
|------|-------------|
| `contributions/ai_review/__init__.py` | Package init |
| `contributions/ai_review/views.py` | ViewSet: list/detail pending submissions, propose reviews, list templates. Includes filterset with 13 filters. |
| `contributions/ai_review/serializers.py` | Light serializer (list), full serializer (detail with evidence + user history), propose serializer, template serializer |
| `contributions/ai_review/permissions.py` | `IsAIReviewToken` — authenticates via `X-AI-Review-Key` header against `AI_REVIEW_API_KEY` setting |
| `contributions/ai_review/urls.py` | Route registration with SimpleRouter |

**Endpoints** (all under `/api/v1/ai-review/`):
- `GET /` — List pending submissions (paginated, filterable)
- `GET /{id}/` — Submission detail with evidence and user history
- `POST /{id}/propose/` — Submit a review proposal
- `GET /templates/` — List review templates

---

## Models

| File | Key Models |
|------|------------|
| `contributions/models.py` | `SubmittedContribution` (proposal fields: proposed_action, proposed_points, proposed_staff_reply, proposed_by, proposed_at), `SubmissionNote` (CRM notes with is_proposal flag and data JSONField), `Evidence` |
| `stewards/models.py` | `Steward`, `StewardPermission` (per-action permissions on contribution types), `ReviewTemplate` (admin-managed response templates with action field) |
| `users/models.py` | Ban fields on `User` (is_banned, ban_reason, banned_at, banned_by), `BanAppeal` model |

---

## Steward & Permissions

| File | Description |
|------|-------------|
| `contributions/permissions.py` | Steward permission checking logic |
| `contributions/views.py` | `StewardSubmissionViewSet` with review actions and ban appeals |
| `contributions/serializers.py` | `StewardSubmissionSerializer`, `SubmissionProposeSerializer`, `SubmissionNoteSerializer` |
| `stewards/views.py` | `StewardViewSet` for profiles and ban appeal management |
| `stewards/serializers.py` | Steward and permission serializers |
| `stewards/admin.py` | Admin interface for stewards and permissions |

---

## Migrations

| File | Description |
|------|-------------|
| `contributions/migrations/0032_submittedcontribution_proposal_fields_submissionnote.py` | Adds proposal fields to SubmittedContribution, creates SubmissionNote |
| `contributions/migrations/0033_submissionnote_data_field.py` | Adds JSONField to SubmissionNote for calibration data |
| `stewards/migrations/0004_stewardpermission_reviewtemplate.py` | Creates StewardPermission and ReviewTemplate models |
| `stewards/migrations/0005_grant_all_permissions_to_existing_stewards.py` | Grants all permissions to existing stewards |
| `stewards/migrations/0006_create_ai_steward.py` | Creates AI steward user (genlayer-steward@genlayer.foundation) with full permissions |
| `stewards/migrations/0007_add_action_to_reviewtemplate.py` | Adds action field to ReviewTemplate |
| `stewards/migrations/0008_add_wrong_category_template.py` | Adds "wrong category" review template |
| `users/migrations/0017_user_ban_fields.py` | Adds ban system fields and BanAppeal model |

---

## Configuration

| File | Description |
|------|-------------|
| `tally/settings.py` | `AI_REVIEW_API_KEY` env var for API authentication |
| `api/urls.py` | Registers `ai-review/` endpoint path |
| `deploy-apprunner-dev.sh` | SSM secret: `/tally-backend/dev/ai_review_api_key` |
| `deploy-apprunner.sh` | SSM secret: `/tally-backend/prod/ai_review_api_key` |

---

## Tests

| File | Description |
|------|-------------|
| `contributions/tests/test_review_submissions.py` | Tests for all 9 Tier 1 deterministic rules |
| `contributions/tests/test_calibration_data.py` | Tests for calibration data in SubmissionNote.data |
| `contributions/tests/test_ban_submission_block.py` | Tests for banned user submission blocking and appeals |
| `contributions/tests/test_steward_permissions.py` | Tests for steward permission model |
| `users/tests/test_ban_system.py` | Tests for user ban and appeal models |

---

## Documentation

| File | Description |
|------|-------------|
| `submissions_review.md` | Full documentation covering rules, AI classification, ban system, API, cost tracking |
| `.claude/skills/ai-review.md` | Claude Code skill for the external AI review agent workflow |
