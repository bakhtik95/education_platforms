# core/security.py
import re
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional, Dict, Any


class PasswordManager:
    @staticmethod
    def hash_password(password: str) -> str:
        return generate_password_hash(password, method='scrypt')

    @staticmethod
    def verify_password(password_hash: str, password: str) -> bool:
        return check_password_hash(password_hash, password)

    @staticmethod
    def validate_password_strength(password: str) -> tuple:
        errors = []

        if len(password) < 6:
            errors.append("Parol kamida 6 ta belgidan iborat bo'lishi kerak")

        if not re.search(r'[A-Z]', password):
            errors.append("Parolda kamida 1 ta katta harf bo'lishi kerak")

        if not re.search(r'[a-z]', password):
            errors.append("Parolda kamida 1 ta kichik harf bo'lishi kerak")

        if not re.search(r'\d', password):
            errors.append("Parolda kamida 1 ta raqam bo'lishi kerak")

        return len(errors) == 0, errors

    @staticmethod
    def generate_temp_password() -> str:
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%'
        return ''.join(secrets.choice(alphabet) for _ in range(10))


class SecurityManager:
    def __init__(self, storage):
        self.storage = storage

    def verify_access(self, user_id: str, resource_type: str, resource_id: str) -> bool:
        user = self.storage.get_user(user_id)
        if not user:
            return False

        if user.get('role') == 'admin':
            return True

        if resource_type == 'course':
            return self._has_course_access(user_id, resource_id)
        elif resource_type == 'lesson':
            return self._has_lesson_access(user_id, resource_id)
        elif resource_type == 'file':
            return self._has_file_access(user_id, resource_id)
        elif resource_type == 'video':
            return self._has_video_access(user_id, resource_id)

        return False

    def _has_course_access(self, user_id: str, course_id: str) -> bool:
        access = self.storage.get_access(user_id, course_id)
        if not access:
            return False

        if access.get('end_date'):
            from .utils import DateUtils
            if DateUtils.is_expired(access['end_date']):
                self.storage.update_access_status(access.get('id'), 'expired')
                return False

        return access.get('status') == 'active'

    def _has_lesson_access(self, user_id: str, lesson_id: str) -> bool:
        lesson = self.storage.get_lesson(lesson_id)
        if not lesson:
            return False

        return self._has_course_access(user_id, lesson.get('course_id'))

    def _has_file_access(self, user_id: str, file_id: str) -> bool:
        file_data = self.storage.get_file(file_id)
        if not file_data:
            return False

        lesson = self.storage.get_lesson_by_file(file_id)
        if not lesson:
            return False

        return self._has_lesson_access(user_id, lesson.get('id'))

    def _has_video_access(self, user_id: str, video_filename: str) -> bool:
        lesson = self.storage.get_lesson_by_video(video_filename)
        if not lesson:
            return False

        return self._has_lesson_access(user_id, lesson.get('id'))

    def sanitize_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = re.sub(r'[<>]', '', value.strip())
            else:
                sanitized[key] = value
        return sanitized

    def validate_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def validate_phone(self, phone: str) -> bool:
        phone = re.sub(r'[\s\-()]', '', phone)
        pattern = r'^\+?998[0-9]{9}$|^[0-9]{9,12}$'
        return re.match(pattern, phone) is not None