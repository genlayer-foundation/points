# Submissions Review System

## Overview

Two-tier review pipeline for GenLayer Testnet Program submissions:
- **Tier 1**: Deterministic rules run via `review_submissions` management command (auto-reject)
- **Tier 2**: External AI agent using the `/api/v1/ai-review/` API endpoints (proposals for human review)

## Architecture

| Tier | Method | Auto-applies? | Human review? |
|------|--------|--------------|---------------|
| **Tier 1** | Deterministic rules (management command) | Yes (reject only) | No |
| **Tier 2** | External AI agent via API | No — creates proposals | Yes |
| **Auto-ban** | Post-batch check (management command) | Yes (ban user) | Appeal via in-app flow |

### AI Steward

- **User**: `genlayer-steward@genlayer.foundation` (migration: `stewards/migrations/0006_create_ai_steward.py`)
- **Permissions**: Full steward permissions on all contribution types
- **Visibility**: `visible=False` (hidden from leaderboard/public)

### Review Templates

Managed in `stewards_reviewtemplate` table. Three templates used by Tier 1 (created via migration `stewards/migrations/0009_tier1_review_templates.py`):

| Label | Action | Purpose |
|-------|--------|---------|
| `Reject: No Evidence` | reject | Submission has no evidence URL |
| `Reject: Duplicate Submission` | reject | Evidence URL already used in another submission |
| `Reject: Invalid Evidence URL` | reject | All evidence URLs are blocklisted platform pages |

## Tier 1: Deterministic Rules

Three rules evaluated in order; first match wins. Optimized for batch processing with pre-loaded URL lookups (2 DB queries total regardless of submission count).

| # | Rule | What it catches |
|---|------|-----------------|
| 1 | `rule_no_evidence_url` | No evidence items with a non-empty URL |
| 2 | `rule_blocklisted_url` | All evidence URLs match blocklisted platform prefixes |
| 3 | `rule_duplicate_evidence_url` | Any evidence URL already exists in a pending/accepted/more_info_needed submission by any user |

### Processing Order

Submissions are processed **newest first** (`-created_at`). When duplicates share a URL, the newer copy is rejected and the oldest original survives. After each rejection, the submission is removed from the in-memory URL lookup to prevent mutual rejection.

### Blocklisted URLs

Managed in the `contributions_blocklistedurl` database table (Django admin). URL prefixes are normalized on save (query params, fragments, and trailing slashes stripped).

Initial seed data (migration `contributions/migrations/0043_seed_blocklisted_urls.py`):
- `studio.genlayer.com/run-debug`
- `studio.genlayer.com/contracts`
- `points.genlayer.foundation`
- `www.genlayer.com`
- `genlayer.com`

### Evidence URL Requirement

Evidence items require a URL. This is enforced at:
- **Backend serializer**: `SubmittedEvidenceSerializer` requires `url` (non-blank)
- **Frontend**: Submit and edit forms require at least one evidence item with a URL
- **Tier 1 review**: Submissions without any evidence URL are auto-rejected

## User Ban System

### Auto-Ban

After each batch run, the command checks for users meeting the threshold:
- **5+ total rejections** AND **0 acceptances** (100% rejection rate)
- Sets `is_banned=True` with reason explaining the rejection count
- `banned_by` set to the AI steward user

### Ban Appeal Flow

1. Banned user sees ban status + reason on their profile
2. User submits one-time appeal via `POST /api/v1/users/me/appeal/`
3. Stewards review appeals via `GET /api/v1/steward-submissions/ban-appeals/`
4. Steward approves (unbans) or denies via `POST /api/v1/steward-submissions/ban-appeals/{id}/review/`

## Tier 2: External AI Agent

The external AI agent accesses submissions via the `/api/v1/ai-review/` API endpoints, authenticated with the `X-AI-Review-Key` header. See `contributions/ai_review/` for implementation and `.claude/skills/ai-review.md` for the agent workflow.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/ai-review/` | GET | List pending submissions (paginated, filterable) |
| `/api/v1/ai-review/{id}/` | GET | Submission detail with evidence and user history |
| `/api/v1/ai-review/{id}/propose/` | POST | Submit a review proposal |
| `/api/v1/ai-review/templates/` | GET | List review templates |

## Management Command Usage

```bash
# Dry run (see what would happen)
python manage.py review_submissions --dry-run

# Specific batch size
python manage.py review_submissions --batch-size 50

# Filter by contribution type
python manage.py review_submissions --type "Educational Content"

# Single submission
python manage.py review_submissions --submission-id <uuid>
```

## Environment Variables

```
AI_REVIEW_API_KEY=...   # For external AI agent API authentication
```

## Files

| File | Purpose |
|------|---------|
| `contributions/management/commands/review_submissions.py` | Tier 1 deterministic rules + auto-ban |
| `contributions/models.py` | `BlocklistedURL` model for URL prefix management |
| `contributions/ai_review/` | API endpoints for external AI agent |
| `stewards/migrations/0009_tier1_review_templates.py` | Tier 1 review templates |
| `contributions/migrations/0042_blocklisted_url_model.py` | BlocklistedURL table |
| `contributions/migrations/0043_seed_blocklisted_urls.py` | Initial blocklisted URLs |
| `users/models.py` | Ban fields + `BanAppeal` model |
| `.claude/skills/ai-review.md` | AI agent workflow documentation |
