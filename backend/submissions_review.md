# Submissions Review System

## Overview

AI-assisted review pipeline for GenLayer Testnet Program submissions. Processes 1,000+ pending community contributions using deterministic rules and AI classification via Claude (OpenRouter).

## Architecture

### Three Tiers

| Tier | Method | Auto-applies? | Human review? |
|------|--------|--------------|---------------|
| **Tier 1** | Deterministic rules | Yes (reject only) | No |
| **Tier 2 (HIGH confidence)** | AI via Claude | Yes (reject/more_info only) | No |
| **Tier 2 (MEDIUM/LOW)** | AI via Claude | No — creates proposal | Yes |
| **Tier 2 (accept)** | AI via Claude | Never — always proposal | Yes |
| **Auto-ban** | Post-batch check | Yes (ban user) | Appeal via in-app flow |

### AI Steward

- **User**: `genlayer-steward@genlayer.foundation` (migration: `stewards/migrations/0006_create_ai_steward.py`)
- **Permissions**: Full steward permissions on all contribution types
- **Visibility**: `visible=False` (hidden from leaderboard/public)

### Review Templates

31 templates in `stewards_reviewtemplate` covering rejection, more-info, and acceptance scenarios. Templates will be added to a data migration once finalized.

## Tier 1: Deterministic Rules

Rules that auto-reject with 100% confidence. Evaluated in order; first match wins.

| # | Rule | What it catches | Impact |
|---|------|-----------------|--------|
| 1 | `rule_no_evidence_no_notes` | Zero evidence + blank notes | 9 |
| 2 | `rule_no_evidence_short_notes` | Zero evidence + notes <=10 chars | 38 |
| 3 | `rule_spam_notes` | Notes match spam wordlist or non-alpha gibberish | ~5 |
| 4 | `rule_duplicate_pending_from_same_user` | Older pending submission with identical notes from same user | 27 |
| 5 | `rule_resubmitted_rejected_url` | Same user resubmits a previously-rejected URL | 25 |
| 6 | `rule_same_url_reused_by_same_user` | Same URL in another pending submission by same user | 24 |
| 7 | `rule_blocklisted_evidence_url` | Generic platform URLs as sole evidence (studio, points site) | 11 |
| 8 | `rule_cross_user_duplicate_url` | Non-repo URL submitted by a different user (copy-paste) | 1 |
| 9 | `rule_cross_user_identical_notes` | Same notes (>20 chars) used by a different user (farming) | 0* |

**Current impact**: 135 out of 1,114 pending submissions (12.1%).

*Rule 9 catches 0 currently because the farming templates have minor variations.

### Anti-Gaming Detection (Analysis Findings)

Deep analysis of the submission database revealed these gaming patterns:

| Pattern | Pending affected | Detection method |
|---------|-----------------|------------------|
| No evidence at all | 220 (20.2%) | Caught by rules 1-2 |
| Same-user URL reuse | 62 (5.7%) | Caught by rules 5-6 |
| Previously-rejected URL resubmission | 28 | Caught by rule 5 |
| Cross-user identical tweet URLs | 11 | Caught by rule 8 |
| Blocklisted platform URLs | 11 | Caught by rule 7 |
| High-rejection users (80%+ rate, 5+ rejections) | 53 (4.9%) | Auto-ban + AI context |
| Sybil farm clusters (e.g., 5 "rahimi" accounts) | ~19 | Tier 2 AI context |
| Bulk submitters (4+ pending) | 332 (30.5%) | Tier 2 AI context |
| Submission velocity (5+/day) | 72 | Tier 2 AI context |

### Blocklisted URLs

Generic platform pages that are never valid evidence:
- `studio.genlayer.com/run-debug*`
- `studio.genlayer.com/contracts*`
- `points.genlayer.foundation*`
- `genlayer.com` / `www.genlayer.com`

**Not included** in Tier 1 (by design):
- Duplicate GitHub repo URLs — can be resubmitted after new commits
- Contribution types with 0% acceptance — may accept in the future

### Adding New Rules

Add a function to `TIER1_RULES` in `review_submissions.py`:

```python
def rule_my_new_rule(submission, evidence_items):
    """Description of what this catches."""
    if some_condition:
        return ('Template Label', 'CRM note explaining why')
    return None

TIER1_RULES = [
    ...existing rules...,
    rule_my_new_rule,
]
```

## User Ban System

### How It Works

Users who repeatedly submit low-quality/spam content get automatically banned from submitting. They can appeal once via an in-app form.

### Auto-Ban

