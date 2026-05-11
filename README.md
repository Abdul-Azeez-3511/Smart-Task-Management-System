# TaskFlow — Smart Task Management System

A full-stack task management web application built with **Python/Flask**, **PostgreSQL**, **Pandas & NumPy**, and **WebSockets**.

---

## Tech Stack

| Layer        | Technology                          |
|-------------|--------------------------------------|
| Backend     | Python 3.10+, Flask 3               |
| Database    | PostgreSQL + SQLAlchemy ORM         |
| Analytics   | Pandas, NumPy                       |
| Real-time   | Flask-SocketIO (WebSockets)         |
| Frontend    | HTML5, CSS3 (vanilla), JavaScript   |
| Auth        | Werkzeug password hashing, sessions |

---

## Features

### 1. Authentication
- User **Registration** (username, email, password)
- User **Login** with session management
- **Logout** functionality
- Password hashing with Werkzeug (bcrypt)

### 2. REST API

| Method | Endpoint               | Description          |
|--------|------------------------|----------------------|
| POST   | `/api/auth/register`   | Register new user    |
| POST   | `/api/auth/login`      | Login                |
| POST   | `/api/auth/logout`     | Logout               |
| GET    | `/api/auth/me`         | Current user info    |
| GET    | `/api/tasks`           | Get all tasks        |
| POST   | `/api/tasks`           | Create task          |
| PUT    | `/api/tasks/<id>`      | Update task          |
| DELETE | `/api/tasks/<id>`      | Delete task          |
| GET    | `/api/analytics`       | Analytics data       |

Each task contains: **title**, **description**, **priority** (low/medium/high), **status** (pending/in_progress/completed).

### 3. PostgreSQL Integration
Two tables:
- `users` — id, username, email, password_hash, created_at
- `tasks` — id, title, description, priority, status, user_id (FK), created_at, updated_at

### 4. Analytics (Pandas & NumPy)
- Total Tasks
- Completed Tasks
- Pending Tasks
- Completion Percentage (`numpy.round`)
- Priority breakdown
- Average tasks per day

### 5. WebSockets (Flask-SocketIO)
- Real-time task updates pushed to the client
- Toast notifications on task create / update / delete
- Live indicator in the dashboard header

### 6. Frontend
- Clean dark UI with sidebar navigation
- Task list with filters (All / Pending / In Progress / Completed)
- Add / Edit task modal
- Analytics dashboard with progress bars
- Fully responsive

---

## Setup & Run

### Prerequisites
- Python 3.10+
- PostgreSQL running locally (or a connection URL)

### 1 — Clone / copy the project
```bash
cd task_manager
```

### 2 — Create virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### 4 — Configure environment
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 5 — Create the database
```sql
-- In psql:
CREATE DATABASE taskmanager;
```
Then:
```bash
python init_db.py
```

### 6 — Run the app
```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## Project Structure

```
task_manager/
├── app.py              # Main Flask app (routes, models, WebSocket)
├── init_db.py          # One-time DB table creation script
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── templates/
    ├── auth.html       # Login / Register page
    └── dashboard.html  # Main dashboard (tasks + analytics)
```

---

## API Examples (curl)

```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"secret123"}'

# Add a task
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"title":"Design UI","description":"Create wireframes","priority":"high"}'

# Get analytics
curl http://localhost:5000/api/analytics -b cookies.txt
```
