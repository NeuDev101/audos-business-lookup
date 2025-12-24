"""
Database migration helper.

Provides a simple create_tables function to initialize the database schema.
For production, consider using Alembic for more sophisticated migrations.

Usage:
    python -m db.migrations
    or
    from db.migrations import create_tables
    create_tables()
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db import init_db, get_database_url, get_engine
from sqlalchemy import text


def create_tables():
    """
    Create all database tables.
    
    This function initializes the database schema by creating all tables
    defined in the models. It reads DATABASE_URL from environment.
    
    Raises:
        ValueError: If DATABASE_URL is not configured properly.
    """
    print(f"Initializing database at: {get_database_url()}")
    init_db()
    print("Database tables created successfully.")


def add_user_id_column():
    """
    Add user_id column to invoice_results table if it doesn't exist.
    This is a migration for existing databases.
    """
    engine = get_engine()
    with engine.connect() as conn:
        # Check if column exists (PostgreSQL)
        if 'postgresql' in get_database_url():
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='invoice_results' AND column_name='user_id'
            """))
            if result.fetchone():
                print("user_id column already exists")
                return
        
        # Check if column exists (SQLite)
        elif 'sqlite' in get_database_url():
            result = conn.execute(text("PRAGMA table_info(invoice_results)"))
            columns = [row[1] for row in result.fetchall()]
            if 'user_id' in columns:
                print("user_id column already exists")
                return
        
        # Add column
        try:
            conn.execute(text("ALTER TABLE invoice_results ADD COLUMN user_id INTEGER"))
            conn.commit()
            print("Added user_id column to invoice_results table")
        except Exception as e:
            print(f"Error adding user_id column: {e}")
            conn.rollback()


if __name__ == "__main__":
    create_tables()
    add_user_id_column()