After each batch run, the `review_submissions` command checks for users meeting the auto-ban threshold:
- **5+ total rejections** AND **0 acceptances** (100% rejection rate)
- Sets `is_banned=True` with reason explaining the rejection count
- `banned_by` set to the AI steward user
- Runs at the end of each batch (not per-submission)
- **Current impact**: 46 users would be auto-banned from the production snapshot

### Manual Ban

Admins can ban/unban users via:
- **Admin panel**: `is_banned` field in User admin, plus bulk actions "Ban selected users" / "Unban selected users"
- **Future**: Steward UI for ban management

### User Model Fields

```python
# users/models.py
is_banned = BooleanField(default=False)
ban_reason = TextField(blank=True)       # Shown to user
banned_at = DateTimeField(null=True)
banned_by = ForeignKey(User, null=True)  # Who banned them
```

### Ban Appeal Flow

1. Banned user sees ban status + reason on their profile (`GET /api/v1/users/me/` returns `is_banned`, `ban_reason`)
2. User submits **one-time appeal** via `POST /api/v1/users/me/appeal/` with `appeal_text`
3. System returns 409 if appeal already exists (one per user)
4. Stewards review appeals via `GET /api/v1/steward-submissions/ban-appeals/` (filterable by status)
5. Steward approves or denies via `POST /api/v1/steward-submissions/ban-appeals/{id}/review/`
6. If approved: user is unbanned (all ban fields cleared)
7. If denied: user stays banned, no further appeals possible

### Ban Appeal Model

```python
# users/models.py
class BanAppeal(BaseModel):
    user = FK(User)
    appeal_text = TextField
    status = CharField: pending / approved / denied
    reviewed_by = FK(User, null)
    reviewed_at = DateTimeField(null)
    review_notes = TextField(blank)
```

### API Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/v1/users/me/appeal/` | GET | User | Get appeal status |
| `/api/v1/users/me/appeal/` | POST | User | Submit appeal (banned users only, once) |
| `/api/v1/steward-submissions/ban-appeals/` | GET | Steward | List appeals (filter by ?status=pending) |
| `/api/v1/steward-submissions/ban-appeals/{id}/review/` | POST | Steward | Approve or deny appeal |

### Submission Blocking

Banned users get HTTP 403 when trying to create submissions (`SubmittedContributionViewSet.create()`):
```json
{"error": "Your account has been suspended due to repeated policy violations. You may submit one appeal from your profile page."}
```

## Tier 2: AI Classification (Claude via OpenRouter)

### How It Works

For each submission:
1. Builds context: notes, evidence URLs, contribution type, user history + rejection rate + spam signals
2. Loads few-shot examples from same contribution type (5 accepted + 5 rejected)
3. Calls Claude via OpenRouter API (with retry on parse errors, max 2 retries)
4. Returns structured JSON with action, template, confidence, reasoning, flags

### Spam Signals (Fed to AI Context)

The AI receives additional signals about suspicious patterns:
- **Submission velocity**: Warning if user submitted 5+ on the same day
- **Bulk submitter**: Warning if user has 8+ pending across N types
- **Suspicious email**: Warning if email contains "airdrop"
- **Rejection rate**: Shown with warning flag at 80%+ (3+ reviewed)

### AI Response Schema

```json
{
    "action": "accept | reject | more_info",
    "template_id": 5,
    "staff_reply": "Personalized message based on template",
    "points": 3,
    "confidence": "high | medium | low",
    "reasoning": "Internal reasoning for CRM note",
    "flags": ["ai_generated", "plagiarism", "low_effort", "wrong_type", "duplicate"]
}
```

### Decision Matrix

| Confidence | Action | Result |
|-----------|--------|--------|
| HIGH | reject | Direct rejection (auto-applied) |
| HIGH | more_info | Direct more_info request (auto-applied) |
| HIGH | accept | Proposal (human review required) |
| MEDIUM/LOW | any | Proposal (human review required) |

### Cost Tracking

The command tracks and reports per-run:
- Input/output tokens
- Total USD cost
- Per-submission cost

### Model Options

| Model | Cost/submission | Quality | Use for |
|-------|----------------|---------|---------|
| `anthropic/claude-opus-4.6` | ~$0.023 | Best | Default, full review |
| `anthropic/claude-sonnet-4.6` | ~$0.012 | Good | Cost-effective alternative |
| `anthropic/claude-haiku-4.5` | ~$0.002 | Basic | Future pre-filter |

### Tested Performance (100-submission batch)

