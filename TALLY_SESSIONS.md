# Tally Session Management System Documentation

## Overview
The Tally project uses a custom session management system that allows multiple parallel development sessions using Git worktrees, tmux, and Claude Code. Each session gets its own isolated environment with dedicated ports and persistent Claude conversations.

## Key Components

### 1. The `tally-session` Script
Location: `/Users/rasca/Dev/tally/tally-session`

This is the main management script with the following commands:
- `./tally-session add <name>` - Creates a new session with worktree, branch, and tmux windows
- `./tally-session remove <name>` - Removes a session completely (worktree, branch, tmux)
- `./tally-session resume [name]` - Resumes session(s) after system restart
- `./tally-session list` - Shows all active sessions with their ports

### 2. Session Structure
Each session consists of:
- **Git Worktree**: Located at `~/Dev/tally-<name>/`
- **Git Branch**: Named exactly as the session (e.g., `feature-auth`, not `session-feature-auth`)
- **Tmux Session**: Named `tally-<name>` with 5 windows:
  - `backend:<port>` - Django server running on the specified port
  - `frontend:<port>` - Svelte dev server running on the specified port
  - `claude` - Claude Code session running in worktree root
  - `shell` - Interactive shell with environment activated and ready
  - `cli` - Command line ready for one-off commands (env activated, not executed)

### 3. Port Management
- Backend ports start at 8000 and increment (8001, 8002, etc.)
- Frontend ports start at 5000 and increment (5001, 5002, etc.)
- Port assignments are tracked in `.tally-sessions` file to avoid conflicts
- The script automatically finds the next available ports when creating new sessions

### 4. Session Configuration File
Location: `/Users/rasca/Dev/tally/.tally-sessions`

JSON file tracking all sessions:
```json
{
  "session-name": {
    "backend_port": 8000,
    "frontend_port": 5000,
    "worktree": "/Users/rasca/Dev/tally-session-name",
    "branch": "session-name"
  }
}
```

## Automatic Setup Features

When creating a new session, the script automatically:

### 1. Creates Symlinks
- `frontend/node_modules` → symlinked to main project's node_modules (avoids reinstalling)

### 2. Copies Resources (Each Session Gets Its Own)
- `backend/db.sqlite3` → copied from main project (independent database per session)
- `backend/.env` - Copied from main project (contains SECRET_KEY and other env vars)
- `frontend/.env` - Copied from main project and updated with session-specific backend URL
  - Automatically sets `VITE_API_URL=http://localhost:<backend_port>` for proper API routing

### 3. Sets Up Claude Code
- Each Claude session uses a persistent name: `tally-<session-name>`
- When resuming: uses `--resume` flag to continue previous conversation
- Working directory is set to the worktree root

### 4. Activates Virtual Environment
All commands use `workon tally` to activate the Python virtual environment before executing

## Claude Tool Permissions

### Where Permissions Are Stored
Claude Code stores tool permissions in `~/.claude.json` under the `projects` section:
```json
{
  "projects": {
    "/Users/rasca/Dev/tally": {
      "allowedTools": [
        "Bash(npm install:*)",
        "Bash(python manage.py:*)",
        // ... other allowed tools
      ]
    }
  }
}
```

### Permission Inheritance Issue
Currently, each new worktree is treated as a separate project by Claude Code, so permissions need to be set up for each worktree. The script should copy the `allowedTools` array from the main project to each new worktree project in `~/.claude.json`.

## Common Workflows

### Creating a New Feature Session
```bash
./tally-session add feature-payment
tmux attach -t tally-feature-payment
# Work on your feature across backend, frontend, and Claude windows
```

### After System Restart
```bash
# Resume all sessions
./tally-session resume

# Or resume specific session
./tally-session resume feature-payment
```

### Cleaning Up
```bash
./tally-session remove feature-payment
# This removes the worktree, branch, and kills the tmux session
```

## Troubleshooting

### Port Already in Use
If you get "port already in use" errors:
1. Check `.tally-sessions` file for port assignments
2. Make sure the script's port allocation is working correctly
3. Kill any orphaned processes using `lsof -i :PORT | grep LISTEN`

### Missing Dependencies
If backend or frontend fail to start:
1. Check that `.env` files were copied correctly
2. Verify symlinks are intact (node_modules, db.sqlite3)
3. Ensure virtual environment is activated (`workon tally`)

### Claude Sessions
- Session names follow pattern: `tally-<session-name>`
- Use `--resume` flag to continue previous conversations
- Each worktree needs its own tool permissions in `~/.claude.json`

## Important Notes for Claude (AI Assistant)

When working with this system:
1. **Always use the worktree path** - Each session runs in its own worktree at `~/Dev/tally-<name>/`
2. **Port awareness** - Check `.tally-sessions` for assigned ports before suggesting localhost URLs
3. **Virtual environment** - All Python commands need `workon tally` first
4. **Independent databases** - Each session has its own database copy, changes don't affect other sessions
5. **Shared node_modules** - Node modules are symlinked to save space (read-only, shared)
6. **Git operations** - Each worktree has its own branch; commits don't affect other sessions
7. **Tool permissions** - New worktrees may need permission setup if not inherited from main project
8. **Frontend API URL** - Each session's frontend automatically points to its own backend port

## File Structure Example
```
~/Dev/
├── tally/                    # Main repository
│   ├── backend/
│   │   ├── .env             # Original env file
│   │   └── db.sqlite3       # Original database
│   ├── frontend/
│   │   ├── .env             # Original env file
│   │   └── node_modules/    # Original node modules
│   ├── tally-session        # Management script
│   └── .tally-sessions      # Session tracking file
│
├── tally-feature-auth/       # Worktree for feature-auth session
│   ├── backend/
│   │   ├── .env             # Copied from main
│   │   └── db.sqlite3       # Independent copy (not shared)
│   └── frontend/
│       ├── .env             # Copied & updated with backend port
│       └── node_modules/    # Symlink to main (shared)
│
└── tally-bugfix-ui/          # Another worktree
    └── ...                   # Same structure
```

## Session Commands Reference

Inside each tmux session, the windows and their states are:
- **backend:<port>**: Running Django server - `python manage.py runserver <port>`
- **frontend:<port>**: Running Svelte dev server - `npm run dev -- --port <port>`
- **claude**: Running Claude Code session - `claude tally-<name>` (or with `--resume`)
- **shell**: Interactive shell ready for use (environment activated, in worktree root)
- **cli**: Command line with environment ready but not executed (press Enter to run commands)

All windows have:
- Virtual environment activated: `workon tally`
- Working directory set: `cd ~/Dev/tally-<name>/[appropriate-dir]`

The port numbers are shown in the window names for easy reference.