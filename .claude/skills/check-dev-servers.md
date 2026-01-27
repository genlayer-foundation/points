# Check Dev Servers

Check the tmux session for backend and frontend dev server status, read errors, and relaunch if needed.

## Instructions

1. **Find the tmux session** for the current worktree:
   - Get the worktree directory name from `basename $PWD` or the known session name
   - The session name matches the worktree directory name
   - Window 1 = backend (Django runserver), Window 2 = frontend (npm run dev)

2. **Capture output from both windows** in parallel:
   ```bash
   tmux capture-pane -t '<session>:1' -p -S -80
   tmux capture-pane -t '<session>:2' -p -S -80
   ```

3. **Analyze the output**:
   - Look for Python tracebacks, Django errors, or "Error" messages in window 1
   - Look for build errors, compilation failures, or crash messages in window 2
   - Svelte a11y warnings are NOT errors - ignore them
   - Report findings to the user

4. **Relaunch if server is down**:
   - For backend (window 1): Extract the port from the window name (e.g., `backend:8004` means port 8004)
     ```bash
     tmux send-keys -t '<session>:1' 'workon tally && cd /Users/rasca/Dev/<worktree>/backend && python manage.py runserver <port>' Enter
     ```
   - For frontend (window 2): Extract the port from the window name (e.g., `frontend:5004` means port 5004)
     ```bash
     tmux send-keys -t '<session>:2' 'source ../backend/env/bin/activate && cd /Users/rasca/Dev/<worktree>/frontend && npm run dev -- --port <port>' Enter
     ```

5. **Wait a few seconds then verify** the server started successfully:
   ```bash
   sleep 3
   tmux capture-pane -t '<session>:<window>' -p -S -20
   ```

## Common Issues
- Missing environment variables in `.env` -> check `.env.example` for defaults
- Port already in use -> check with `lsof -i :<port>`
- Missing dependencies -> run `pip install -r requirements.txt` or `npm install`
