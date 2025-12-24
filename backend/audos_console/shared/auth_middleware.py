"""
Authentication middleware for Flask routes.
"""

import os
from functools import wraps
from flask import request, jsonify
from db.auth_models import verify_token, get_user_by_id

# Set DISABLE_AUTH=1 to bypass auth checks for local testing.
AUTH_DISABLED = os.getenv("DISABLE_AUTH", "").lower() in ("1", "true", "yes")


def require_auth(f):
    """
    Decorator to require authentication on a route.
    
    Expects Authorization: Bearer <token> header.
    Sets request.current_user_id and request.current_user_email on success.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if AUTH_DISABLED:
            # Bypass auth but keep a consistent shape for downstream code.
            request.current_user_id = 0
            request.current_user_email = "bypass@example.com"
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        
        token = auth_header[7:].strip()  # Remove "Bearer " prefix
        
        payload = verify_token(token, token_type="access")
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        if not user_id:
            return jsonify({"error": "Invalid token payload"}), 401
        
        # Verify user still exists
        from db.auth_models import get_user_by_id
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 401
        
        # Attach user info to request
        request.current_user_id = user_id
        request.current_user_email = email
        
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """
    Decorator for routes that work with or without auth.
    
    Sets request.current_user_id and request.current_user_email if token is valid,
    otherwise sets them to None.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if AUTH_DISABLED:
            request.current_user_id = 0
            request.current_user_email = "bypass@example.com"
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization")
        request.current_user_id = None
        request.current_user_email = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            payload = verify_token(token, token_type="access")
            if payload:
                user_id = payload.get("user_id")
                email = payload.get("email")
                if user_id:
                    from db.auth_models import get_user_by_id
                    user = get_user_by_id(user_id)
                    if user:
                        request.current_user_id = user_id
                        request.current_user_email = email
        
        return f(*args, **kwargs)
    
    return decorated_function
