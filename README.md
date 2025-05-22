# Tally

A points and contribution tracking system for the GenLayer Foundation's Testnet 
Program.

## Overview

Tally is a comprehensive tracking system for the GenLayer Testnet Program 
incentives. It enables transparent monitoring of community contributions, with 
each action earning participants badges and points. The system serves as an 
experiment for developing autonomous and trustless GLF programs that will 
eventually be part of the Deepthought DAO.

## Features

- Track various contribution actions (Node Running, Uptime, Asimov, Blog Posts, 
  etc.)
- Award badges and action points to participants
- Apply dynamic multipliers to transform action points into global points
- Maintain a global leaderboard of all participants
- Provide transparent and open tracking of contributions

## Architecture

- **Backend**: Python-based Django REST API
- **Frontend**: Svelte 5

## Data Model

### Users App
- **User**: Custom user model with email as the unique identifier. Extends Django's AbstractUser with additional fields for name and address.

### Contributions App
- **ContributionType**: Represents different types of contributions participants can make (e.g., Node Runner, Uptime, Asimov, Blog Post).
- **Contribution**: Records specific contributions made by users, with points, evidence, and notes. Tracks a frozen point value that includes the multiplier at the time of creation.

### Leaderboard App
- **GlobalLeaderboardMultiplier**: Tracks multiplier values over time for each contribution type. Each multiplier has a valid_from date that determines when it becomes active.
- **LeaderboardEntry**: Represents a user's position on the leaderboard with their total points and rank.

### API App
- **Action**: Defines different types of actions participants can perform.
- **Participant**: Extends the User model with additional profile fields.
- **Badge**: Represents badges awarded to participants for completing actions.
- **Leaderboard**: Stores historical snapshots of the global leaderboard.
- **LeaderboardEntry**: Records a participant's position on a historical leaderboard snapshot.

### Utils App
- **BaseModel**: Abstract model providing created_at and updated_at fields for all models.

## Point Calculation System
1. Users make contributions of various types
2. Each contribution has base points
3. Contributions are multiplied by the active multiplier at the time of creation
4. The resulting "global points" are frozen and used for leaderboard rankings
5. Multipliers can change over time, but this doesn't affect previously awarded points

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL (optional, SQLite for development)

### Backend Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/tally.git
   cd tally
   ```

2. Create and activate a virtual environment:
   ```
   cd backend
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Setup Node.js environment using nodeenv:
   ```
   nodeenv -p
   ```

5. Run migrations:
   ```
   python manage.py migrate
   ```

6. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```
   python manage.py runserver
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Run the development server:
   ```
   npm run dev
   ```

## Development

### Backend Development

The backend is structured into several Django apps:

- **users**: Custom user management
- **contributions**: Tracking different types of contributions
- **leaderboard**: Global ranking system
- **utils**: Shared utilities
- **api**: Core API functionality

### API Endpoints

The following API endpoints will be available:

- `/api/users/` - User management
- `/api/auth/` - Authentication (login, refresh token)
- `/api/contributions/` - Contribution management
- `/api/contributions/types/` - Contribution types
- `/api/leaderboard/` - Leaderboard data
- `/api/leaderboard/multipliers/` - Manage contribution type multipliers
- `/api/participants/` - Participant profiles
- `/api/actions/` - Available actions
- `/api/badges/` - User badges

### Frontend Development

The frontend is built with Svelte 5 and will include:

- User dashboard with personal stats
- Contribution submission forms and history
- Global leaderboard with real-time rankings
- Badge collection display
- Participant profile pages
- Admin interfaces for managing contribution types and multipliers

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Workflow

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Run tests: `python manage.py test`
4. Push your branch: `git push origin feature/your-feature-name`
5. Submit a pull request

## License

See [LICENSE](./LICENSE) for details.

## About GenLayer Foundation

GenLayer's Testnet Program aims to reach Mainnet with the most mature and 
decentralized ecosystem possible. It's directed at professional Validators, 
Developers, and Community Contributors, working together to grow the GenLayer 
ecosystem.