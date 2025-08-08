# Tally: GenLayer Testnet Program Tracking System

## 📚 Quick Reference Documentation
**Important**: This project has detailed documentation for faster development:
- **Backend Documentation**: See `backend/CLAUDE.md` for Django structure, API endpoints, models, and patterns
- **Frontend Documentation**: See `frontend/CLAUDE.md` for Svelte 5 structure, routes, components, and API integration
- **Session Management**: See `TALLY_SESSIONS.md` for the Git worktree-based development session system

⚠️ **Keep documentation updated**: When making changes to the codebase, update the relevant CLAUDE.md file to help future development sessions.

## Development Sessions & Worktrees
This project uses a custom session management system with Git worktrees. See `TALLY_SESSIONS.md` for complete documentation on:
- Creating and managing parallel development sessions
- Port allocation and tmux window management
- Claude Code session persistence across worktrees
- Troubleshooting common issues

Quick commands:
```bash
./tally-session add <name>     # Create new session
./tally-session list            # Show all sessions
./tally-session resume [name]   # Resume after restart
./tally-session remove <name>   # Remove session
```

## Svelte 5 Important Notes

### Runes Mode and Props
The frontend uses Svelte 5 with runes mode enabled. This means:
- **DO NOT use `export let` for props** - This will cause an error
- **ALWAYS use `$props()` instead** for component props

```javascript
// ❌ WRONG - This will cause an error in runes mode
export let params = {};

// ✅ CORRECT - Use $props() in Svelte 5
let { params = {} } = $props();
```

## Git Commit Guidelines

### No Attribution in Commits
When creating git commits, **DO NOT** include Claude attribution lines such as:
- 🤖 Generated with [Claude Code](https://claude.ai/code)
- Co-Authored-By: Claude <noreply@anthropic.com>

Keep commit messages clean and focused on the changes made.

## Environment Setup

### Frontend Development
When working with the frontend, always activate the Node.js environment before using npm commands:

```bash
# Activate the environment before using npm
cd [..]/tally/frontend
source ../backend/env/bin/activate
# Then run npm commands
npm install
npm run dev
npm test
```

### Backend Development
For backend development, activate the Python virtual environment:

```bash
# Activate the Python virtual environment
cd [..]/tally/backend
source env/bin/activate
# Then run Python/Django commands
python manage.py runserver
```

## Project Overview

Tally is a points and contribution tracking system specifically designed for the 
GenLayer Foundation's Testnet Program. It serves as a comprehensive platform that 
tracks, rewards, and visualizes community contributions to the GenLayer ecosystem. 
Each participant action earns badges and points, with the system applying dynamic 
multipliers to transform action points into global points that determine rankings 
on the leaderboard.

The system represents an experiment in creating autonomous and trustless GLF 
(GenLayer Foundation) programs that will eventually become part of the 
Deepthought DAO.

## Technical Architecture

### Backend (Python/Django)

The backend is built with Django and Django REST Framework, providing a robust 
API for tracking and managing contributions. The architecture consists of several 
key components:

1. **Main Django Apps**:
   - **users**: Custom user management system with email-based authentication
   - **contributions**: Tracking different types of contributions and their 
     associated points
   - **leaderboard**: Global ranking system with dynamic multipliers
   - **utils**: Shared utilities and base models
   - **api**: Core API functionality

2. **Database Models**:
   - **User**: Extended Django user model with additional fields for blockchain 
     address
   - **ContributionType**: Different categories of contributions (Node Running, 
     Uptime, Blog Posts, etc.)
   - **Contribution**: Individual contribution records linking users to 
     contribution types
   - **ContributionTypeMultiplier**: Dynamic multipliers for different 
     contribution types
   - **LeaderboardEntry**: User rankings based on total points

3. **Key Features**:
   - JWT-based authentication
   - CORS support for frontend integration
   - Automatic point calculation with multipliers
   - Dynamic rank calculations

### Frontend (Svelte 5)

The frontend is planned to be built with Svelte 5, though development appears to 
be in early stages with only the package.json file created. The frontend will 
provide:

1. **User Interface**:
   - Dashboard for viewing personal contributions
   - Global leaderboard
   - Contribution submission and verification
   - Badge collection display

2. **Integration**:
   - API integration with the Django backend
   - JWT authentication
   - Real-time updates

## Data Flow

1. **Contribution Recording**:
   - Users make contributions to the GenLayer ecosystem
   - Contributions are recorded with evidence (URLs, etc.)
   - Each contribution is assigned points based on its type

2. **Point Calculation**:
   - Base points are assigned to each contribution
   - Dynamic multipliers transform base points into global points
   - Multipliers can change over time, but previously calculated points remain 
     frozen

3. **Leaderboard Updates**:
   - User's total points are calculated from all contributions
   - Rankings are determined by total points
   - Ties receive the same rank

## Development Status

The project appears to be in its early stages of development. The backend 
structure is set up with Django apps and models defined, but many planned 
features are not yet implemented according to the ROADMAP.md. The frontend is 
just beginning development with only a package.json file created.

### Current Progress:
- Backend structure established
- Key models defined
- Authentication system set up
- API framework in place

### Next Steps (from ROADMAP.md):
- Complete database schema implementation
- Implement basic API endpoints
- Create Svelte 5 frontend skeleton
- Implement user authentication integration
- Develop badge and points system functionality

## Integration with GenLayer Ecosystem

Tally is designed to integrate with the broader GenLayer ecosystem, particularly 
the Testnet Program. It will serve as the official tracking system for:

1. **Validator Contributions**:
   - Node uptime
   - Network participation

2. **Developer Contributions**:
   - Code contributions
   - Bug reports
   - Documentation

3. **Community Contributions**:
   - Blog posts
   - Social media engagement
   - Community support

Long-term plans include integration with the Deepthought DAO and potential 
on-chain recognition of contributions.

## Future Considerations

According to the roadmap, future plans include:
1. Integration with the Deepthought DAO
2. On-chain recognition of contributions
3. Automated contribution verification
4. Mobile application development

The system is designed to be a stepping stone towards more autonomous and 
trustless governance mechanisms within the GenLayer ecosystem.