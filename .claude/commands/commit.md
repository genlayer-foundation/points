# /commit — Create a 3-Layer Commit

You are creating a git commit with a structured 3-layer message. Follow this workflow exactly.

---

## Step 1: Analyze Changes

1. Run `git status` (never use `-uall`) to see all changed files
2. Run `git diff` and `git diff --cached` to see actual changes
3. Run `git log --oneline -10` to see recent commit style
4. Understand what changed at the product, architecture, and implementation levels

---

## Step 2: Compose the 3-Layer Commit Message

### Layer 1: Subject Line (product/story level)
- One line, imperative mood, under 72 characters
- What happened from a **product perspective** — no code, no files, no components
- Examples: "Improve hero banner responsiveness on tablet and mobile", "Add referral program landing page"

### Layer 2: Body (architecture/component level)
- Blank line after subject, then a paragraph or short bullets
- Names components and structural decisions, explains what was merged/split/refactored and why
- **No file paths, no line numbers** — this is for developers scanning the log
- Written in present tense: "The hero banner now supports..."

### Layer 3: Claude Implementation Notes
- After another blank line, starts with `## Claude Implementation Notes`
- File-level details: what changed where and why
- Format: `- path/to/file.ext: Description of changes`
- This section is the technical reference for Claude in future sessions

### Template:
```
<subject line — product level, imperative, <72 chars>

<body — architecture/component level, what and why, no file paths>

## Claude Implementation Notes
- path/to/file: What changed and why
- path/to/other-file: What changed and why
```

---

## Step 3: Present for Review

Show the complete commit message to the user in a clear code block. Ask if they want to modify anything. Do NOT proceed until the user approves.

Use AskUserQuestion with options like:
- "Commit as-is"
- "Edit message" (then ask what to change)
- "Abort"

---

## Step 4: Stage and Commit

1. Stage files explicitly by name — **never use `git add -A` or `git add .`**
2. Do not stage files that contain secrets (.env, credentials, etc.)
3. Create the commit using a HEREDOC for proper formatting:
```bash
git commit -m "$(cat <<'EOF'
<the approved message>
EOF
)"
```
4. **No attribution lines** — no Co-Authored-By, no "Generated with Claude Code"

---

## Step 5: Update CHANGELOG.md

1. Read the current CHANGELOG.md
2. Get the commit hash with `git rev-parse --short HEAD`
3. Add a one-line entry under `## Unreleased` in plain language (product level only)
4. Format: `- <what changed for users> (<short hash>)`
5. Only add entries for user-facing changes — skip internal refactors, test-only changes, etc.
6. Stage and commit the changelog update:
```bash
git add CHANGELOG.md
git commit -m "Update changelog"
```

---

## Step 6: Verify

Run `git log --oneline -3` to confirm the commits look clean.

---

## Git History Management (Before Pushing)

When the user is ready to push or create a PR, help them clean the history:

1. **Review**: `git log --oneline dev..HEAD` to see all commits on the branch
2. **Squash if needed**: If there are WIP or fixup commits, use `git rebase -i` to combine them into clean logical units (never use `-i` flag directly — present the rebase plan to the user and use `GIT_SEQUENCE_EDITOR` to automate)
3. **Rebase onto target**: `git rebase dev` for linear history (no merge commits)
4. **Verify**: `git log --oneline dev..HEAD` to confirm clean history

---

## Rules

- **Never blind-stage**: Always review what you're staging
- **No secrets**: Never commit .env, credentials, API keys
- **No attribution**: No Co-Authored-By or Generated-with lines
- **Always present for review**: The user must approve before committing
- **Imperative mood**: "Add feature" not "Added feature" or "Adds feature"
- **No merge commits**: Always rebase, never merge

---

## Learned Preferences

<!-- Claude updates this section when the user gives feedback about commit style -->
<!-- Examples: "don't mention migration files", "always group frontend/backend" -->

(none yet)
