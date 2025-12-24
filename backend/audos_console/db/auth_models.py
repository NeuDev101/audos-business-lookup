"""
User authentication models and utilities.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Index
from sqlalchemy.sql import func
import bcrypt
import jwt
import os
from typing import Optional, Dict

from .db import Base


class User(Base):
    """
    User model for authentication.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=True, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', username='{self.username}')>"

    def to_dict(self):
        """Convert user to dictionary (without password hash)."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password.
        
    Returns:
        Hashed password string.
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        password: Plain text password.
        password_hash: Hashed password from database.
        
    Returns:
        True if password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def get_jwt_secret() -> str:
    """
    Get JWT secret from environment.
    
    Raises:
        ValueError: If JWT_SECRET is not set.
    """
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise ValueError("JWT_SECRET environment variable is required")
    return secret


def create_access_token(user_id: int, email: str) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User ID.
        email: User email.
        
    Returns:
        JWT token string.
    """
    secret = get_jwt_secret()
    expires_in = int(os.environ.get("ACCESS_TOKEN_EXPIRES", 3600))  # Default 1 hour
    
    payload = {
        "user_id": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.utcnow().timestamp() + expires_in,
        "iat": datetime.utcnow().timestamp(),
    }
    
    return jwt.encode(payload, secret, algorithm="HS256")


def create_refresh_token(user_id: int, email: str) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User ID.
        email: User email.
        
    Returns:
        JWT refresh token string.
    """
    secret = get_jwt_secret()
    expires_in = int(os.environ.get("REFRESH_TOKEN_EXPIRES", 86400 * 7))  # Default 7 days
    
    payload = {
        "user_id": user_id,
        "email": email,
        "type": "refresh",
        "exp": datetime.utcnow().timestamp() + expires_in,
        "iat": datetime.utcnow().timestamp(),
    }
    
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(token: str, token_type: str = "access") -> Optional[Dict]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string.
        token_type: Expected token type ("access" or "refresh").
        
    Returns:
        Decoded payload dict if valid, None otherwise.
    """
    try:
        secret = get_jwt_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        # Verify token type
        if payload.get("type") != token_type:
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_user(email: str, password: str, username: Optional[str] = None) -> User:
    """
    Create a new user.
    
    Args:
        email: User email (must be unique).
        password: Plain text password.
        username: Optional username (must be unique if provided).
        
    Returns:
        Created User object.
        
    Raises:
        ValueError: If DATABASE_URL is not configured.
        Exception: Database errors (e.g., duplicate email/username).
    """
    from .db import get_session

    session = get_session()
    try:
        password_hash = hash_password(password)
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


def get_user_by_email(email: str) -> Optional[User]:
    """
    Get user by email.
    
    Args:
        email: User email.
        
    Returns:
        User object if found, None otherwise.
    """
    from .db import get_session

    session = get_session()
    try:
        return session.query(User).filter_by(email=email).first()
    finally:
        session.close()


def get_user_by_id(user_id: int) -> Optional[User]:
    """
    Get user by ID.
    
    Args:
        user_id: User ID.
        
    Returns:
        User object if found, None otherwise.
    """
    from .db import get_session

    session = get_session()
    try:
        return session.query(User).filter_by(id=user_id).first()
    finally:
        session.close()