| Outcome | Count | % |
|---------|-------|---|
| Tier 1 auto-reject | 22 | 22% |
| Tier 2 HIGH reject (auto) | 37 | 37% |
| Tier 2 HIGH more_info (auto) | 5 | 5% |
| Tier 2 MEDIUM reject (proposal) | 16 | 16% |
| Tier 2 MEDIUM accept (proposal) | 18 | 18% |
| Tier 2 MEDIUM more_info (proposal) | 2 | 2% |

**64% auto-actioned**, 36% proposals for human review.

Tested across all contribution types: Educational Content, Tools & Infrastructure, Community Building, Blog Post, Documentation, Research & Analysis, Adversarial Testing, Projects & Milestones, 3rd Party Integrations.

## Management Command Usage

```bash
# Dry run (see what would happen)
python manage.py review_submissions --dry-run

# Tier 1 only
python manage.py review_submissions --tier1-only

# Tier 2 only
python manage.py review_submissions --tier2-only

# Specific batch size
python manage.py review_submissions --batch-size 50

# Filter by contribution type
python manage.py review_submissions --type "Educational Content"

# Single submission
python manage.py review_submissions --submission-id <uuid>

# Override model
python manage.py review_submissions --model anthropic/claude-sonnet-4.6
```

## Environment Variables

```
OPENROUTER_API_KEY=sk-or-v1-...   # Required for Tier 2
```

## AWS Deployment (Planned)

- **EventBridge** scheduled rule (e.g., every 6 hours)
- **ECS RunTask** on the existing App Runner container
- Runs: `python manage.py review_submissions --batch-size 100`
- `OPENROUTER_API_KEY` stored in SSM Parameter Store

## Files

| File | Purpose |
|------|---------|
| `contributions/management/commands/review_submissions.py` | Main management command |
| `stewards/migrations/0006_create_ai_steward.py` | AI steward user + permissions |
| `users/models.py` | `is_banned`, `ban_reason`, `banned_at`, `banned_by` fields + `BanAppeal` model |
| `users/migrations/0017_user_ban_fields.py` | Migration for ban system |
| `users/serializers.py` | `BanAppealSerializer`, `BanAppealReviewSerializer` |
| `users/views.py` | Appeal create/get endpoints |
| `users/admin.py` | Ban admin, BanAppeal admin, bulk ban/unban actions |
| `contributions/views.py` | Banned user submission block + steward appeal review endpoints |
| `leaderboard/models.py` | Fixed `raw=True` check in signals for loaddata |
| `.env` | `OPENROUTER_API_KEY` (gitignored) |

## Data Analysis (Feb 25, 2026 snapshot)

- **12,191 users**, **3,295 submissions** (1,087 pending)
- **593 pending** are "Educational Content" (mostly tweets)
- **135** auto-rejectable by Tier 1 rules (12.1%)
- **46** users auto-bannable (5+ rejections, 0 acceptances)
- **~640** auto-actionable by Tier 1 + Tier 2 HIGH (est. 64%)
- **~395** proposals for human review (est. 36%)
- Estimated total Tier 2 cost: ~$22 (979 submissions x $0.023)
- Top spam patterns: empty/short notes, URL reuse, previously-rejected URLs, blocklisted platform URLs
- October 2025 spam wave: 10x spike in submissions
- 87% of users have 0% acceptance rate
- Sybil farm detected: 5 "rahimi" accounts with identical submission patterns

---

## Future Enhancements

### URL Content Fetching

Fetching actual content from evidence URLs to give the AI reviewer much richer context for classification. This is the highest-impact improvement for review accuracy.

#### GitHub Repos

**Goal**: Detect README-only repos, verify actual code exists, assess project quality.

**Implementation plan**:
1. **API**: Use GitHub REST API (public, no auth needed for public repos; use OAuth token for higher rate limits)
2. **Data to fetch**:
   - Repository metadata: stars, forks, language breakdown, created_at, last push date
   - File tree: list of files (detect README-only repos with 0 code files)
   - README.md content: extract for AI context
   - Commit count and recent activity
3. **Signals to extract**:
   - `is_readme_only`: True if repo has only README.md (or < 3 files total)
   - `has_code`: True if any `.py`, `.js`, `.ts`, `.sol`, etc. files exist
   - `commit_count`: Total commits (1 commit = likely generated)
   - `last_push_days_ago`: Days since last push
   - `language_breakdown`: Percentage of languages (detect empty/docs-only repos)
4. **Integration**: Call before AI classification, include in user message:
   ```
   ## GitHub Repo Analysis
   - Files: 3 (.py: 2, README.md: 1)
   - Commits: 5 (last push: 2 days ago)
   - Stars: 0, Forks: 0
   - README excerpt: (first 500 chars)
   ```
