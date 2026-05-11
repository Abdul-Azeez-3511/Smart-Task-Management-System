from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import pandas as pd
import numpy as np
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:Ajees5204@localhost:5432/taskmanager'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ─────────────────────────── MODELS ────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    tasks         = db.relationship('Task', backref='owner', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {'id': self.id, 'username': self.username, 'email': self.email}


class Task(db.Model):
    __tablename__ = 'tasks'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    priority    = db.Column(db.String(20), default='medium')   # low / medium / high
    status      = db.Column(db.String(20), default='pending')  # pending / in_progress / completed
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id':          self.id,
            'title':       self.title,
            'description': self.description,
            'priority':    self.priority,
            'status':      self.status,
            'user_id':     self.user_id,
            'created_at':  self.created_at.isoformat(),
            'updated_at':  self.updated_at.isoformat(),
        }

# ──────────────────────── AUTH HELPERS ─────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated

def current_user():
    return User.query.get(session['user_id']) if 'user_id' in session else None

# ────────────────────── PAGE ROUTES ────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('auth.html', mode='login')

@app.route('/register')
def register_page():
    return render_template('auth.html', mode='register')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('dashboard.html')

# ────────────────────── AUTH APIS ──────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    return jsonify({'message': 'Registration successful', 'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data     = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401

    session['user_id'] = user.id
    return jsonify({'message': 'Login successful', 'user': user.to_dict()})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'})


@app.route('/api/auth/me', methods=['GET'])
@login_required
def me():
    return jsonify(current_user().to_dict())

# ────────────────────── TASK APIS ──────────────────────────────

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    uid    = session['user_id']
    status = request.args.get('status')
    prio   = request.args.get('priority')

    q = Task.query.filter_by(user_id=uid)
    if status:
        q = q.filter_by(status=status)
    if prio:
        q = q.filter_by(priority=prio)

    tasks = q.order_by(Task.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tasks])


@app.route('/api/tasks', methods=['POST'])
@login_required
def add_task():
    data  = request.get_json()
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400

    priority = data.get('priority', 'medium')
    if priority not in ('low', 'medium', 'high'):
        return jsonify({'error': 'Invalid priority'}), 400

    task = Task(
        title       = title,
        description = data.get('description', ''),
        priority    = priority,
        status      = 'pending',
        user_id     = session['user_id'],
    )
    db.session.add(task)
    db.session.commit()

    # Broadcast via WebSocket
    socketio.emit('task_update', {
        'action': 'created',
        'task':   task.to_dict(),
    }, room=f"user_{session['user_id']}")

    return jsonify(task.to_dict()), 201


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first()
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    data = request.get_json()
    if 'title' in data:
        task.title = data['title'].strip() or task.title
    if 'description' in data:
        task.description = data['description']
    if 'priority' in data and data['priority'] in ('low', 'medium', 'high'):
        task.priority = data['priority']
    if 'status' in data and data['status'] in ('pending', 'in_progress', 'completed'):
        task.status = data['status']
    task.updated_at = datetime.utcnow()
    db.session.commit()

    socketio.emit('task_update', {
        'action': 'updated',
        'task':   task.to_dict(),
    }, room=f"user_{session['user_id']}")

    return jsonify(task.to_dict())


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first()
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    task_data = task.to_dict()
    db.session.delete(task)
    db.session.commit()

    socketio.emit('task_update', {
        'action':  'deleted',
        'task_id': task_id,
    }, room=f"user_{session['user_id']}")

    return jsonify({'message': 'Task deleted', 'task': task_data})

# ────────────────────── ANALYTICS API ──────────────────────────

@app.route('/api/analytics', methods=['GET'])
@login_required
def analytics():
    tasks = Task.query.filter_by(user_id=session['user_id']).all()
    if not tasks:
        return jsonify({
            'total': 0, 'completed': 0, 'pending': 0,
            'in_progress': 0, 'completion_pct': 0,
            'priority_breakdown': {}, 'avg_tasks_per_day': 0,
        })

    df = pd.DataFrame([t.to_dict() for t in tasks])

    total       = int(len(df))
    completed   = int((df['status'] == 'completed').sum())
    pending     = int((df['status'] == 'pending').sum())
    in_progress = int((df['status'] == 'in_progress').sum())
    comp_pct    = float(np.round((completed / total) * 100, 2)) if total else 0.0

    priority_counts = df['priority'].value_counts().to_dict()
    priority_counts = {k: int(v) for k, v in priority_counts.items()}

    df['created_at'] = pd.to_datetime(df['created_at'])
    days_active      = max((df['created_at'].max() - df['created_at'].min()).days, 1)
    avg_per_day      = float(np.round(total / days_active, 2))

    return jsonify({
        'total':              total,
        'completed':          completed,
        'pending':            pending,
        'in_progress':        in_progress,
        'completion_pct':     comp_pct,
        'priority_breakdown': priority_counts,
        'avg_tasks_per_day':  avg_per_day,
    })

# ─────────────────────── WEBSOCKET ─────────────────────────────

@socketio.on('join')
def on_join(data):
    if 'user_id' in session:
        room = f"user_{session['user_id']}"
        join_room(room)
        emit('joined', {'room': room})

@socketio.on('connect')
def on_connect():
    if 'user_id' in session:
        join_room(f"user_{session['user_id']}")

# ───────────────────────── INIT ────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
