# Changelog

All notable user-facing changes to this project will be documented in this file.

## Unreleased

- Direct Cloudinary image upload from Django admin for featured content (ce4c157)
- Responsive hero banner images for tablet and mobile (e5c01b5)

## 2026-04-01 — Per-Network Validator Leaderboards

### Added
- Network tabs (Asimov | Bradbury) on `/validators/leaderboard` page with lazy-loading per tab
- Deep-links from testnets overview cards to the matching leaderboard tab
- Validator status breakdown on testnets page: active, quarantined, banned, inactive counts per network
- URL query param support (`?network=asimov`) for direct-linking to a network tab

### Changed
- Testnets overview now shows total validator count from wallet API `network_stats` instead of leaderboard entry count
- Leaderboard API calls on testnets overview limited to top 5 (was fetching all entries)

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
