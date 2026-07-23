# Submissions Review System

## Overview

Submission review has two AI stages followed by a three-level human steward
hierarchy. The AI stages keep their historical Tier 1 / Tier 2 names in code
and operational tooling; steward tiers are a separate authorization model.

- **AI gate (legacy Tier 1)**: deterministic rules run via the
  `review_submissions` command and may auto-reject.
- **AI proposal agent (legacy Tier 2)**: the external agent uses
  `/api/v1/ai-review/` to create proposals for humans.
- **Reviewer (steward tier 1)**: reviews AI-engaged submissions and can create
  proposals; high-point accepts escalate instead of finalizing.
- **Top-level steward (steward tier 2)**: sees the unrestricted queue, has the
  full permission matrix, and finalizes escalated proposals.
- **Apex steward (steward tier 3)**: has tier-2 powers and reviews accepted,
  interesting submissions through the Apex queue.

## Architecture

| Stage | Method | Auto-applies? | Human review? |
|------|--------|--------------|---------------|
| **AI gate** | Deterministic rules (management command) | Yes (reject only) | No |
| **AI proposal** | External AI agent via API | No - creates proposals | Yes |
| **Steward tier 1** | Portal review queue | Yes, below the type threshold | Yes |
| **Steward tier 2** | Portal review queue | Yes | Yes |
| **Steward tier 3** | Accepted + interesting queue | No separate decision | Yes |
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

The external AI agent accesses submissions via the `/api/v1/ai-review/` API endpoints, authenticated with a service account bearer token (`Authorization: Bearer sa_<id>_<secret>`, scopes `ai_review:read` / `ai_review:propose`). See `contributions/ai_review/` and `service_accounts/` for implementation and `.claude/skills/ai-review.md` for the agent workflow.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/ai-review/` | GET | List pending submissions, including appeals (paginated, filterable); use `has_more_info_request=true` for recorded request blocks or `is_more_info_resubmitted=true` for audited resubmissions |
| `/api/v1/ai-review/{id}/` | GET | Submission detail with evidence and user history |
| `/api/v1/ai-review/{id}/propose/` | POST | Submit a review proposal |
| `/api/v1/ai-review/templates/` | GET | List review templates |

DAI can combine lifecycle and assignment filters directly:

```text
GET /api/v1/ai-review/?assigned_to=unassigned&has_more_info_request=true
```

List and detail payloads distinguish `has_more_info_request`, backed by the
same structured notes rendered in submission cards, from
`is_more_info_resubmitted`, backed only by an append-only transition from
`more_info_needed` to `pending`.

Appeals and more-info resubmissions remain available to both AI stages. The
deterministic gate records an appeal as gate-reviewed but never auto-rejects
it, so an appeal always reaches a human reviewer.

### Project Rubric Proposals

Builder Project contribution types can opt into a structured rubric flow with
`ContributionType.review_flow`. When the value is `builder_project`, both human
Steward proposals and AI Review API proposals must include `rubric_review`.

The detailed rubric is stored in `ProjectMilestoneReview`, one row per
submission, and the existing `SubmittedContribution.proposed_*` fields remain
the active queue summary. Proposal actions still create `SubmissionNote`
records, but notes store only a compact summary/reference and are not the
source of truth.

Rubric proposal fields:
- Gate failures: fixed checklist, any selected gate forces `reject`.
- Sections: `genlayer_fit`, `contract_quality`, `engineering`, `frontend_ux`, each scored 0-5 when the gate passes. Section reasons are optional.
- Extras: fixed checklist for `live_deployment`, `demo_video`, and `public_post`.
- Overall reason: required internal explanation for the final steward.

## Human Steward Hierarchy

`Steward.tier` is `1` (Reviewer), `2` (Top-level steward), or `3` (Apex
steward). Tier 2 and tier 3 stewards receive every action on every contribution
type regardless of `StewardPermission` rows. A steward superuser has effective
tier 3.

Two fields on `ContributionType` control the hierarchy:

- `requires_ai_review`: hides unengaged pending submissions from tier-1
  reviewers, including propose-only reviewers. A submission becomes visible
  after any active proposal, an AI proposal note, an AI `ReviewProposal`, an
  appeal, or an audited more-info resubmission. Tier 2+ bypasses the gate.
- `escalation_threshold_points`: when a tier-1 reviewer accepts at or above
  `round(points * multiplier)` for the submission's contribution date, the
  accept becomes a human proposal instead of creating a `Contribution`.
  Blank disables escalation.

Builder-category types are initialized with AI review required and a 400-point
escalation threshold. The threshold is evaluated against the final type chosen
by the reviewer. Reject and request-more-info decisions never escalate.

Escalation reuses the normal `proposed_*`, `ProjectMilestoneReview`, and
`ReviewProposal` records. `SubmittedContribution.escalated_at` marks the active
proposal, and an `escalated` `SubmissionStateTransition` provides durable
history. Replacing or deciding the proposal clears the marker. A tier-1
reviewer can revise, reject, question, request more information, or accept
below the threshold; another at-threshold accept remains a proposal. Tier 2+
accepts finalize normally, including reviewer rewards for matching project
rubrics. If a top-level steward questions an escalation, its original reviewer
can revise it through their direct review permission even without a separate
`propose` permission.

Tier-1 stewards also cannot edit an already accepted award upward across the
type threshold. The steward search grammar exposes `is:escalated` and
`not:escalated`. Tier 2+ gets an Escalated queue shortcut; tier 3 gets an Apex
shortcut equivalent to `status:accepted is:interesting`.

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

## Authentication

The external AI agent authenticates with a service account token
(`Authorization: Bearer sa_<id>_<secret>`, issued from Django admin or via
`python manage.py issue_service_account_token`, see `service_accounts/`).
No environment variables are involved; tokens live in the database and are
revoked via Django admin.

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
