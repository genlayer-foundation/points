---
name: ai-review
description: >
  Review pending community submissions for the GenLayer Testnet Program via the AI Review API.
  Use when asked to review submissions, evaluate pending contributions, propose accept/reject/more_info
  actions, or process the submission review queue. Authenticates via X-AI-Review-Key header against
  the backend API. All proposals require human steward approval before being applied.
---

# AI Submission Review

Review pending community submissions for the GenLayer Testnet Program and propose review actions.

## Prerequisites

- Backend server running (local or remote)
- `AI_REVIEW_API_KEY` configured in the backend `.env` file

## Setup

Before making any API calls:

1. Read the API key from the backend `.env` file (look for `AI_REVIEW_API_KEY`)
2. Determine the backend base URL (default: `http://localhost:8000`)
3. All requests require the header: `X-AI-Review-Key: <key>`

Use `curl` via the Bash tool for all API calls.

## Workflow

Follow this sequence for every review session:

### Step 1: Fetch templates

```bash
curl -s -H "X-AI-Review-Key: $KEY" "$BASE_URL/api/v1/ai-review/templates/"
```

Cache the template list for the session. Templates have `id`, `label`, and `text` fields.
Use template text as the basis for `proposed_staff_reply` to keep responses consistent.

### Step 2: List pending submissions

```bash
curl -s -H "X-AI-Review-Key: $KEY" "$BASE_URL/api/v1/ai-review/?page_size=10"
```

The list view returns lightweight data (no evidence or user history — just id, type, category, notes, state, created_at).
Use it to identify which submissions to evaluate in detail.

Common filters: `category=builder`, `exclude_empty_evidence=true`, `include_content=github`, `ordering=-created_at`.

### Step 3: Get submission detail

For each submission to evaluate:

```bash
curl -s -H "X-AI-Review-Key: $KEY" "$BASE_URL/api/v1/ai-review/{uuid}/"
```

The detail view returns the full submission including `evidence_items` (URLs, descriptions) and
`user_history` (accepted_count, rejected_count, pending_count). Use this data to make your evaluation.

### Step 4: Propose a review (POST = create, PUT = update)

**Create** a new proposal (fails with 409 if one already exists):

```bash
curl -s -X POST -H "X-AI-Review-Key: $KEY" -H "Content-Type: application/json" \
  "$BASE_URL/api/v1/ai-review/{uuid}/propose/" \
  -d '{
    "proposed_action": "reject",
    "proposed_staff_reply": "Your submission lacks verifiable evidence.",
    "reasoning": "No evidence URLs. User has 3 rejections, 0 acceptances.",
    "confidence": "high",
    "template_id": 7
  }'
```

**Update** an existing proposal (fails with 404 if no proposal exists):

```bash
curl -s -X PUT -H "X-AI-Review-Key: $KEY" -H "Content-Type: application/json" \
  "$BASE_URL/api/v1/ai-review/{uuid}/propose/" \
  -d '{
    "proposed_action": "accept",
    "proposed_points": 3,
    "proposed_staff_reply": "After re-evaluation, this contribution meets the criteria.",
    "reasoning": "Revisited evidence — GitHub repo has real code and README.",
    "confidence": "medium"
  }'
```

Use PUT when you want to change your mind on a previous proposal (e.g. after fetching more context or re-evaluating evidence). Both the old and new proposals are preserved as CRM notes for audit.

**Required fields by action:**

| Action | Required |
|--------|----------|
| `accept` | `proposed_points` (within contribution type min/max) |
| `reject` | `proposed_staff_reply` |
| `more_info` | `proposed_staff_reply` |

Optional: `reasoning` (internal CRM note), `confidence` (high/medium/low), `template_id`.

`confidence` is stored on the submission and displayed as a color-coded badge to stewards in the CRM notes panel. Set it accurately — stewards use it to prioritize which proposals to review first.

`template_id` is stored on the submission and stewards can filter by it. Always pass it when using a template so the data is traceable.

Errors: 400 = validation, 404 = not found/not pending/no proposal to update, 409 = already has proposal (POST only).

### Step 5: Continue

Page through remaining submissions with `?page=2&page_size=10`.

### Calibration: Review past decisions

```bash
curl -s -H "X-AI-Review-Key: $KEY" "$BASE_URL/api/v1/ai-review/reviewed/?page_size=10"
```

Returns submissions that were reviewed by stewards after having an AI proposal. Includes the final `state`, `staff_reply`, `evidence_items`, and all `internal_notes` (with proposal data). Use this to calibrate future proposals — check whether stewards agreed with your proposals or overrode them.

Filters: `state=accepted|rejected|more_info_needed`, `contribution_type={id}`, `category={slug}`.

## Evaluation Guidelines

### Reject when:
- No evidence and no meaningful notes
- Evidence URLs are generic platform pages (points.genlayer.foundation, studio.genlayer.com)
- Notes are spam, gibberish, or very short
- Same URL already submitted by another user (copy-paste gaming)
- Tweets or social posts submitted as "Educational Content" / "Documentation" / "Research & Analysis" — these belong in community content via Discord
- AI-generated content with no specific technical detail
- Plans or intentions with no actual work done

### Accept when:
- GitHub repos with real code, README, and ideally a deployed demo
- Deep technical content (tutorials with code, architecture analysis)
- Tools, dashboards, SDKs that help the ecosystem
- Original research with genuine insights
- Award 1-2 points for borderline, 3-5+ for substantial work

### Request more info when:
- Notes describe a project but evidence is missing
- Evidence links are broken or unclear
- The contribution is plausible but needs verification

### Confidence:
- **high**: Obvious spam, clearly valuable, or clear-cut violations
- **medium**: Likely correct but edge cases exist
- **low**: Ambiguous, needs human judgment

## Important constraints

- Never auto-accept. Acceptances always need careful human review.
- Users with many rejections and zero acceptances are likely spammers.
- Users with prior acceptances are more likely legitimate.
- Prefer `more_info` over `reject` when evidence is missing but notes are descriptive — unless spam history.
- `proposed_staff_reply` is shown to the user. Be helpful and specific.
- `reasoning` is internal only. Be candid about red flags.
