---
name: ai-review
description: >
  Use the GenLayer AI Review API to fetch submissions, inspect details, create
  AI review proposals, update AI-created proposals, list active proposals,
  inspect active human steward proposals, and inspect reviewed AI proposals for
  calibration. All requests require a service account bearer token. The AI
  Review API creates proposals only; it does not apply final accept, reject,
  or more-info decisions.
---

# AI Review API

## Rules

- Use only `/api/v1/ai-review/...` endpoints.
- Do not call `/api/v1/steward-submissions/{id}/review/`.
- Fetch `/api/v1/ai-review/{id}/` before proposing on any submission.
- Use POST to create an AI proposal. Use PUT only to update an AI-created proposal.
- If PUT returns 403, stop; the active proposal is not AI-created.
- `proposed_staff_reply` is user-visible. `reasoning` is internal.

## Setup

Set:

- `TOKEN`: a service account token (`sa_<id>_<secret>`) with the
  `ai_review:read` and `ai_review:propose` scopes, issued from Django admin
  or with `python manage.py issue_service_account_token`
- `BASE_URL`: backend base URL, usually `http://localhost:8000`

Every request needs:

```bash
-H "Authorization: Bearer $TOKEN"
```

Read endpoints need the `ai_review:read` scope; propose needs
`ai_review:propose` (a read-only token gets 403 on propose).

## Endpoints

| Endpoint | Method | Purpose | Default Scope |
|---|---:|---|---|
| `/api/v1/ai-review/` | GET | Find new submissions to evaluate, or query active proposals when proposal filters are sent | Pending, unproposed, non-appealed unless `has_appeal` or proposal filters are sent |
| `/api/v1/ai-review/{id}/` | GET | Full submission detail, including `internal_notes` | One pending submission |
| `/api/v1/ai-review/{id}/propose/` | POST | Create AI proposal | Fails if an active proposal already exists |
| `/api/v1/ai-review/{id}/propose/` | PUT | Update AI-created proposal | Fails if no proposal exists or proposal is human-created |
| `/api/v1/ai-review/proposed/` | GET | List active proposals | Pending submissions with active AI or human steward proposals |
| `/api/v1/ai-review/reviewed/` | GET | Calibration data | Reviewed submissions that have AI proposal notes |
| `/api/v1/ai-review/templates/` | GET | List reusable review templates | Returns `id`, `label`, `action`, and `text` |

Use `/ai-review/` for new unproposed work, `/ai-review/proposed/` for active
proposals from AI or human stewards, and `/ai-review/reviewed/` only for
calibration. Add `proposed_by=ai` when you need active AI-created proposals
only. Add `proposed_by=<user_id>` and/or `assigned_to=<user_id>` when you need
active proposals for a specific steward.

## Workflow

1. Fetch candidates from `/api/v1/ai-review/`.
2. Fetch detail for one candidate with `/api/v1/ai-review/{id}/` and inspect `internal_notes`.
3. Fetch `/api/v1/ai-review/templates/` if you plan to use a review template.
4. Decide `accept`, `reject`, or `more_info`.
5. POST a proposal to `/api/v1/ai-review/{id}/propose/`.
6. Continue pagination with `page` and `page_size`.

Create proposal:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/api/v1/ai-review/{uuid}/propose/" \
  -d '{
    "proposed_action": "reject",
    "proposed_staff_reply": "Your submission lacks verifiable evidence for the work described.",
    "reasoning": "No evidence URLs were provided and the notes do not identify a concrete artifact.",
    "confidence": "high"
  }'
```

Update AI-created proposal:

```bash
curl -s -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/api/v1/ai-review/{uuid}/propose/" \
  -d '{
    "proposed_action": "accept",
    "proposed_points": 3,
    "proposed_staff_reply": "This contribution meets the program criteria after re-evaluating the repository.",
    "reasoning": "The repository includes working code, documentation, and GenLayer-specific implementation details.",
    "confidence": "medium"
  }'
