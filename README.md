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
- `/api/leaderboard/` - Leaderboard data

### Frontend Development

The frontend is built with Svelte 5 and will include:

- User dashboard
- Contribution submission forms
- Global leaderboard
- Badge collection display

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