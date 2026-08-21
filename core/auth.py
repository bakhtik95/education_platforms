# core/auth.py
from flask import session, request, redirect, url_for, render_template
from functools import wraps
from typing import Optional, Dict, Any
from .storage import JSONStorage
from .security import PasswordManager
from .utils import DateUtils


class AuthManager:
    def __init__(self, storage: JSONStorage):
        self.storage = storage

    def login(self, login: str, password: str) -> bool:
        user = self.storage.find_user_by_login(login)
        if not user:
            return False

        if not PasswordManager.verify_password(user.get('password_hash', ''), password):
            return False

        if user.get('status') not in ['active', 'admin']:
            return False

        session['user_id'] = user['id']
        session['role'] = user.get('role', 'user')
        session.permanent = True

        return True

    def logout(self):
        session.clear()

    def is_authenticated(self) -> bool:
        return 'user_id' in session

    def get_current_user(self) -> Optional[Dict]:
        if 'user_id' in session:
            return self.storage.get_user(session['user_id'])
        return None

    def get_current_user_id(self) -> Optional[str]:
        return session.get('user_id')

    def is_admin(self) -> bool:
        user = self.get_current_user()
        if not user:
            return False
        return user.get('role') == 'admin'

    def check_access(self, user_id: str, resource_type: str, resource_id: str) -> bool:
        user = self.storage.get_user(user_id)
        if not user:
            return False

        if user.get('role') == 'admin':
            return True

        if resource_type == 'course':
            access = self.storage.get_access(user_id, resource_id)
            if not access:
                return False
            return access.get('status') == 'active'

        if resource_type == 'lesson':
            lesson = self.storage.get_lesson(resource_id)
            if not lesson:
                return False
            module = self.storage.get_module(lesson.get('module_id'))
            if not module:
                return False
            return self.check_access(user_id, 'course', module.get('course_id'))

        return False


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Iltimos, tizimga kiring', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Iltimos, tizimga kiring', 'warning')
            return redirect(url_for('auth.login'))

        storage = JSONStorage()
        user = storage.get_user(session['user_id'])
        if not user or user.get('role') != 'admin':
            return render_template('error.html', code=403,
                                   message="Kirish taqiqlangan. Sizda ushbu sahifaga kirish huquqi mavjud emas."), 403

        return f(*args, **kwargs)

    return decorated_function


def course_access_required(f):
    @wraps(f)
    def decorated_function(course_id, *args, **kwargs):
        if 'user_id' not in session:
            flash('Iltimos, tizimga kiring', 'warning')
            return redirect(url_for('auth.login'))

        storage = JSONStorage()
        user = storage.get_user(session['user_id'])
        if not user:
            flash('Foydalanuvchi topilmadi', 'error')
            return redirect(url_for('auth.login'))

        if user.get('role') == 'admin':
            return f(course_id, *args, **kwargs)

        access = storage.get_access(session['user_id'], course_id)
        if not access or access.get('status') != 'active':
            flash('Sizda bu kursga kirish huquqi yo\'q', 'error')
            return redirect(url_for('user.courses'))

        return f(course_id, *args, **kwargs)

    return decorated_function


def flash(message: str, category: str = 'info'):
    from flask import flash as flask_flash
    flask_flash(message, category)