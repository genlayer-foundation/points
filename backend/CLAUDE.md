# Backend Quick Reference - Django Structure

## 📝 MAINTENANCE INSTRUCTIONS
**IMPORTANT**: Keep this file updated when you:
- Add new API endpoints - update the "API Endpoints Summary" section
- Create new models - add to relevant app section with location
- Add new apps - update "Project Structure" and create new section
- Change authentication flow - update "Authentication Flow" section
- Add new environment variables - update "Environment Variables" section
- Create new ViewSets or serializers - add to relevant app section
- Change URL patterns - update endpoint paths
- Add new commands or scripts - update "Common Commands" section

**Quick update checklist:**
```bash
# After making changes, check:
- [ ] New endpoints added to API Endpoints Summary?
- [ ] New models documented with file locations?
- [ ] New serializers listed in app sections?
- [ ] Environment variables documented?
- [ ] URL pattern changes reflected?
```

## Project Structure
```
backend/
├── api/                    # Core API app
├── contributions/          # Contribution tracking
├── leaderboard/           # Leaderboard and rankings
├── social_connections/    # OAuth (GitHub, Twitter, Discord) + encrypted token storage
├── social_tasks/          # Repeatable social tasks (follow, join, like) and completions
├── users/                 # User management and auth
├── partners/              # Ecosystem partners directory
├── gen_tv/                # Gen TV livestream index
├── notifications/         # Portal notification system
├── service_accounts/      # Machine identities + scoped bearer tokens (AI review agent)
├── utils/                 # Shared utilities
└── tally/                 # Django project settings (settings.py, urls.py)
```

## Key Files & Locations

### User Management
- **Models**: `users/models.py`
  - User model with email auth, name, address fields
  - Validator model with node_version field (OneToOne with User)
  - Custom UserManager for email-based auth
- **Views**: `users/views.py`
  - `/api/v1/users/me/` - GET/PATCH current user profile (name/description/website/socials editable; node_version is NOT editable — Grafana-sourced, display only)
  - `/api/v1/users/by-address/{address}/` - Get user by wallet address
  - `/api/v1/users/validators/` - Get validator list from blockchain
- **Serializers**: `users/serializers.py`
  - UserSerializer - Full user data including validator info
  - ValidatorSerializer - Validator node version and target matching
  - UserProfileUpdateSerializer - Allows name/description/website/socials updates (node_version removed — Grafana is source of truth)
  - UserCreateSerializer - Registration

### Authentication
- **Views**: `api/views.py`
  - `/api/auth/nonce/` - Get nonce for SIWE
  - `/api/auth/login/` - Login with signed message
  - `/api/auth/verify/` - Verify auth status
  - `/api/auth/logout/` - Logout
- **Settings**: `backend/settings.py`
  - JWT auth configuration
  - CORS settings for frontend
  - Session-based auth with SIWE

### Contributions
- **Models**: `contributions/models.py`
  - Contribution - Individual contribution records. Has optional `project_contribution` self-FK and `milestone_version` used by the Projects/Milestones split.
  - ContributionType - Categories with slug field, M2M `accepted_evidence_url_types`, optional global lifetime `max_submissions`, and optional `max_submissions_per_user_per_week`. The weekly limit uses Monday-Sunday UTC `SubmittedContribution.created_at` bounds and counts every state; edits/appeals reuse the same row and do not consume another slot. If an editable submission changes contribution type, the target type's capacity is checked in the submission's original creation week. `requires_ai_review` gates unengaged pending submissions from tier-1 stewards, while `escalation_threshold_points` converts tier-1 accepts whose contribution-date multiplied points meet the threshold into proposals. Migration 0084 backfills Builder-category types once; new Builder types default to `True` / `400` for values not supplied explicitly, and later explicit admin/model updates remain unchanged.
  - AIReviewFeedback - Per-reviewer, per-AI-proposal benchmark feedback with an immutable `(proposal_source, proposal_source_id)` binding, timestamp metadata in `proposal_ref`, verdict, optional corrected decision/rubric ranges, typed anchored error claims, and a best-effort commit SHA pinned on first save. Records are unique by `(submitted_contribution, reviewer, proposal_source, proposal_source_id)` and never alter submission review state.
  - SubmissionStateTransition - Append-only lifecycle log for submissions (migration 0079). One row per event (`submitted`/`review`/`bulk_reject`/`gate_reject`/`edited`/`canceled`/`appeal`/`evidence_added`/`escalated`/`admin`) with from_state/to_state/actor. Written by every path that changes `state` or clears `reviewed_by`/`reviewed_at` (creation via post_save signal; the rest inline at each call site, incl. the Tier-1 gate command and admin `save_model`). Never mutate or delete rows; read-only in admin. Rationale: row state is overwritten in place and re-open paths destroy review fields, so this log is the only durable decision/lifecycle history. Bulk reject also writes a per-submission decision SubmissionNote (`data.action='reject'`, `data.bulk=true`) so bulk decisions appear in the CRM timeline and note-based metrics like single rejects. The dead `resubmitted_more_info` filter (relied on `reviewed_at` surviving edits, impossible since 2026-06-22) was removed from both filtersets and the steward search grammar.
  - Human review hierarchy - `Steward.tier` is reviewer (1), top-level (2), or apex (3); steward superusers act as tier 3. Tier 2+ gets the full permission matrix and unrestricted submission visibility. `SubmittedContribution.escalated_at` marks an active threshold proposal and is exposed only through the steward serializer. Tier-1 AI-gated visibility accepts durable AI proposal notes/rows, any active proposal, appeals, and transition-backed more-info resubmissions. Search supports `is_escalated`; the portal grammar maps `is:escalated` / `not:escalated`.
- **Projects/Milestones split**: `contributions/project_milestones.py`
  - `projects` and `milestones` are separate contribution types (migration 0068). Projects require a GitHub repository evidence URL (`required_evidence_url_types` = github-repo). New milestones must be linked to one of the submitter's HIGHLIGHTED Projects CONTRIBUTIONS (`/submissions/accepted-projects/`) via the `project_contribution` self-FK, require a written change description (evidence optional), and get an auto-assigned sequential `milestone_version` per project contribution. Existing pending/more-info milestone links are grandfathered if the project is not highlighted or its highlight is removed, so they remain editable and reviewable; new links still require a highlight. IMPORTANT: this is unrelated to the projects app's curated `projects.Project` showcase table and its `show_in_overview` field, which contribution flows must never create or modify.
  - FeaturedContent - Portal hero/community/validator-steward content managed through admin
  - ContributionTypeMultiplier - Dynamic point multipliers
  - Evidence - Evidence items with `url_type` FK for auto-detected URL type, `normalized_url` indexed field for fast duplicate detection (text descriptions and URLs only - file uploads are disabled)
  - EvidenceURLType - Defines URL type categories (X Post, GitHub PR, etc.) with regex patterns for auto-detection and handle ownership validation
- **URL Utilities**: `contributions/url_utils.py`
  - `normalize_url()` - Enhanced URL normalization (strips tracking params, preserves essential params)
  - `detect_url_type()` - Auto-detects URL type from regex patterns
  - `extract_handle()` - Extracts handle/owner from URL for ownership checks
  - `validate_handle_ownership()` - Validates URL handle matches user's linked social account
  - `check_duplicate_url()` - Checks for duplicate URLs across submissions