```

## Proposal Body

| Field | Required When | Values |
|---|---|---|
| `proposed_action` | Always | `accept`, `reject`, `more_info` |
| `proposed_points` | Standard `proposed_action=accept`; optional for `review_flow=builder_project` | Integer within `min_points` and `max_points` from detail |
| `proposed_staff_reply` | `reject`, `more_info`; optional for `accept` | User-visible text |
| `reasoning` | Optional | Internal text |
| `confidence` | Optional | `high`, `medium`, `low`; defaults to `medium` |
| `template_id` | Optional | ID from `/api/v1/ai-review/templates/`; template `action` must match `proposed_action` |
| `rubric_review` | `review_flow=builder_project` | Gate failures, section scores, optional section reasons, extras, and overall reason |
| `synthesis` | Optional; always send it for `review_flow=builder_project` | Markdown analysis of the submission (merged adversarial + merit passes). Steward-only: shown to human reviewers in an expandable "AI review analysis" panel on the submission card. Unlike the other proposal fields, it is preserved permanently even after a human steward re-proposes on top |

## Internal Notes

- Pending submission details from `/api/v1/ai-review/{id}/` include `internal_notes`.
- Reviewed calibration submissions from `/api/v1/ai-review/reviewed/` also include `internal_notes`.
- Each note includes `message`, `is_proposal`, `data`, and `created_at`.
- Treat `internal_notes` as internal context only. Do not copy private reasoning or CRM notes into `proposed_staff_reply`.

## Response Fields

List responses from `/api/v1/ai-review/` and `/api/v1/ai-review/proposed/`
include compact submission fields plus the active proposal summary:

- `assigned_to`, `assigned_to_name`
- `has_proposal`
- `proposed_action`, `proposed_points`, `proposed_staff_reply`
- `proposed_contribution_type`
- `proposed_user`, `proposed_user_details`
- `proposed_create_highlight`, `proposed_highlight_title`, `proposed_highlight_description`
- `proposed_by`, `proposed_by_name`, `proposed_at`
- `proposed_confidence`
- `proposed_template`, `proposed_template_name`
- `rubric_review`

Full detail from `/api/v1/ai-review/{id}/` includes the same active proposal
summary, plus `evidence_items`, `internal_notes`, and `user_history`.

For standard reviews, `rubric_review` is `null`; use the `proposed_*` fields.
For Builder Project reviews (`review_flow=builder_project`), `rubric_review`
contains `gate_failures`, `sections`, `extras`, `overall_reason`, `action`,
`confidence`, and `proposer_name`. Builder Project accept proposals may have
`proposed_points: null` because final stewards assign points manually from the
rubric.

## Filters

All list endpoints support these parameters unless the endpoint default scope
already makes the filter meaningless. Send backend parameter names exactly.

| Parameter | Values | Meaning |
|---|---|---|
| `page` | positive integer | Page number |
| `page_size` | 1-100 | Results per page |
| `ordering` | `created_at`, `-created_at`, `contribution_date`, `-contribution_date` | Sort order |
| `state` | `pending`, `accepted`, `rejected`, `more_info_needed`, `canceled` | Current submission state |
| `exclude_state` | same as `state` | Exclude current state |
| `contribution_type` | contribution type ID | Exact contribution type |
| `exclude_contribution_type` | contribution type ID | Exclude contribution type |
| `category` | category slug | Contribution type category |
| `exclude_category` | category slug | Exclude category |
| `mission` | mission ID, `none`, `null` | Exact mission, or no mission |
| `exclude_mission` | mission ID, `none`, `null` | Exclude mission, or require a mission when value is `none`/`null` |
| `username_search` | text | Match submitter name, email, or address |
| `exclude_username` | text | Exclude matching submitters |
| `assigned_to` | user ID, `unassigned`, `null`; comma-separated values accepted | Assigned steward, unassigned, or any of several assignments |
| `exclude_assigned_to` | user ID, `unassigned`, `null`; comma-separated values accepted | Exclude assigned stewards and/or unassigned submissions |
| `proposed_by` | user ID, `ai`, `none`, `null`, `unproposed`; comma-separated values accepted | Proposal creator. On `/proposed/`, this means the active proposal creator. On `/reviewed/`, this means historical proposal-note creator. `ai` means `genlayer-steward@genlayer.foundation`; `none`/`null`/`unproposed` means no creator |
| `exclude_proposed_by` | user ID, `ai`, `none`, `null`, `unproposed`; comma-separated values accepted | Exclude proposal creators using the same active-vs-historical rule as `proposed_by` |
| `search` | text | Match submitter name/email/address, notes, evidence URL, or evidence description |
| `include_content` | comma-separated terms | Every term must match notes or evidence |
| `exclude_content` | comma-separated terms | Exclude if any term matches notes or evidence |
| `exclude_empty_evidence` | `true`, `false` | `true` keeps submissions with URL evidence or URL in notes |
| `only_empty_evidence` | `true`, `false` | `true` keeps submissions with no URL evidence and no URL in notes |
| `has_proposal` | `true`, `false` | Whether `proposed_action` is set |
| `proposed_action` | `accept`, `reject`, `more_info` | Active proposal action |
| `proposed_confidence` | `high`, `medium`, `low` | Active proposal confidence |
| `proposed_template` | template ID | Active proposal template |
| `has_appeal` | `true`, `false` | Submitter appeal flag |
| `is_interesting` | `true`, `false` | Internal interesting flag |
| `resubmitted_more_info` | `true`, `false` | Pending submissions that were reviewed before and edited after that review |
| `min_accepted_contributions` | positive integer | Submitter has at least this many accepted submissions |

## More-Info Filters

Use the exact filter for the question being asked:

| Need | Endpoint | Filter |
|---|---|---|
| Submissions currently waiting on submitter info | `/api/v1/ai-review/reviewed/` or steward search | `state=more_info_needed` |
| Pending submissions resubmitted after more info was requested | `/api/v1/ai-review/` | `resubmitted_more_info=true` |
| Active proposals recommending more info | `/api/v1/ai-review/proposed/` | `proposed_action=more_info` |
| Reviewed submissions where final steward decision was more info | `/api/v1/ai-review/reviewed/` | `state=more_info_needed` |
| Exclude current more-info submissions | Any list endpoint where state is not fixed | `exclude_state=more_info_needed` |

There is no direct query parameter for "ever had a more-info request but later
became accepted or rejected". For that, use `/api/v1/ai-review/reviewed/` and
inspect `internal_notes`.

## Common Filter Examples

```bash
# New unproposed builder submissions with URL evidence.
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/ai-review/?category=builder&exclude_empty_evidence=true"

