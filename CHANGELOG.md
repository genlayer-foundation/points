# Changelog

All notable user-facing changes to this project will be documented in this file.

## Unreleased

- Fix admin 500 when opening a contribution type: the `required_evidence_url_types` M2M was folded into an already-applied migration, so environments on the previous 0050 never got the table. Split it into its own migration so it actually runs (1bc0024)
- Validator Waitlist no longer awards 20 points; historical waitlist contributions are zeroed out and leaderboards rebuilt. Only selected validators (and builders, for builder contributions) can submit to those categories; ineligible users now see a category-themed explainer linking to their profile Journeys section (77a3dec)
- Required evidence URL types per contribution type: admins can now declare one or more required URL types on a contribution type, and submissions must include at least one URL whose detected type matches; the submit form shows a dedicated required-evidence field and the edit form surfaces a live-status banner (d9c3a1c)
- Evidence URL type detection and validation for contribution submissions with duplicate checking and handle ownership verification (3a20426)
- Direct Cloudinary image upload from Django admin for featured content (ce4c157)
- Responsive hero banner images for tablet and mobile (e5c01b5)

## 2026-04-01 — Fix Overview Leaderboards

### Fixed
- Per-network leaderboards on testnets overview page now show sequential ranks (1, 2, 3) instead of gapped global ranks
- Asimov network filter no longer includes validators with no synced wallets

### Changed
- Testnets overview shows validator count from leaderboard entries instead of separate wallet stats endpoint
- Simplified network stat display to single "Active Validators" metric per network

### Removed
- Wallet stats endpoint (`/api/v1/validators/wallets/stats/`) — data now derived from leaderboard entries

## 2026-03-30 — Fix Testnet Metrics

### Fixed
- Testnet validator counts now show only truly active validators instead of including quarantined/banned ones
- Bradbury testnet metrics now functional with correct contract addresses
- All contract addresses, RPC URLs, and explorer URLs updated to new unified testnet chain

### Added
- Quarantined validator sync via `getAllQuarantinedValidators()` contract call
- Per-network RPC URL support in backend settings
- Proper status classification: active, quarantined (temporary ban), banned (permanent), inactive
