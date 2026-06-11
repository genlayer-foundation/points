# Changelog

All notable user-facing changes to this project will be documented in this file.

## Unreleased

- Searching the Community leaderboard now shows each participant's real rank instead of restarting the numbering at 1 for the search results (d26509e0)
- Browser back navigation now works everywhere in the portal: links to portal pages from GenNews announcements, hero banners, featured builds, ecosystem project cards, and admin-authored alerts navigate in-app instead of opening a new tab, and pages that redirect away (login-required and steward-only views) no longer trap the back button. GenNews also gets its own entry in the sidebar's Discover section (c81eb99c)
- Projects and Milestones are now separate contribution types. Projects submissions require the project's GitHub repository as evidence. Builders with an accepted Projects contribution can submit Milestones: auto-versioned progress updates (v1, v2, ...) linked to that contribution, where the written explanation of changes is required, extra evidence is optional, and stewards review the changes against the project's repository (3e7f4d8)
- Security hardening across the portal: steward review endpoints only accept the audited review actions, ban appeals are handled by staff, evidence on pending or rejected submissions is visible only to its owner and stewards, all markdown rendered from the API is sanitized, evidence links only open real web URLs, sign-in is rate limited, and contribution dates can no longer be set in the future (8e335b9)
- The public Wall of Shame and validator wallet endpoints no longer reveal the profile identity (name, avatar, profile link) of operators who set their account to non-visible; the validator still appears, identified only by its on-chain operator address (dedbeae)
- New Wall of Shame page under Validators publicly flags every active validator that isn't reporting metrics or logs in the last five minutes. The page lists all active validators (SHAME rows first) with their moniker, addresses, operator profile link, network badge, and binary ON/SHAME badges for both metrics and logs. Backed by a five-minute cron that cross-references on-chain active validators against our observability stack (98d083e)
- Stewards reviewing submissions can now copy a compact AI-ready bundle (user, contribution, mission, state, submitter notes, evidence URLs, staff reply, proposal, and internal CRM notes) from a copy icon next to each submission's title; the copy aborts with a warning if internal notes can't be loaded so the clipboard payload is never silently incomplete. Evidence URL types gain an admin-editable "Allow duplicate" flag that exempts URLs of that type (for example shared GitHub repositories) from duplicate detection across both manual and automated review (ac68ec7)
- Contributions explorer now shows highlighted contributions again, the page footer is flush to the bottom and CTAs users to submit a contribution, and the highlights section collapses to a single compact line when empty so contributions get more room. The Submit Contribution form no longer shows misleading "Please add a description" errors for evidence URLs, detects URL types correctly when users omit `https://`, and disables the submit button when a required GitHub or X URL has no linked social account (b249787)
- Highlights and All Contributions are now a single filterable Contributions explorer at `/all-contributions` with a category pill toggle, type and mission dropdowns, a debounced search bar that supports `sort:` syntax, a Both / Highlights only / Contributions only view switch, and shareable URL state. Highlights show as a horizontal slider with arrows in the default Both view; non-submittable contribution types (badges, journey rewards) are hidden from the public list, consecutive contributions of the same type are no longer stacked, and the Dashboard highlights strip now shows the latest 10 sorted by date (c9f7b88)
- Metrics dashboard Pending review tile no longer collapses to zero when filters are applied; it now shows submissions created in the selected range that are still awaiting a decision (97dc404)
- Stewards can now mark submissions as internally interesting from a header checkbox on the submission card and filter the steward queue by that flag with `is:interesting` / `not:interesting` in the search bar; the flag is never exposed to submitters. Requesting more information on a submission also records the staff reply as a quoted block in the submission's internal CRM note next to the action summary (6dfeb10)
- Metrics dashboard now reports the same Builder and Validator counts as the role dashboards (visible users with a category-matched contribution) and drops the "Unique participants" tile from the Portal Participation strip (b46195c)
- Profile Ranking widget hides the Community tab and shows community points that match the Community section, the bottom CTA banner skips users tied with the viewer when computing the next rank and greets rank-1 users with a category-aware message, and the Profile Edit banner drops the purple gradient overlay once a banner image is uploaded (d74f7fd)
- Overview hero banner card now clamps the project title to one line and the description to two lines, with ellipsis on overflow (4368281)
- Overview hero banner is more compact on desktop and no longer leaves a large empty gap inside the text card when the description is short or the View Project button is missing; titles and descriptions now ellipsize cleanly when they overflow (2e75620)
- Overview hero banner now keeps a fixed-height text card and a steadier image ratio across descriptions and the optional View Project button; profile X and GitHub pills link out to those platforms, the banner gradient only renders when no banner image is uploaded, and Community XP is renamed to Community Points. Referral points no longer count Builder, Builder Welcome, or Validator Waitlist contributions from referred users (a04d4a5)
- Mission-host contribution types: admins can mark a non-submittable type as visible in the public Contributions list so it appears alongside submittable types; direct submissions to non-submittable types are blocked server-side and users are routed through an active mission. Contribution cards and profile history now show the mission name with the parent type as a subtitle, so past submissions keep their mission identity after a mission ends. The portal submit form shows inline per-slot URL errors and rejects pasted non-URL content (a5b7d7f)
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
