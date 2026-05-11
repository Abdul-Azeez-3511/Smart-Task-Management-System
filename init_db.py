"""
Run this ONCE to create all tables:
    python init_db.py
"""
from app import app, db

with app.app_context():
    db.create_all()
    print("✅ Database tables created successfully.")
