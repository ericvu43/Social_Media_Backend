### Backend README

# Social Network Platform - Backend

Backend service for the social networking platform.

## Features

- User Authentication
  - Login
  - Sign Up
  - Password Reset functionality
- Profile Management
- API for frontend integration

## Prerequisites

- Python 3.9 or later
- pip package manager
- PostgreSQL database

## Getting Started

1. Clone the repository:
```
git clone [your-backend-repository-url]
```

2. Navigate to the project directory:
```
cd p-466_group4-Backend
```

3. Create a virtual enviroment:
```
python -m venv venv
```

4. Activate the virtual environment:
- On Windows:
```
venv/scripts/activate
```
- On macOS/Linux:
```
source venv/bin/activate
```

5. Install dependencies
```
pip install -r requirements.txt
```

6. Create a .env file in the project root and add your email and project password:
```
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
```

7. Set up the database:
```
python manage.py migrate
```

8. Run the development server
```
python manage.py runserver
```

## Project Structure

```
social-network-backend/
├── accounts/                # User accounts app
├── api/                     # API endpoints
├── social_network/          # Project settings
├── manage.py                # Django management script
└── requirements.txt         # Project dependencies
```


