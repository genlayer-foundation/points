# Development Sessions with Orca

## Overview

This project uses [orca](https://github.com/rasca/orca) for Docker-isolated development sessions. Each session gets its own git worktree, Docker container, tmux session, and PostgreSQL database.

## Prerequisites

- **orca** installed: `curl -fsSL https://raw.githubusercontent.com/rasca/orca/main/install.sh | bash`
- **Docker Desktop** running
- **orca base image** built: `orca build`

## Quick Start

```bash
# Start the shared PostgreSQL container (one-time)
cd backend && docker compose up -d db && cd ..

# Create a new session
orca add feature-auth

# Attach to the tmux session
orca attach feature-auth

# List all sessions
orca list

# Stop a session (preserves worktree + volumes)
orca stop feature-auth

# Resume after restart
orca resume feature-auth

# Remove everything
orca remove feature-auth
```

## Session Structure

Each session consists of:
- **Git Worktree**: `~/Dev/tally-<name>/`
- **Git Branch**: Named after the session
- **Docker Container**: `orca-tally-<name>`
- **Tmux Session**: `tally-<name>` with windows:
  - `backend:<port>` — Django server
  - `frontend:<port>` — Svelte dev server
  - `django-shell` — Django interactive shell
  - `claude` — Claude Code session
  - `shell` — Interactive shell
  - `cli` — For one-off commands

## Configuration

All session configuration lives in `orchestrator.yml` at the project root. Key settings:
- **Ports**: Backend starts at 8000, frontend at 5000 (auto-incremented per session)
- **Database**: Each session gets `DATABASE_URL` set to `tally_<session-name>` database
- **Setup files**: `.env` files are copied and updated per-session automatically

## Database Management

### Architecture

A single shared PostgreSQL container serves all sessions:

```
Docker: tally-postgres (port 5432, postgres:17)
  ├── tally_main        ← main worktree
  ├── tally_template    ← production snapshot
  ├── tally_feature_x   ← orca session
  └── tally_pr_123      ← PR session
```

### Start PostgreSQL

```bash
cd backend && docker compose up -d db
```

### Sync Production Data

```bash
cd backend/scripts
./migrate-prod-to-dev.sh --download   # Download from RDS
./migrate-prod-to-dev.sh --upload     # Restore to tally_template
./migrate-prod-to-dev.sh --setup      # Run migrations + create admin
```

### Create Session Database from Template

After syncing prod data, create instant clones for new sessions:

```bash
docker compose -f backend/docker-compose.yml exec db \
  psql -U tally_user -c 'CREATE DATABASE "tally-feature-x" TEMPLATE tally_template'
```

### Database Status

```bash
docker compose -f backend/docker-compose.yml exec db \
  psql -U tally_user -c "\l" | grep tally
```

## PR Reviews

```bash
orca pr 42              # Create session from PR #42
orca attach pr-42       # Attach to it
orca update-pr 42       # Pull latest changes
orca remove pr-42       # Clean up
```

## Port Allocation

Ports are auto-allocated globally across all orca sessions:
- Backend: 8000, 8001, 8002, ...
- Frontend: 5000, 5001, 5002, ...

Port assignments are visible via `orca list` and in tmux window names.

## Troubleshooting

### Django Can't Connect to Database
1. Ensure `tally-postgres` container is running: `docker ps | grep tally-postgres`
2. Check the database exists: `docker compose -f backend/docker-compose.yml exec db psql -U tally_user -l`
3. From inside orca container, host is `host.docker.internal`, not `localhost`

### Port Already in Use
Check active sessions with `orca list`. Ports are tracked in `~/.orca/sessions.json`.

### Container Won't Start
```bash
orca stop <name>        # Force stop
orca resume <name>      # Restart fresh
```
