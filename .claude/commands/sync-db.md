---
description: Sync production database to local development
---

Put a copy of the production database in local `db.sqlite3`:

```bash
cd backend
source env/bin/activate
python scripts/sync_prod_to_sqlite.py
```

Roughly 30 minutes. Requires Docker running and AWS credentials for Parameter
Store. Every user password becomes `pass`. The existing `db.sqlite3` is renamed
to `db.sqlite3.backup_<timestamp>` first — those are ~1.6GB each, so prune them.

Flags for resuming after a failure:

- `--reuse-dump` — skip the pg_dump, use the newest `backups/*.sql`
- `--reuse-postgres` — the `tally-local-pg` container already holds the data
- `--keep-container` — leave Postgres up (`docker start tally-local-pg` to reuse)
- `--keep-json` — keep the intermediate `prod_snapshot.json`
- `--no-leaderboard` — skip the leaderboard rebuild

Verified end to end on 2026-08-01: 16 minutes with the dump already local,
0 dangling foreign keys, 56,304 users, 106,937 contributions.

## Do not use the other two scripts

`scripts/migrate_rds_to_sqlite.py` runs `dumpdata` straight against production
RDS. Django emits a query per row for many-to-many fields, so over a remote link
it manages about 90 user rows per minute — a 3.5 hour run did not finish the
users table, and production has ~56k users.

`scripts/migrate-prod-to-dev.sh` targets a **PostgreSQL** database (the shared
AWS dev instance), not local SQLite. Local Django uses SQLite unless
`DATABASE_URL` is set, so it is not the local-development path. Its upload step
is untested here.

## Why the working script is shaped the way it is

Each stage is scar tissue from a real failure; do not "simplify" them away:

1. **pg_dump, not dumpdata, against production** — one streamed dump takes
   minutes instead of never finishing.
2. **Explicit Docker `--platform`** — a cached amd64 `postgres:17` on Apple
   Silicon fails with `exec format error`.
3. **Migrate the local Postgres copy before exporting** — production's schema
   lags the code, so `dumpdata` otherwise fails on columns that exist only in
   the models (it died on `ethereum_auth_pendingwalletsignup.acquisition_campaign_link_id`).
4. **Do not exclude contenttypes/auth.permission from the export** — the m2m
   rows reference production's permission ids; a freshly migrated database
   generates different ones, and `loaddata` then fails its foreign-key check at
   commit, rolling back the entire load.
5. **Clear every table except `django_migrations` before loading** — data
   migrations seed rows that collide with the snapshot on natural keys such as
   `projects.Project.slug`.
6. **Suppress model signals during the load** — see the known bug below.
7. **Rebuild the leaderboard afterwards** — leaderboard entries are excluded
   from the export, so it is empty until `manage.py update_leaderboard` runs.

## Known bug this works around

`contributions/models.py` `sync_contribution_discord_xp_state` and
`sync_social_task_completion_discord_xp_state` do not check
`kwargs.get('raw')`, so a fixture load recreates every
`ContributionDiscordXPState` and collides on `contribution_id` at the first row.
`users/signals.py` `create_referral_code` and `poaps/signals.py`
`attach_legacy_poap_claims` have the same gap on User.

Neighbouring receivers guard correctly — `ensure_validator_profile_for_graduation_contribution`
in the same file, and `update_leaderboard_on_contribution` in
`leaderboard/models.py`, whose comment reads "Skip during fixture loading
(loaddata) to avoid ordering issues". The real fix is a one-line
`if kwargs.get('raw', False): return` in each of the four. Until that lands, the
sync script suppresses signals for the duration of the load.
