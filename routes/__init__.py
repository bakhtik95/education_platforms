# routes/__init__.py
from .auth import auth_bp
from .user import user_bp
from .course import course_bp
from .admin import admin_bp

__all__ = [
    'auth_bp',
    'user_bp',
    'course_bp',
    'admin_bp'
]