- **reCAPTCHA**: `contributions/recaptcha_field.py`
  - Custom DRF serializer field for Google reCAPTCHA v2 validation
  - Validates tokens from frontend reCAPTCHA widget
  - Required for new contribution submissions only (not for edits)

### Projects
- **Models**: `projects/models.py`
  - Project - Project profile with website/GitHub links, description, usage notes, details, media, participants, and related accepted contributions
  - ProjectMetric - Admin-managed title/value/detail metric rows for project pages
  - ProjectPageRevision - Owner-submitted ordered page blocks rendered through whitelisted portal components
- **AI Review**: `contributions/ai_review/views.py`
  - `/api/v1/ai-review/` - List pending unproposed submissions for the external AI review agent, including appeals by default; `has_appeal=false` excludes appeals, `has_more_info_request=true` selects submissions with recorded request blocks, and `is_more_info_resubmitted=true` selects audited resubmissions
  - `/api/v1/ai-review/{id}/` - Retrieve a pending submission with evidence and user history
  - `/api/v1/ai-review/{id}/propose/` - Submit an AI proposal for human approval
  - `/api/v1/ai-review/proposed/` - List pending submissions with active proposals awaiting steward review; use `proposed_by=ai` for AI-created proposals only
  - `/api/v1/ai-review/reviewed/` - List reviewed submissions that had AI proposals for calibration
  - `/api/v1/ai-review/feedback/` - Paginated structured steward feedback deterministically ordered by `(updated_at, id)`; incremental consumers must follow the documented overlap/count/dedupe/retry protocol. Filters: `updated_after` (inclusive despite the legacy name, so equal-timestamp changes overlap) and `submission` UUID.
  - **Feedback pull consistency**: keep the previous `updated_after` cursor while reading every `next` page; within a scan require `count` to remain stable and the number of unique record IDs to equal `count`, otherwise discard the scan and retry from that cursor. Across completed scans, expect the inclusive boundary to repeat records and upsert/deduplicate them by feedback `id`. Advance the cursor to the maximum `updated_at` only after a complete validated scan.
  - `/api/v1/ai-review/templates/` - List review templates available to the AI review agent
  - **Auth**: service account bearer tokens (`Authorization: Bearer sa_<id>_<secret>`) with scopes `ai_review:read` (all GETs) and `ai_review:propose` (propose). Proposals are attributed to the hidden AI steward user (`contributions/ai_attribution.py:get_ai_steward()`, `genlayer-steward@genlayer.foundation`); the authenticating account's name is recorded in the proposal note's `data.service_account` for audit. The old `X-AI-Review-Key` shared key has been removed; tokens are the only way in.
  - **Appeals**: both AI stages process appeals. The deterministic command marks them `gate_reviewed` but never auto-rejects them; the proposal API includes them by default. More-info resubmissions remain available to both stages as well.
- **AI feedback validation**: `contributions/ai_feedback.py`
  - Closed verdict/decision/error-claim vocabularies, exact criterion correction shapes, proposal binding, and first-save GitHub repository HEAD lookup. Commit lookup uses `GITHUB_METRICS_TOKEN` when configured, degrades to an empty SHA without blocking feedback, and is not repeated on record revisions.
  - `GET|POST /api/v1/steward-submissions/{id}/ai-feedback/` lists all feedback for a visible submission or creates/revises the current steward's record. Creates omit `expected_updated_at`; revisions must echo the record's current `updated_at` and receive 409 on a stale version. The same per-type permission bar as CRM notes applies, including propose-only stewards.

### Service Accounts

- **App**: `service_accounts/` provides machine identities for server-to-server API access. No HTTP API of its own.
- **Models**: `ServiceAccount` (name, description, is_active; acts as the DRF request principal; it is NOT a User and can never become a session) and `ServiceAccountToken` (unique non-secret `identifier`; unique SHA-256 `digest` of the plaintext, which is never stored; `scopes` list; `expires_at`/`revoked_at`/`last_used_at`, with `last_used_at` writes throttled to once per minute).
- **Auth class**: `service_accounts.authentication.ServiceAccountAuthentication` parses `Bearer sa_<id>_<secret>`, looks up the token by non-secret id, compares digests in constant time, rejects expired/revoked/inactive with a generic 401. Non-`sa_` credentials pass through to other authenticators.
- **Permission**: `service_accounts.permissions.HasServiceAccountScope`; views declare `required_scopes = {'<action>': '<scope>', '*': '<default>'}`.
- **Issue a token**: Django admin Service account change page -> "Issue token", or `python manage.py issue_service_account_token <account> --scopes <scope>... [--expires-days N]`; plaintext is shown exactly once. Rotate = issue new + revoke old (admin action on Service account tokens); kill switch = deactivate the account.
- **Tests**: `service_accounts/tests/`; test helper `service_accounts.testing.service_account_auth_headers()` returns client auth kwargs.

### Node Upgrade (Sub-app)
- **Models**: `contributions/node_upgrade/models.py`
  - TargetNodeVersion - Active target version for node upgrades. Per-network, single
    `is_active` per network. The version-shame grace period — how many days after
    `target_date` a node still behind is marked version "shame" — is the global
    `settings.NODE_VERSION_SHAME_GRACE_DAYS` (default 3, env-overridable), not a per-target field.
- **Version verdict**: `validators/version_status.py::compute_version_status(wallet, target, now, node_version=...)`
  is the shared helper (used by the Wall of Shame view and the Grafana sync) that returns
  `on`/`warning`/`shame`/`unknown` using the `NODE_VERSION_SHAME_GRACE_DAYS` setting. The viewset's
  `ValidatorWalletViewSet._version_context` delegates to it; the Grafana sync passes the
  Prometheus-observed version explicitly.
- **Node versions are Grafana-sourced.** Target creation and the `node-upgrade` award are
  driven automatically by the Grafana sync (`GrafanaValidatorStatusService._sync_node_versions`
  / `_award_node_upgrade`); the portal no longer lets users edit their node version. The old
  `NodeVersionMixin.save()` auto-submission path has been removed — `NodeVersionMixin` now only
  holds the version fields + validation + comparison helpers, and `calculate_early_upgrade_bonus`
  (reused by the Grafana award). Dedup on the `version {v} [{network}]` notes key is preserved.
- **Admin**: `contributions/node_upgrade/admin.py`
  - TargetNodeVersion admin interface
- **Views**: `contributions/views.py`
  - `/api/v1/contributions/` - CRUD for contributions
  - `/api/v1/contribution-types/` - Contribution type management
  - `/api/v1/contribution-types/statistics/` - Stats per type

### Leaderboard
- **Models**: `leaderboard/models.py`
  - LeaderboardEntry - User rankings with total points
  - GlobalMultiplier - System-wide multipliers
  - MultiplierPeriod - Time-based multiplier changes
- **Views**: `leaderboard/views.py`
  - `/api/v1/leaderboard/` - Get rankings
  - `/api/v1/leaderboard/monthly/` - Top portal point totals for the current month by default, or for an explicit `start_date`/`end_date` range. Combines all category contributions (including onboarding/link awards) with social-task completions and returns `contribution_points`, `social_task_points`, and `total_points`. Non-community categories keep their normal leaderboard eligibility gate. Cumulative Discord chat XP is not included because it has no earning-event timestamp for monthly attribution.
  - `/api/v1/leaderboard/community-podium/` - Community dashboard podium only. Returns at most three visible users ranked by `Contribution.frozen_global_points` from Contributions linked to accepted `SubmittedContribution.converted_contribution` rows. Discord/MEE6 XP, social-task completions, and direct/system/admin Contributions without an accepted source submission do not count.
  - `/api/v1/leaderboard/stats/` - Global statistics
  - `/api/v1/leaderboard/user_stats/by-address/{address}/` - User-specific stats