# Pending submissions edited after a more-info request.
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/ai-review/?resubmitted_more_info=true"

# Active more-info proposals from AI or human stewards.
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/ai-review/proposed/?proposed_action=more_info"

# Active low-confidence AI proposals.
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/ai-review/proposed/?proposed_confidence=low&proposed_by=ai"

# Active proposals assigned to and proposed by a specific steward.
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/ai-review/proposed/?assigned_to=123&proposed_by=123&page_size=20"

# Exclude unassigned submissions and one steward's assigned submissions.
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/ai-review/?exclude_assigned_to=unassigned,123&page_size=20"

# Equivalent active-proposal query through the main list endpoint.
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/ai-review/?has_proposal=true&assigned_to=123&proposed_by=123&page_size=20"

# Reviewed AI-proposed submissions with final more-info state.
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/ai-review/reviewed/?state=more_info_needed"

# Include appealed submissions in the new-work list.
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/ai-review/?has_appeal=true"
```

## Endpoint Defaults And Conflicts

- `/api/v1/ai-review/` defaults to pending and unproposed. Proposal filters such as `has_proposal=true`, `proposed_by`, `proposed_action`, `proposed_confidence`, or `proposed_template` opt into active proposals.
- `/api/v1/ai-review/proposed/` is always pending active proposals from AI or human stewards. Use proposal filters there.
- `/api/v1/ai-review/reviewed/` is historical calibration data. Do not propose from it.
- Main `/api/v1/ai-review/` excludes appeals unless `has_appeal` is present.
- `state=accepted`, `state=rejected`, or `state=more_info_needed` does not make sense on main `/api/v1/ai-review/` because that endpoint starts from pending submissions.

## Minimal Decision Guidance

- Propose `reject` for unverifiable, duplicate, spam, generic, irrelevant, or no-work submissions.
- Propose `more_info` when the work might be valid but evidence is missing, broken, private, or unclear.
- Propose `accept` only for concrete, verifiable work. Use detail `min_points` and `max_points`.
- Use `high` confidence for obvious decisions, `medium` for likely decisions, and `low` for ambiguous decisions.

## Project Rubric Reviews

Submissions whose detail payload has `review_flow` set to `builder_project`
require a structured `rubric_review` object on proposal POST/PUT requests.
For this flow, `proposed_points` is optional because the final steward assigns
points manually from the rubric.

Always decide the gate first:

1. If any gate failure applies, propose `reject`.
2. If no gate failure applies and the project is valid, propose `accept`.
3. If the project might be valid but evidence is missing, private, broken, or
   ambiguous, propose `more_info`.

Gate failures force a reject proposal. If any gate failure applies, send
`proposed_action: "reject"`, a user-visible `proposed_staff_reply`, and
`rubric_review.overall_reason`. Do not send section scores for gate-failure
rejects; use `sections: {}`.

Passing Builder Projects usually use `proposed_action: "accept"` with all four
section scores. Do not send `proposed_points` for Builder Project accepts unless
you are explicitly instructed to; stewards assign final points from the rubric.

Use templates when possible. Fetch `/api/v1/ai-review/templates/`, find the
template by `label`, copy its `text` into `proposed_staff_reply`, and send its
`id` as `template_id`. The template `action` must match `proposed_action`.

Valid gate failure keys:

| Key | Meaning |
|---|---|
| `no_real_genlayer_contract` | No real GenLayer contract, deterministic-only contract, or fake off-chain AI consensus |
| `branding_only` | GenLayer is only branding and nothing actually calls a contract |
| `repo_does_not_build` | Repository does not build or work |
| `empty_fork_or_boilerplate` | Empty fork, plain fork, or renamed boilerplate example |

When the gate passes, score all four sections from 0 to 5. Section reasons are
optional; `overall_reason` is required.

The payload requires all four sections, but `frontend_ux` is a human-only
dimension: the portal hides the AI's `frontend_ux` score from stewards and a
human reviewer supplies the real one. Score it conservatively (it is not
displayed); put real effort into the other three.

Required section keys:

| Key | Section |
|---|---|
| `genlayer_fit` | GenLayer fit |
| `contract_quality` | Contract quality |
| `engineering` | Engineering |
| `frontend_ux` | Frontend / UX |

Optional verified extras:

| Key | Extra |
|---|---|
| `live_deployment` | Live deployment |
| `demo_video` | Demo video |
| `public_post` | Public post |

Template labels for gate-failure rejects:

| Gate failure key | Template label |
|---|---|
| `no_real_genlayer_contract` | `Reject: Project Has No Real GenLayer Contract` |
| `branding_only` | `Reject: GenLayer Is Branding Only` |
| `repo_does_not_build` | `Reject: Project Does Not Build` |
| `empty_fork_or_boilerplate` | `Reject: Empty Fork or Boilerplate` |

Fetch templates:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/ai-review/templates/"
```

