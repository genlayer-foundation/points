# Multi-Port Development Setup

## Overview
This project supports running multiple development instances simultaneously on different ports without session conflicts. This is useful when working with Git worktrees or testing different branches simultaneously.

## How It Works

### Session Cookie Isolation
The Django backend automatically creates port-specific session and CSRF cookies based on the port number used when running the development server. This prevents authentication sessions from interfering with each other across different development instances.

### Cookie Naming Convention
- Port 8000: `tally_sessionid_8000`, `tally_csrftoken_8000`
- Port 8001: `tally_sessionid_8001`, `tally_csrftoken_8001`
- Port 8002: `tally_sessionid_8002`, `tally_csrftoken_8002`
- Production: `tally_sessionid`, `csrftoken`

## Running Multiple Instances

### Backend Setup
Run each backend instance on a different port:

```bash
# Terminal 1 - Main development
cd backend
python manage.py runserver 8000

# Terminal 2 - Feature branch
cd ../tally-feature-branch/backend
python manage.py runserver 8001

# Terminal 3 - Bug fix branch
cd ../tally-bugfix/backend
python manage.py runserver 8002
```

### Frontend Setup
Configure each frontend to connect to its corresponding backend:

```bash
# Terminal 4 - Main development frontend
cd frontend
VITE_API_URL=http://localhost:8000 npm run dev -- --port 5000

# Terminal 5 - Feature branch frontend
cd ../tally-feature-branch/frontend
VITE_API_URL=http://localhost:8001 npm run dev -- --port 5001

# Terminal 6 - Bug fix branch frontend
cd ../tally-bugfix/frontend
VITE_API_URL=http://localhost:8002 npm run dev -- --port 5002
```

## Benefits

1. **No Session Conflicts**: Each development instance maintains its own authentication session
2. **Parallel Testing**: Test different features or branches simultaneously
3. **Worktree Support**: Perfect for Git worktree workflows
4. **Independent States**: Each instance can have different logged-in users or states

## Important Notes

1. **Development Only**: This feature only works in DEBUG mode. Production deployments use standard cookie names.

2. **Browser Isolation**: Sessions are isolated per port, so:
   - Logging in on `localhost:5000` won't affect `localhost:5001`
   - Each instance maintains its own authentication state
   - You can be logged in as different users on different ports

3. **Database Sharing**: All instances still share the same database by default. If you need separate databases:
   ```bash
   # Use different database files
   DATABASE_URL=sqlite:///./db_8001.sqlite3 python manage.py runserver 8001
   ```

4. **Cookie Cleanup**: Old session cookies from different ports will accumulate in your browser. You can clear them periodically through your browser's developer tools.

## Troubleshooting

### Sessions Still Conflicting
- Ensure the backend is running with the correct port argument
- Check the console output for: `[DEV] Using port-specific cookies for port XXXX`
- Clear browser cookies and try again

### Can't Connect Frontend to Backend
- Verify VITE_API_URL matches the backend port
- Check CORS settings allow the frontend port
- Ensure both frontend and backend are running

### Authentication Not Persisting
- Check browser developer tools for the correct cookie names
- Verify SESSION_COOKIE_DOMAIN is set to None (not 'localhost')
- Ensure cookies are not being blocked by browser settings