- **Builder leaderboard eligibility is write-time**: a `type='builder'` LeaderboardEntry
  exists iff the user has a Builder profile AND ≥1 builder-category contribution whose
  slug is not in `BUILDER_LEADERBOARD_ELIGIBILITY_EXCLUDED_CONTRIBUTION_TYPE_SLUGS`
  (`has_eligible_builder_contribution` in `leaderboard/models.py`; same predicate inline
  in `recalculate_all_leaderboards`). Reads never filter — no per-request Exists — so
  stored ranks are contiguous over exactly the displayed set and `LeaderboardEntry` has a
  `(type, rank)` index for the page query. Excluded-slug and social-task points still
  count toward the total once eligible; ineligible builders' earned builder points
  surface via profile stats and the `BuilderSerializer.get_total_points` fallback.
  `social_tasks/0006` backfilled the `star-genlayer-boilerplate` completion (25 pts) to
  all pre-existing Builders and ran one full recalculation.
- **Social-task plumbing**: `calculate_category_points` and `calculate_waitlist_points` sum
  `Contribution.frozen_global_points` AND `social_tasks.SocialTaskCompletion.points_awarded`
  for the matching category. The `update_leaderboard_on_social_task_completion` post_save
  handler is wired in `social_tasks/apps.py:ready()`.
  All social-task reads in `leaderboard/models.py` go through the `_social_tasks_ready()`
  guard: old data migrations (e.g. contributions 0051) call `recalculate_all_leaderboards()`
  while replaying history on a fresh database, before `social_tasks` 0001 has run — the
  guard makes completions read as empty until the table exists (a try/except would abort
  the surrounding PostgreSQL migration transaction).
  The community leaderboard ranking (`community_xp.utils.effective_community_ranking_queryset`)
  uses the same effective total as community profiles and aggregate stats: MEE6 XP plus
  contribution and community social-task points not covered by the applied MEE6 baseline.
  Pending social-task points count immediately; after steward distribution they remain pending
  until a newer MEE6 snapshot contains them, then roll into the baseline without double counting.
  Builder/validator category task points feed their stored leaderboard totals directly.

### Social Tasks
- **Models**: `social_tasks/models.py`
  - SocialTask - CMS row admins manage. Fields: name, slug, description, category (FK,
    restricted by clean() to the surfaced categories community/builder/validator —
    see SURFACED_CATEGORY_SLUGS), points, verification_type (slug of a registered
    verifier), typed target_* fields (only the ones used by a current verifier —
    today: `target_handle`, `target_guild_id`, `target_repo`), action_url (optional:
    save() derives it from the verifier when blank, e.g. the GitHub repo page or an
    X follow-intent link; clean() requires it for verifiers that cannot derive),
    cta_text, platform (derived from verifier on save), is_active, starts_at,
    ends_at, order (admin sort within the lists; list_editable). Add new target_*
    fields in the same migration as the verifier that needs them; the admin
    "Verification targets" fieldset picks up `target_*` model fields automatically.
    The changelist shows a per-task Completions count.
  - `SocialTask.clean()` validates the typed target field(s) required by the chosen
    verifier; raises ValidationError otherwise. The admin dropdown for
    verification_type is rendered from the registry, so new verifiers show up
    automatically.
  - SocialTaskCompletion - Per-user completion. unique_together (user, task).
    Stores points_awarded + verification_type snapshot + verification_data audit.
- **Discord XP integration**: community-category completions get a
  `contributions.ContributionDiscordXPState` row (post_save signal in
  `contributions/models.py`, registered with the lazy string sender
  `'social_tasks.SocialTaskCompletion'` to avoid a circular import), so they
  surface in the steward Discord XP view (`/api/v1/steward-discord-xp/`)
  alongside community contributions as XP to distribute manually. The state
  model holds exactly one source (`contribution` XOR `social_task_completion`,
  DB check constraint); `target_amount` reads `frozen_global_points` or
  `points_awarded` accordingly. Detail actions (`record-copy`,
  `mark-distributed`, `unset-distributed`) are keyed by the **state id** (not
  contribution id). These mutations share the MEE6 fetch/apply lock and return
  409 while a sync is active; applied snapshots reject any distribution at or
  after `run.started_at`, the conservative boundary that covers every fetched
  page. Manual admin apply acquires the same lock. Stewards with 'accept'
  permission on any community contribution type can manage social-task XP rows. Migration
  `contributions/0069` backfills states for pre-existing community completions.
- **Verifier registry**: `social_tasks/verifiers/` package
  - `base.py` exposes `Verifier` base class, `VerifierResult` dataclass, `@register`
    decorator, and dispatch helpers: `verify(task, user)`, `get_choices()`,
    `required_fields_for()`, `platform_for()`, `requires_verification_for()`,
    `required_connection_for()`.
  - One file per verification logic: `twitter_follow.py`, `discord_guild_join.py`,
    `github_star.py`, `click_through.py`. Each self-registers via `@register` and
    declares `verification_type`, `label`, `platform`, `required_fields`,
    `requires_verification`, and `required_connection` (which linked social
    account the verifier needs: 'twitter' / 'discord' / 'github' / None).
    Verifiers can also override `clean_task(task)` for admin-time validation
    beyond field presence (e.g. github_star validates the owner/repo format).
  - To add a new logic (e.g. github_star): create
    `social_tasks/verifiers/github_star.py`, declare a `Verifier` subclass with
    `@register`, implement `verify(task, user) -> VerifierResult`, import it from
    `verifiers/__init__.py`. Model.clean(), admin dropdown, serializer flag, and
    view dispatch pick it up automatically with no further central edits.
  - `twitter_follow` calls Sorsa via `social_tasks/sorsa_client.py:SorsaClient.is_following`.
  - `discord_guild_join` makes the Discord API call inline (not via
    `DiscordOAuthService.check_guild_membership`, which collapses all non-200
    cases into `False`). It distinguishes 200 (member), 404 (not member),
    401/403 (token expired), and 429/5xx / transport errors
    (-> `verification_unavailable`). On 401/403 it first attempts one
    `DiscordOAuthService.refresh_stored_access_token` rotation and retries
    (Discord user tokens expire after ~7 days), so long-linked users are not
    funneled into a re-link flow; only when the refresh itself is impossible
    (missing/invalid refresh token) does it return
    `token_invalid_relink_required`. It only writes back to
    `DiscordConnection.guild_member` when the checked guild is the main
    `settings.DISCORD_GUILD_ID`; custom-guild tasks must not corrupt the main
    guild flag.
  - `github_star` calls `GET https://api.github.com/user/starred/{owner}/{repo}`
    inline with the user's token (not via `GitHubOAuthService.check_repo_star`,
    which collapses non-204 statuses and falls back to an unpaginated public
    listing). 204 (starred), 404 (not starred), 401 (-> `token_invalid_relink_required`),
    403 rate-limit / 5xx / transport (-> `verification_unavailable`). Works with the
    portal's empty-scope GitHub tokens because starred repos are public data.
  - `click_through` always succeeds (trust on click; `requires_verification=False`).