Example gate-failure Project reject:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/api/v1/ai-review/{uuid}/propose/" \
  -d '{
    "proposed_action": "reject",
    "template_id": 123,
    "proposed_staff_reply": "Thanks for your submission. We could not accept this Builder Project because the repository does not build or the project does not work from the submitted evidence. Please resubmit with a working repository, setup instructions, and any deployment or demo evidence needed to verify it.",
    "confidence": "high",
    "reasoning": "The repository install/build path failed during review, so the project cannot be verified as working.",
    "rubric_review": {
      "gate_failures": ["repo_does_not_build"],
      "sections": {},
      "extras": [],
      "overall_reason": "The repository does not build from the submitted evidence."
    }
  }'
```

Example passing Project proposal:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/api/v1/ai-review/{uuid}/propose/" \
  -d '{
    "proposed_action": "accept",
    "confidence": "medium",
    "reasoning": "The repository passes the Project gate and has enough implementation evidence.",
    "synthesis": "## Overview\nA prediction-market dApp where a GenLayer contract adjudicates contested outcomes...\n\n## Strengths\n- Real non-deterministic contract logic...\n\n## Concerns\n- Thin test coverage; the resolution path is only exercised manually...",
    "rubric_review": {
      "gate_failures": [],
      "sections": {
        "genlayer_fit": {"score": 3, "reason": "The outcome is contested and trustless adjudication adds value."},
        "contract_quality": {"score": 2, "reason": "The contract has state and validates the meaningful result."},
        "engineering": {"score": 2, "reason": "The repo builds and has original project structure."},
        "frontend_ux": {"score": 1, "reason": "The UI is basic but wired to the contract."}
      },
      "extras": ["live_deployment"],
      "overall_reason": "Valid Project proposal with conservative section scores."
    }
  }'
```

## Error Meanings

| Status | Meaning |
|---:|---|
| 400 | Invalid body or invalid query value |
| 401 | Missing, invalid, expired, or revoked bearer token |
| 403 | Token lacks the required scope, or the proposal is not AI-created (PUT) |
| 404 | Submission not found, not pending, or no AI proposal exists for PUT |
| 409 | POST attempted when an active proposal already exists |
