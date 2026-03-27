# Changelog

All notable user-facing changes to this project will be documented in this file.

## Unreleased

### Added
- Daily uptime points system: automated management command and cron endpoint for granting daily validator uptime contributions
- Multi-network support (asimov + bradbury) with per-network duplicate detection
- Date range backfill support via `--start-date`/`--end-date` with 366-day cap
- Snapshot-based activity verification with fallback to current wallet status for recent dates
- GitHub Actions workflow for daily uptime cron job (00:30 UTC)
- Comprehensive test suite (16 tests) covering all command paths

### Changed
- Refactored `add_daily_uptime` command from per-user saves to bulk_create with batch processing
- Leaderboard updates now use shared `update_user_leaderboard_entries` and `update_referrer_points` helpers
- All contribution creation + leaderboard updates wrapped in atomic transaction

### Fixed
- Migration 0037 no longer crashes in test environments when seed users don't exist

- Direct Cloudinary image upload from Django admin for featured content (ce4c157)
- Responsive hero banner images for tablet and mobile (e5c01b5)