- **Views**: `social_tasks/views.py:SocialTaskViewSet`
  - `GET /api/v1/social-tasks/` - List with `?status=active|completed`, `?category=community|builder|validator`.
    The internal `verification_type` slug is NOT exposed; each task instead carries
    two derived flags from the verifier registry: `requires_verification`
    ("open-and-credit" vs "open-then-verify" UX) and `required_connection`
    ('twitter' / 'discord' / 'github' / null — which linked account the card must
    offer inline linking for). The frontend never inspects verifier slugs.
  - `POST /api/v1/social-tasks/{slug}/complete/` - Run verification, award atomically (UserRateThrottle 30/min)
- **URLs**: `social_tasks/urls.py` mounted from `api/urls.py` under `/api/v1/`.
- **Active seeded tasks** (slug): `follow-genlayer-x`, `join-genlayer-discord`.
  Both are in the `community` category and award 500 points
  (migration 0002 bumped the seeds and changed the model default from 10 to
  500; migration 0003 deactivated `check-out-genlayer-on-x`; completions made
  before the bump keep their frozen `points_awarded`). Community task points
  count immediately in the shared effective community total and roll into the
  MEE6 baseline after distribution without double counting; builder / validator
  category tasks feed their stored leaderboards when created.

### Validators
- **Models**: `validators/models.py`
  - ValidatorWallet - Synced validator wallet metadata per network. Now also stores Wall of Shame observability state: `metrics_status`, `logs_status` (both `on` / `shame` / `unknown`), and `last_grafana_check_at`.
  - ValidatorWalletStatusSnapshot - Daily wallet rollup. On-chain `status` (owned by the on-chain sync, for uptime lookback) PLUS the latched observability verdict written by the Grafana sync: `metrics_status` / `logs_status` / `version_status`, `metrics_samples` / `logs_samples` counters, and `node_version`. **Metrics and logs latch pessimistically** (worst-of-day: shame at ANY observation → the day is shame). **Version latches optimistically** (best-of-day: a single up-to-date observation → the day is OK, since once a node upgrades that day an earlier stale reading must not shame it; `on` > `warning` > `shame`). A day is "clean" only if `status=='active'` and both sample counters are ≥1 and neither metrics nor logs is `shame` and version is not `shame`. The two syncs write disjoint columns (bulk_create update_conflicts on `(wallet, date)`), so neither clobbers the other.
  - ValidatorWalletObservation - Append-only raw log; one row per active wallet per Grafana sync run (`observed_at`, `onchain_status`, `metrics_status`, `logs_status`, `version_status`, `node_version`). Source of truth the daily rollup is materialised from and rebuildable via `rebuild_daily_snapshots`.
  - SyncLock - Database-backed sync coordination row with owner token for cross-worker locking