5. **Rate limiting**: GitHub allows 60 requests/hour unauthenticated, 5000/hour with token. At 100 submissions/batch, this is well within limits.

#### Blog Posts (Medium, Dev.to, personal blogs)

**Goal**: Verify article exists, assess depth and originality.

**Implementation plan**:
1. **Method**: HTTP GET with appropriate User-Agent, parse HTML to extract article text
2. **Libraries**: `requests` + `beautifulsoup4` (already available) or `trafilatura` for article extraction
3. **Data to fetch**:
   - Article title and full text
   - Word count
   - Publication date
   - Author name (cross-check with submitter)
4. **Signals to extract**:
   - `word_count`: Short articles (< 300 words) are likely low-effort
   - `mentions_genlayer`: Does the article actually mention GenLayer?
   - `is_accessible`: Can we actually reach the URL?
   - `content_excerpt`: First 500 chars for AI context
5. **Edge cases**: Medium paywalled articles, deleted posts, geo-blocked content
6. **Integration**: Include article excerpt + metadata in AI prompt

#### X/Twitter Posts

**Goal**: Verify tweet exists, assess engagement and thread depth.

**Implementation plan**:
1. **Method**: Use Twitter/X embed API (`publish.twitter.com/oembed`) or `nitter` instances for scraping
2. **Data to fetch**:
   - Tweet text
   - Is it a thread? (multiple tweets)
   - Engagement: likes, retweets, replies (if available)
   - Author handle (cross-check with submitter's twitter_handle)
3. **Signals to extract**:
   - `is_thread`: Thread vs single tweet
   - `tweet_length`: Character count
   - `engagement_score`: likes + retweets
   - `mentions_genlayer`: Does tweet mention GenLayer?
4. **Challenges**: X API is increasingly locked down. Alternatives:
   - Twitter embed endpoint (free, returns HTML)
   - Nitter instances (third-party, may be unreliable)
   - Twitter API v2 (paid, $100/month minimum)
5. **Recommendation**: Start with embed API for basic tweet text, escalate to paid API only if needed

#### Architecture

```
contributions/
  content_fetcher.py          # URL content fetching module
  models.py                   # Add EvidenceContent model for caching

# EvidenceContent model
class EvidenceContent(BaseModel):
    evidence = FK(Evidence)
    url = URLField
    content_type = CharField  # github_repo, blog_post, tweet, unknown
    raw_content = TextField   # Fetched content
    metadata = JSONField      # Structured data (word_count, stars, etc.)
    fetched_at = DateTimeField
    fetch_error = TextField(blank)  # Error message if fetch failed
```

**Caching strategy**: Fetch once per URL, store in `EvidenceContent`. Re-fetch if older than 7 days. Skip URLs that previously failed (retry after 30 days).

**Cost impact**: No API costs (public endpoints). Adds ~0.5s per URL to processing time. Content included in AI prompt increases token count by ~$0.002/submission.

### Embeddings-Based Similarity Detection

**Goal**: Detect near-duplicate submissions across users (Sybil farms, copy-paste with minor word changes).

**Implementation plan**:
1. **Embedding model**: Use OpenRouter to call an embedding model (e.g., `openai/text-embedding-3-small` at $0.02/1M tokens)
2. **What to embed**: Submission notes + fetched evidence content (once URL fetching is implemented)
3. **Storage options**:
   - **pgvector** extension on PostgreSQL (production already uses Postgres)
   - **SQLite vec** for local development
   - **Separate vector DB** (Pinecone, Qdrant) if scale demands it
4. **Similarity search**: For each new submission, find top-5 most similar existing submissions
5. **Cross-user detection**: Flag when two different users have > 0.9 cosine similarity on notes
6. **Sybil cluster detection**: Build a similarity graph, find connected components with > 3 users

**Estimated cost**: ~$0.50 to embed all 3,295 existing submissions. ~$0.001 per new submission.

**Dependencies**: Requires URL content fetching to be most effective. Can start with notes-only embeddings.

### Other Planned Improvements

- [ ] Haiku pre-filter for cost optimization
- [ ] Frontend validation to prevent empty submissions at submission time
- [ ] Real-time Tier 1 rules on submission creation (reject before saving)
- [ ] Data migration for review templates
- [ ] Rate limiting at API level (flag at 5+ submissions/day, block at 10+)
- [ ] Sybil detection via email clustering + submission pattern overlap
- [ ] User reputation score displayed in steward review UI
- [ ] Steward UI for ban management (beyond admin panel)
- [ ] Frontend ban appeal form on user profile/dashboard