- **Services**: `validators/grafana_service.py`
  - GrafanaValidatorStatusService - Polls Grafana Cloud (`/api/ds/query`) Prometheus + Loki datasources and updates `ValidatorWallet.metrics_status` / `logs_status` for `status='active'` wallets, per network. The Prometheus query also reads the `version` label from `genlayer_node_info` — **normalised at ingest** in `parse_response` ('v' prefix stripped, capped to the 50-char column; when a node briefly reports two version series right after an upgrade, the higher parseable one wins). Each run writes a `ValidatorWalletObservation` and latches today's `ValidatorWalletStatusSnapshot` rollup (`_record_history`, best-effort — never breaks the live status sync). Observations are retained forever by explicit decision — no pruning in points. Used by the Wall of Shame cron.
  - GrafanaValidatorStatusService is also the **source of truth for node versions** (`_sync_node_versions`, best-effort, runs before the active-wallet early return so networks with zero active wallets are still covered): version detection covers **every reporting node on the network regardless of on-chain status** (a quarantined node can still record its upgrade), **except banned wallets**, and only counts versions observed on wallets known to the DB and linked to an operator — the `version` label is self-reported by the node being judged and rewarded, so unknown Prometheus series count for nothing. Only versions that are both semver-valid AND PEP 440-parseable drive comparisons (e.g. `0.6.0-genlayer.1` is excluded — `packaging` can't parse it; in the shame loop an unparseable observed version or an unparseable active target yields `version_status='unknown'`, never a lexicographic fallback verdict). It auto-creates a `TargetNodeVersion` when a STABLE release (bare `x.y.z`, no pre-release/build) higher than the active target is reported by **at least `NODE_VERSION_MIN_OPERATORS_FOR_AUTO_TARGET` (default 1: the first adopter creates the target) distinct operators** (`target_date=now`; an unparseable active target is never blindly superseded; a broadcast notification is emitted via `broadcast_target_node_version`), raises each linked operator's `node_version_<network>` to their highest observed version via a direct `.update()` (**monotonic** — a wallet skipping a scrape cycle can't transiently downgrade the field; genuine downgrades need admin correction), and directly awards an already-approved `node-upgrade` Contribution (`_award_node_upgrade`, early-bonus 4/3/2/1) when a visible operator first reaches the active target. **Removing the node-upgrade multiplier pauses the auto-award** (it is skipped with a warning, not created at 1.0). The per-operator loop is individually fault-isolated — one operator's failure never blocks the rest. Dedup shares the exact `version {v} [{network}]` notes key with the old manual flow so nothing double-awards. A run where a whole datasource comes back empty (no Prometheus series or no Loki counts) still updates live wallet statuses (they self-heal) but **skips the permanent history latch** — a datasource blackout must not shame every validator's recorded day.
- **Commands**: `validators/management/commands/rebuild_daily_snapshots.py` (`--days N`) re-materialises the daily rollup's observability columns from the raw observation log (preserves the on-chain `status`).
- **Views**: `validators/views.py`
  - `/api/v1/validators/` - Validator profile listing/detail for authenticated users; create/update/delete are staff-only (non-staff mutations get 403)
  - `/api/v1/validators/me/` - GET current validator profile (read-only; PATCH removed — node versions are Grafana-sourced, not portal-editable)
  - `/api/v1/validators/wallets/` - Read-only validator wallet listing
  - `/api/v1/validators/wallets/sync/` - POST cron-protected background sync trigger with DB-backed lock (on-chain validator sync)
  - `/api/v1/validators/wallets/sync-grafana/` - POST cron-protected background sync trigger for Grafana observability cross-check (separate SyncLock row `grafana_status_sync` so it can run alongside the on-chain sync)
  - `/api/v1/validators/wallets/wall-of-shame/` - Public read-only endpoint listing active validator wallets with `metrics_status` / `logs_status`. SHAME rows sort first. Cached 60s. Optional `?network=asimov|bradbury` filter. Each wallet also carries `clean_streak_days` + `clean_streak_broken_by` (consecutive not-shamed days for that node, from `validators/streaks.py` over the daily rollup). The grouped `validators` output adds `network_streaks` — per-operator-per-network any-node-clean streaks (a network-day is clean if ≥1 of the operator's nodes was clean) — plus per-node `clean_streak_days` on each `networks` entry. Streaks start accumulating at deploy (history wasn't recorded before). Days with no Grafana data while the node was active (sync outage, pre-history) are SKIPPED — they neither count nor break, so an infra failure on our side never resets streaks; days spent non-active per the on-chain sync break the streak with `broken_by: ['status']`.
  - `/api/v1/validators/wallets/grafana/` - Public minimal roster for the Grafana Infinity datasource (`GrafanaValidatorSerializer`). Flat array, one row per wallet across ALL statuses; fields: `network` (Grafana label value e.g. `asimov-phase5`), `node` (on-chain validator address == Prometheus `genlayer_node_info` `node` label, lowercased), `name`, `status`, `operator`, `account`/`account_name` (only for visible operators), `explorer_url`, plus **raw link/identity facts** (verdicts are computed dashboard-side, NOT here): `linked` (bool — wallet attributed to a portal account; a bare fact, safe for non-visible operators), `moniker` and `logo_uri` (raw synced `getIdentity()` values, empty string = unset), `has_description` (presence bool so the roster doesn't ship long texts). Excludes observability/shame fields by design. Cached 60s. Optional `?network=asimov|bradbury` filter.
    - The roster **also appends one synthetic `status='missing'` row per network** for every graduated portal validator (visible Validator role user) with no wallet linked on that network (`_missing_graduated_rows` in the view) — graduated validators are expected on every testnet, and an absent one otherwise has no row for dashboards to show. On these rows `node` = the account address (unique join key only — matches no metric series), `operator` is null, and the link/identity facts (`linked`/`moniker`/`logo_uri`/`has_description`) are **null** (no wallet to describe — distinct from `false`/empty on a real wallet). A wallet of ANY status (incl. `inactive`) suppresses the missing row; an unlinked wallet (`operator=None`) does not.

### Partners (Ecosystem Partners)
- **Models**: `partners/models.py`
  - Partner - Ecosystem partner directory entry with `name`, `slug`, `description`, `logo_url`, `website_url`, optional `url` (deep link), `display_order`, `is_active`. Ordered by `display_order, name`.
- **Serializers**: `partners/serializers.py`
  - LightPartnerSerializer - Minimal fields (id, name, slug, logo_url, website_url) for list views
  - PartnerSerializer - Full fields for detail
- **Views**: `partners/views.py`
  - `/api/v1/partners/` - Public read-only list of active partners (search + ordering)
  - `/api/v1/partners/{slug}/` - Public read-only detail by slug
- **Migrations**: `partners/migrations/0001_initial.py` creates the model and seeds the 22 founding partners from a `RunPython` step.
- **Admin**: `partners/admin.py` - list_editable on `display_order`, `is_active`; slug prepopulated from name.

### Notifications
- **Models**: `notifications/models.py`
  - `Notification` - Personal (has `recipient`) or broadcast (`recipient=None` + `audience`: all/validators/stewards/builders/community). Audiences resolve via the role OneToOnes (Validator/Steward/Builder/Creator) in `services.audiences_for`. Broadcasts are ONE row regardless of user count; users see broadcasts created after their `date_joined`. Frozen copy (`title`/`body`/`link_url`), `payload` JSON for future channel renderers, `dedupe_key` (re-broadcasting a source object refreshes + resurfaces instead of duplicating).
  - `NotificationReceipt` - Lazy per-user read state for broadcast rows (created on read).
  - `CustomNotification` - Admin-composed campaign: title/markdown body/optional link + targeting (`everyone` | `roles` union of builders/validators/stewards/creators | hand-picked `target_users` M2M | pasted `target_wallets`) + delivery record (`status` draft/sent, `sent_count`, `unmatched_wallets`, `channels` reserved for email/Telegram).
- **Campaigns**: `notifications/campaigns.py`
  - `resolve_recipients(campaign)` - The channel-agnostic enumeration step (always `is_active=True`; banned/invisible users included by design). Future email/Telegram channels reuse this and add their own delivery.
  - `send_campaign(campaign, actor=...)` - Fans out personal `Notification` rows (snapshot semantics, never broadcast rows, so campaigns stay private to recipients). Idempotent via dedupe key `custom.announcement:{pk}`; resend refreshes copy + resurfaces unread, scoped to the currently resolved audience.
  - `recall_campaign(campaign)` - Deletes delivered portal notification rows for that campaign while keeping the campaign record for audit/resend.
  - Compose flow: Django admin > Notifications > Custom notifications. Saving is a silent draft with reach preview; off-by-default "Send now" checkbox or `send_selected`/`resend_selected` actions deliver. "Recall delivered portal notifications" or the `recall_selected` action removes delivered portal rows. The send/recall runs in `save_related` (M2M targeting commits after `save_model`).
- **Registry**: `notifications/registry.py` - Single source of truth for event types (category, priority, default audience, future channels). **Adding a new notification = register an EventType here + emit it from the producer.**
- **Services**: `notifications/services.py`
  - Core: `notify()` (personal), `broadcast()` (audience-wide single row), `recall_broadcast()` (delete a source object's broadcast row), `feed_for(user)`, `mark_notification_read()`, `mark_all_read()`
  - Producers: `notify_submission_review`, `notify_contribution_highlighted` (via post_save receiver), `notify_referral_joined` (ethereum_auth login), `notify_validator_graduated` (users admin action), `notify_email_verification_reminder` (links to `/verify-email`; fanned out by the `send_email_verification_reminders` management command to active users with `is_email_verified=False`, idempotent per-user dedupe key, cleared on verification by `clear_email_verification_reminder` from `ethereum_auth.email_verification.confirm_existing_user`), `broadcast_featured_content/partner/alert/contribution_type/mission/stream/poap/target_node_version`, `broadcast_social_task` (audience derived from the task's category: builder→builders, validator→validators, community→creators)
- **Admin mixin**: `notifications/admin_mixins.py` - `BroadcastNotificationAdminMixin` adds an off-by-default "Broadcast notification now" checkbox + bulk action, plus recall checkbox/action, to any ModelAdmin (`broadcast_event_slug`, `broadcast_service`, `broadcast_eligible` config). Applied to FeaturedContent, Alert, ContributionType, Mission, Partner, Stream, PoapDrop, TargetNodeVersion, SocialTask admins. Saving/activating stays silent unless explicitly checked.
- **Views**: `notifications/views.py`
  - `/api/v1/notifications/` - Auth-required feed (reverse-chronological; `?unread=true`, `?category=` filters)
  - `/api/v1/notifications/unread-count/` - Unread badge count
  - `/api/v1/notifications/{id}/mark-read/` - Personal sets `read_at`; broadcast creates a receipt
  - `/api/v1/notifications/mark-all-read/`
- **Future channels**: email/Telegram slot in via registry `channels` + a delivery outbox and `NotificationPreference` model when the first external channel ships (Telegram link would follow the `social_connections` pattern).

### Gen TV
- **Models**: `gen_tv/models.py`
  - Stream - Livestream entry with `title`, `slug`, `description`, `url`, `image_url`, `starts_at` (required), `ends_at` (required), `category` (`internal` / `community`), `is_active`. `status` is a derived `@property` computed from `starts_at`/`ends_at` (no DB column).
- **Serializers**: `gen_tv/serializers.py`
  - LightStreamSerializer - Minimal fields for list views (status comes through as a read-only string)
  - StreamSerializer - Full fields for detail
- **Views**: `gen_tv/views.py`
  - `/api/v1/gen-tv/streams/` - Public read-only list with `category` filter; pagination disabled (small dataset)
  - `/api/v1/gen-tv/streams/{slug}/` - Public read-only detail by slug
- **Admin**: `gen_tv/admin.py` - status surfaces as a read-only `computed_status` column; date_hierarchy on `starts_at`; slug prepopulated from title.

### POAPs

- **Models**: `poaps/models.py`
  - PoapDrop - POAP campaign/drop with slug, artwork, event window, status, max claims, and legacy import ID.
  - PoapDistribution - Claiming method/window/cap configuration for a drop.
  - PoapClaim - Individual minted or imported claim records.
- **Views**: `poaps/views.py`
  - `/api/v1/poaps/` - Public read-only POAP drop list.
  - `/api/v1/poaps/{slug}/` - Public read-only POAP drop detail.
- **Admin**: `poaps/admin.py` - `PoapDropAdmin` keeps `created_by` as an autocomplete field, includes only `PoapDistributionInline` in `inlines`, and exposes claims through the read-only `claims_link` field instead of rendering `PoapClaim` rows inline. This keeps heavily claimed drops editable without exceeding Django's POST field limit. Ruff RUF012 warnings on the Django admin `inlines = [PoapDistributionInline]` list literal are intentional false positives for this standard admin pattern.

### Earned Discord Roles (social_connections)
- **Logic**: `social_connections/earned_roles.py:assign_earned_community_roles(dry_run=False)` assigns the Synapse (14,000 effective CP + 8 POAPs) and Brain (80,000 effective CP + 16 POAPs + Neurocreative role held) Discord roles to qualifying users. Add-only: never removes roles; each role's threshold is evaluated independently. CP comes from `community_xp.utils.build_effective_community_scores_queryset` (MEE6 baseline + pending contribution and community social-task points), POAPs from `PoapClaim` counts, held roles from `DiscordConnection.current_roles` (the 15-min sync is the reconciler; a successful assignment also updates the local cache). Aborts the run on 429/401/403 (rate limit, missing Manage Roles, hierarchy); other per-user failures log and continue. No-op unless all three `DISCORD_*_ROLE_ID` env vars are set.
- **Audit**: `DiscordEarnedRoleAssignment` stores each successful automatic grant with the Discord member, role, CP/POAP snapshot, and creation time; records are read-only in admin.
- **Service**: `DiscordRoleSyncService.add_member_role(discord_user_id, role_id)` PUTs to Discord; 404 (member left) returns False.
- **Trigger**: `POST /api/v1/users/discord/assign-earned-roles/` (cron-protected, background thread + `DiscordRoleSyncLock` row `discord_earned_role_assign`), called every three hours at `:43` UTC by `.github/workflows/assign-discord-roles.yml` (after the `:37` Discord role sync; the `00:43` run also follows the daily `00:00` MEE6 XP sync). Manual/backfill: `python manage.py assign_earned_discord_roles [--dry-run]`; dry run prints the would-assign list for review. Staff can also run it from the earned-role assignment admin after being granted `social_connections.run_discord_earned_role_assignment` (directly or through a group).
- **Admin**: staff users with `social_connections.run_discord_earned_role_assignment` (granted directly or through a group) can start the same locked background assignment from the `DiscordEarnedRoleAssignment` changelist after confirming the operation; superusers have this permission automatically.
- **Ops**: the bot needs Manage Roles and its role above Synapse/Brain in the guild hierarchy.

### Database & Migrations
- **Migrations**: `{app}/migrations/`
- **Database**: SQLite by default, configured in settings.py
- **Run migrations**: `python manage.py migrate`
- **Create migrations**: `python manage.py makemigrations`

### Database Migration from Production
- **Script**: `backend/scripts/migrate-prod-to-dev.sh`
- **Documentation**: `backend/scripts/README.md`
- **Purpose**: Sync production PostgreSQL database to local/dev environment
- **Prerequisites**:
  - Virtual environment activated
  - AWS CLI configured with Parameter Store access
  - Docker installed (for database operations)

**Usage:**
```bash
# Navigate to scripts directory
cd backend/scripts

# Download production database only (safest option)
./migrate-prod-to-dev.sh --download

# Upload latest dump to dev database
./migrate-prod-to-dev.sh --upload

# Run Django migrations and create admin user only
./migrate-prod-to-dev.sh --setup

# Full migration (download + upload + setup)
./migrate-prod-to-dev.sh
```

**What it does:**
1. Fetches production database credentials from AWS Parameter Store (`/tally/prod/database_url`)
2. Downloads production data to `backend/backups/` using Docker
3. Restores to development database (local PostgreSQL or AWS dev instance)
4. Runs Django migrations
5. Creates/updates admin user (`dev@genlayer.foundation`) with Steward role — password comes from `DEV_ADMIN_PASSWORD` or is randomly generated and printed by the script

**Notes:**
- Uses Docker to avoid PostgreSQL version mismatch issues
- Modular operation allows partial runs (download, upload, setup separately)
- Creates timestamped backups in `backend/backups/`
- See `backend/scripts/README.md` for detailed setup and troubleshooting

### RDS to SQLite Migration
- **Script**: `backend/scripts/migrate_rds_to_sqlite.py`
- **Purpose**: Convert production PostgreSQL to local SQLite for development
- **Usage**: `python scripts/migrate_rds_to_sqlite.py` (from backend directory)
- **Notes**: Resets all passwords to 'pass', excludes leaderboard entries, backs up existing db.sqlite3

## API Endpoints Summary

### Base URL
- Development: `http://localhost:8000`
- API Root: `/api/v1/`
- Auth endpoints: `/api/auth/` (not v1)

### Main Endpoints
```
# Authentication
GET    /api/auth/nonce/
POST   /api/auth/login/
GET    /api/auth/verify/
POST   /api/auth/logout/

# Users
GET    /api/v1/users/           (requires auth)
GET    /api/v1/users/me/           (requires auth)
PATCH  /api/v1/users/me/           (requires auth; name/description/website/socials — node_version NOT editable, Grafana-sourced)
GET    /api/v1/users/{address}/    (requires auth)
GET    /api/v1/users/by-address/{address}/ (requires auth)
GET    /api/v1/users/validators/   (requires auth)
POST   /api/v1/users/link_x_account/       (requires auth, awards configured points for linking X)
POST   /api/v1/users/link_discord_account/  (requires auth, awards configured points for linking Discord)
POST   /api/v1/users/link_github_account/   (requires auth, awards community-link-github points; auto-fired by SocialLink.svelte on GitHub link)
POST   /api/v1/users/start_builder_journey/    (requires auth, no-op: no longer awards points)
POST   /api/v1/users/complete_builder_journey/ (requires auth, grants Builder role point-free; gated on the star-boilerplate social task)
POST   /api/v1/users/discord/assign-earned-roles/ (cron-protected, X-Cron-Token, background; assigns earned Synapse/Brain Discord roles)

# Social Tasks
GET    /api/v1/social-tasks/                     (?status=active|completed&category=community|builder|validator)
POST   /api/v1/social-tasks/{slug}/complete/     (requires auth; throttled 30/min/user)

# Contributions
GET    /api/v1/contributions/      (requires auth)
POST   /api/v1/contributions/      (requires auth)
GET    /api/v1/contributions/{id}/ (requires auth)
PATCH  /api/v1/contributions/{id}/ (requires auth)
DELETE /api/v1/contributions/{id}/ (requires auth)

# Submissions (submitter-side)
GET    /api/v1/submissions/my/                  (requires auth, paginated user submissions)
GET    /api/v1/submissions/accepted-projects/   (requires auth, the user's highlighted Projects contributions milestones can link to; optional ?submission=UUID includes that pending milestone's grandfathered current link; includes next_milestone_version and github_url)
POST   /api/v1/submissions/{id}/appeal/         (requires auth, owner-only, one per submission)
POST   /api/v1/submissions/{id}/add-evidence/   (requires auth, owner-only)

# Contribution Types
GET    /api/v1/contribution-types/            (requires auth)
GET    /api/v1/contribution-types/{id}/       (requires auth)
GET    /api/v1/contribution-types/statistics/ (requires auth)

# Leaderboard
GET    /api/v1/leaderboard/                             (requires auth)
GET    /api/v1/leaderboard/monthly/                     (requires auth, ?type=builder|community|validator, ?limit=10, optional ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD)
GET    /api/v1/leaderboard/community-podium/            (public, top 3 Community users by accepted-submission points only)
GET    /api/v1/leaderboard/stats/                       (requires auth)
GET    /api/v1/leaderboard/user_stats/by-address/{address}/ (requires auth)

# Multipliers
GET    /api/v1/multipliers/        (requires auth)
GET    /api/v1/multiplier-periods/

# Validators - Wall of Shame
POST   /api/v1/validators/wallets/sync-grafana/    (cron-protected, X-Cron-Token, background)
GET    /api/v1/validators/wallets/wall-of-shame/   (public, cached 60s, ?network= filter)
GET    /api/v1/validators/wallets/grafana/         (public, cached 60s, ?network= filter; minimal Infinity roster)

# Steward Submissions
GET    /api/v1/steward-submissions/stats/           (requires steward)
GET    /api/v1/steward-submissions/daily-metrics/   (requires steward)
GET    /api/v1/steward-submissions/{id}/ai-feedback/  (requires steward + type permission)
POST   /api/v1/steward-submissions/{id}/ai-feedback/  (create or versioned-revise current non-author reviewer's proposal-bound feedback)

# AI Review Agent (service account bearer token; ai_review:read / ai_review:propose scopes)
GET    /api/v1/ai-review/
GET    /api/v1/ai-review/{id}/
POST   /api/v1/ai-review/{id}/propose/     (create new proposal; requires ai_review:propose)
PUT    /api/v1/ai-review/{id}/propose/     (update existing proposal; requires ai_review:propose)
GET    /api/v1/ai-review/proposed/     (pending active proposals awaiting steward review; add proposed_by=ai for AI-only)
GET    /api/v1/ai-review/reviewed/
GET    /api/v1/ai-review/feedback/     (paginated benchmark feedback; inclusive ?updated_after= overlap; ?submission=; requires ai_review:read)
GET    /api/v1/ai-review/templates/

# Partners (Ecosystem Partners)
GET    /api/v1/partners/                   (public, list active partners)
GET    /api/v1/partners/{slug}/            (public, partner detail)

# Projects
GET    /api/v1/projects/                   (public, active project profiles)
GET    /api/v1/projects/{slug}/            (public, project detail with metrics and related contributions)

# Gen TV
GET    /api/v1/gen-tv/streams/             (public, supports ?category= filter)
GET    /api/v1/gen-tv/streams/{slug}/      (public, stream detail)

# Notifications
GET    /api/v1/notifications/              (requires auth, ?unread=true ?category= filters)
GET    /api/v1/notifications/unread-count/ (requires auth)
POST   /api/v1/notifications/{id}/mark-read/   (requires auth)
POST   /api/v1/notifications/mark-all-read/    (requires auth)
```

### Leaderboard monthly date ranges

`GET /api/v1/leaderboard/monthly/` returns ranked users by contribution totals for `type` (for example `community` or `builder`) and optional `limit`. Without `start_date`, it defaults to the current calendar month beginning on day 1; with `start_date` and/or `end_date`, it filters contributions by `contribution_date` date in the provided inclusive range. Dates must be `YYYY-MM-DD`, and `start_date` must be before or equal to `end_date`; invalid dates return `400`.

Example:

`GET /api/v1/leaderboard/monthly/?type=community&limit=5&start_date=2026-05-07&end_date=2026-06-05`

Example response:

```json
[
  {
    "id": "monthly-community-123",
    "user": 123,
    "user_details": { "address": "0x...", "name": "Contributor" },
    "type": "community",
    "total_points": 40,
    "rank": 1
  }
]
```

## Environment Variables
Located in `.env` file:
- `VALIDATOR_RPC_URL` - Blockchain RPC endpoint
- `WEB3_RPC_TIMEOUT_SECONDS` - Optional timeout in seconds for validator Web3 HTTP requests (default `10`)
- `WEB3_RPC_MAX_RETRIES` - Optional number of retries after the initial validator Web3 HTTP request (default `1`)
- `VALIDATOR_CONTRACT_ADDRESS` - Smart contract address
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode flag
- `ALLOWED_HOSTS` - Allowed host headers
- `RECAPTCHA_PUBLIC_KEY` - Google reCAPTCHA site key (required - use test key from .env.example for development)
- `RECAPTCHA_PRIVATE_KEY` - Google reCAPTCHA secret key (required - use test key from .env.example for development)
- `RECAPTCHA_ALLOW_TEST_KEYS` - Optional opt-in flag for non-production deployments that intentionally use Google's reCAPTCHA test keys with `DEBUG=False`. Set to `true` to silence `django_recaptcha.recaptcha_test_key_error`; production must not set this flag. The logic lives in `tally/settings.py` near `_RECAPTCHA_TEST_PUBLIC_KEY` and `SILENCED_SYSTEM_CHECKS`.
- `CRON_SYNC_TOKEN` - Cron-protected endpoint auth (used by `sync` and `sync-grafana`)
- `DISCORD_SYNAPSE_ROLE_ID` / `DISCORD_BRAIN_ROLE_ID` / `DISCORD_NEUROCREATIVE_ROLE_ID` - Discord role IDs for the earned community role automation (Synapse/Brain assignment). All three must be set or the assignment job is a no-op.
- `GRAFANA_BASE_URL` - Grafana Cloud base URL (default `https://genlayerfoundation.grafana.net`)
- `GRAFANA_API_TOKEN` - Grafana service-account bearer token (required for Wall of Shame). Store in AWS SSM (`/tally/{env}/grafana_api_token`) for production.
- `GRAFANA_PROM_DS_UID` - Prometheus datasource UID (default `grafanacloud-prom`)
- `GRAFANA_LOKI_DS_UID` - Loki datasource UID (default `grafanacloud-logs`)
- `GRAFANA_ASIMOV_LABEL` / `GRAFANA_BRADBURY_LABEL` - Override the `network` label values Grafana queries use per testnet (defaults: `asimov-phase5`, `bradbury-phase1`)
- `NODE_VERSION_SHAME_GRACE_DAYS` - Grace period (days) after a target's `target_date` before a node still behind it is version-shamed, applied globally (default `3`)
- `NODE_VERSION_MIN_OPERATORS_FOR_AUTO_TARGET` - Minimum distinct operators that must be observed running a new stable node version before the Grafana sync auto-creates it as the fleet-wide upgrade target (default `1`: the first adopter creates the target; raise it to require corroboration if version spoofing ever becomes a concern)
- `SORSA_API_BASE_URL` - Sorsa API base URL (default `https://api.sorsa.io/v3`); used for Twitter follow verification in social_tasks and X follower counts in overview metrics.
- `SORSA_API_KEY` - Sorsa API key sent in the `ApiKey` header (secret, required). Store in AWS SSM (`/tally/{env}/sorsa_api_key`) for production.
- Note: the Sorsa request timeout and follow endpoint path are intentionally code constants in `social_tasks/sorsa_client.py`, not env vars. Changing the endpoint requires a code deploy anyway because the response parser lives in the same file.

### Investor overview metrics (`api/overview_metrics.py` + `api/metrics_views.py`)
The cron `POST /api/v1/metrics/overview/refresh/` (GitHub Action `sync-overview-metrics.yml`, every 15 min) runs `refresh_overview_metrics()`, which snapshots the source metrics below and then stores final composite payloads in `MetricSnapshot`: `overview_payload` for `GET /api/v1/metrics/overview/` and `network_activity` for `GET /api/v1/metrics/overview/network-activity/`. Public overview reads return the last stored aggregate from the DB and do not live-fetch Studio, explorers, Discord, Telegram, X, or GitHub. A network-activity refresh is only marked `ok` when Studio, Asimov, and Bradbury are all present. Partial fetches are stored as `error` snapshots with the attempted payload plus `expected_sources`, `resolved_sources`, and `missing_sources` dimensions for diagnosis; reads skip incomplete historical `ok` rows and serve the newest complete snapshot.
- `STUDIO_METRICS_URL` - GenLayer Studio executive-metrics dashboard for the decisions/chain-tx series (default `https://studio-metrics-dashboard.vercel.app/api/metrics/executive`).
- `OVERVIEW_TOP_VALIDATORS` - optional JSON array of curated validators; superseded by the per-wallet `ValidatorWallet.show_in_overview` + `assets_under_management_usd` admin fields when any are set.
- `DEFILLAMA_FEES_RANK` / `DEFILLAMA_FEES_RANK_URL` - the DeFiLlama fees-rank value/source shown on the overview.
- `DISCORD_BOT_TOKEN` + `DISCORD_GUILD_ID` (Discord members), `SORSA_API_KEY` + `X_METRICS_USERNAME` (X followers), `GITHUB_METRICS_REPO` + `GITHUB_METRICS_TOKEN` (boilerplate stars).
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` for the live Telegram member count, else `TELEGRAM_MEMBERS` or the built-in `13300` curated fallback.

**AWS Deployment:** For production deployments on AWS App Runner, all environment variables must be stored in AWS Systems Manager (SSM) Parameter Store. See `aws-deployment-guide.md` for setup instructions.

## Common Commands
```bash
# Activate environment
source env/bin/activate

# Run development server
python manage.py runserver

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell

# Run tests
python manage.py test

# Collect static files
python manage.py collectstatic
```

## Authentication Flow
1. Frontend requests nonce from `/api/auth/nonce/`
2. User signs message with MetaMask
3. Frontend sends signed message to `/api/auth/login/`
4. Backend verifies signature and creates session
5. Session cookie is set for subsequent requests
6. All authenticated endpoints require session cookie

Server-to-server callers (currently only the AI review agent) do not use
sessions: they authenticate per request with a service account bearer token
(`Authorization: Bearer sa_<id>_<secret>`), verified by
`service_accounts.authentication.ServiceAccountAuthentication` and scoped by
`HasServiceAccountScope`. See the "Service Accounts" section above.

## Key Patterns
- **Wallet address privacy** (`users/utils.py`): public API surfaces NEVER return a user's
  full account address — serializers emit the truncated form via `truncate_address()`
  (`0x1234...abcd`; full only for the owner via `/users/me/`+auth endpoints, staff, and
  steward/admin serializers). Validator node wallet addresses and on-chain
  `operator_address` are exempt (public chain data used by Grafana joins and explorer
  links). Address SEARCH is exact-full-address only (`is_full_address()` gate) — never
  `icontains`, which would be a char-by-char oracle against truncated payloads. User
  lookups are dual-key via `user_lookup_kwargs()`: `/users/by-address/{key}/`,
  `/users/{key}/`, poaps/leaderboard by-address endpoints, and `?user_address=` params
  all accept a numeric user id OR a full address. Public leaderboard reads have an
  anonymous-only `public_leaderboard` throttle scope. Tests:
  `users/tests/test_address_privacy.py`.
- All models inherit from `utils.models.BaseModel` (adds created_at, updated_at)
- ViewSets use DRF's ModelViewSet for standard CRUD
- Authentication uses Sign-In With Ethereum (SIWE)
- Points calculation: base_points × multipliers = total_points
- Addresses are stored lowercase but compared case-insensitively
- **Evidence Submission**: File uploads are disabled (issue #212). Evidence must be submitted as text descriptions or URLs only.
- **reCAPTCHA Protection**: New contribution submissions require Google reCAPTCHA v2 verification to prevent spam. Editing existing submissions does not require reCAPTCHA. Local development silences Google's test-key system check automatically when `DEBUG=True`; dev deployments that run with `DEBUG=False` can explicitly set `RECAPTCHA_ALLOW_TEST_KEYS=true`. Never enable that flag in production.

## Serialization Patterns & Performance Optimization

The project uses **context-aware serialization** to optimize API performance:
- **Light serializers** (`Light*Serializer`) for list views - minimal fields, no nested queries
- **Full serializers** for detail views - complete data with relationships
- ViewSets set `context['use_light_serializers'] = self.action == 'list'`
- Serializers check context flag to choose which nested serializer to use
- Always use `select_related()` for ForeignKey/OneToOne and `prefetch_related()` for reverse/M2M
- Light serializers defined at top of each app's `serializers.py` with `Light` prefix
- Performance impact: 99%+ query reduction (30s+ → <1s for list views)

**Examples**: See `users/serializers.py` for `LightUserSerializer` and `contributions/serializers.py` for `LightContributionSerializer`

**Evidence URL Type Serializers** (`contributions/serializers.py`):
- `LightEvidenceURLTypeSerializer` - Minimal (id, name, slug, is_generic) for nested use in Evidence responses
- `EvidenceURLTypeSerializer` - Full serializer with url_patterns for client-side detection, used in ContributionType responses

## Testing
- **Test Organization Best Practice**: Use `{app}/tests/` folder structure for better organization
  - Create `{app}/tests/__init__.py` to make it a Python package
  - Separate test files by functionality: `test_models.py`, `test_views.py`, `test_forms.py`, etc.
  - Example: `contributions/tests/test_validator_creation.py`
- Run specific app tests: `python manage.py test {app}`
- Run specific test file: `python manage.py test {app}.tests.test_filename`
- Run specific test class: `python manage.py test {app}.tests.test_filename.TestClassName`
- Test database is created/destroyed automatically
- **Important**: Add 'testserver' to ALLOWED_HOSTS in .env for tests to work properly

## Admin Panel
- URL: `/admin/`
- Requires superuser account
- Models registered in `{app}/admin.py`
- User records include a `can_view_role_sections` checkbox for read-only access to gated Builder, Validator, and Community portal views. It does not create role profiles, enable role actions, affect role metrics, or grant Steward access.
