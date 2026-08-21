# services/user_service.py
from typing import Optional, Dict, Any, List
from models import User, UserRoles, UserStatus, AccessType
from core import JSONStorage, SecurityManager, PasswordManager, Utils
from core.utils import DateUtils


class UserService:
    def __init__(self, storage: Optional[JSONStorage] = None):
        if storage is None:
            self.storage = JSONStorage()
        else:
            self.storage = storage
        self.security = SecurityManager(self.storage)

    def get_all_users(self) -> List[Dict]:
        return self.storage.get_users()

    def get_user(self, user_id: str) -> Optional[Dict]:
        return self.storage.get_user(user_id)

    def get_user_by_login(self, login: str) -> Optional[Dict]:
        return self.storage.find_user_by_login(login)

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        return self.storage.find_user_by_email(email)

    def create_user(self, user_data: Dict) -> Dict:
        valid, msg = User.validate_login(user_data.get('login', ''))
        if not valid:
            raise ValueError(msg)

        if user_data.get('email'):
            valid, msg = User.validate_email(user_data['email'])
            if not valid:
                raise ValueError(msg)

        if user_data.get('phone'):
            valid, msg = User.validate_phone(user_data['phone'])
            if not valid:
                raise ValueError(msg)

        if self.get_user_by_login(user_data['login']):
            raise ValueError("Bu login allaqachon mavjud")

        if user_data.get('email') and self.get_user_by_email(user_data['email']):
            raise ValueError("Bu email allaqachon mavjud")

        if 'password' in user_data:
            user_data['password_hash'] = PasswordManager.hash_password(user_data.pop('password'))
        elif 'password_hash' not in user_data:
            temp_password = PasswordManager.generate_temp_password()
            user_data['password_hash'] = PasswordManager.hash_password(temp_password)
            user_data['temp_password'] = temp_password

        if 'role' not in user_data:
            user_data['role'] = UserRoles.USER

        if 'status' not in user_data:
            user_data['status'] = UserStatus.PENDING

        if 'access_type' not in user_data:
            user_data['access_type'] = AccessType.FREE

        return self.storage.create_user(user_data)

    def update_user(self, user_id: str, update_data: Dict) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False

        if 'login' in update_data:
            valid, msg = User.validate_login(update_data['login'])
            if not valid:
                raise ValueError(msg)
            existing = self.get_user_by_login(update_data['login'])
            if existing and existing['id'] != user_id:
                raise ValueError("Bu login allaqachon mavjud")

        if 'email' in update_data and update_data['email']:
            valid, msg = User.validate_email(update_data['email'])
            if not valid:
                raise ValueError(msg)
            existing = self.get_user_by_email(update_data['email'])
            if existing and existing['id'] != user_id:
                raise ValueError("Bu email allaqachon mavjud")

        if 'phone' in update_data and update_data['phone']:
            valid, msg = User.validate_phone(update_data['phone'])
            if not valid:
                raise ValueError(msg)

        if 'password' in update_data:
            if update_data['password']:
                update_data['password_hash'] = PasswordManager.hash_password(update_data.pop('password'))
            else:
                del update_data['password']

        update_data['updated_at'] = DateUtils.now()

        return self.storage.update_user(user_id, update_data)

    def delete_user(self, user_id: str) -> bool:
        return self.storage.delete_user(user_id)

    def change_user_password(self, user_id: str, new_password: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False

        valid, errors = PasswordManager.validate_password_strength(new_password)
        if not valid:
            raise ValueError(", ".join(errors))

        return self.storage.update_user(user_id, {
            'password_hash': PasswordManager.hash_password(new_password),
            'updated_at': DateUtils.now()
        })

    def verify_user_password(self, user_id: str, password: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        return PasswordManager.verify_password(user['password_hash'], password)

    def block_user(self, user_id: str) -> bool:
        return self.storage.update_user(user_id, {
            'status': UserStatus.BLOCKED,
            'updated_at': DateUtils.now()
        })

    def unblock_user(self, user_id: str) -> bool:
        return self.storage.update_user(user_id, {
            'status': UserStatus.ACTIVE,
            'updated_at': DateUtils.now()
        })

    def get_stats(self) -> Dict:
        users = self.get_all_users()
        total = len(users)
        active = len([u for u in users if u.get('status') == UserStatus.ACTIVE])
        blocked = len([u for u in users if u.get('status') == UserStatus.BLOCKED])
        pending = len([u for u in users if u.get('status') == UserStatus.PENDING])
        free = len([u for u in users if u.get('access_type') == AccessType.FREE])
        paid = len([u for u in users if u.get('access_type') == AccessType.PAID])
        admins = len([u for u in users if u.get('role') == UserRoles.ADMIN])

        return {
            'total': total,
            'active': active,
            'blocked': blocked,
            'pending': pending,
            'free': free,
            'paid': paid,
            'admins': admins
        }

    def get_recent_users(self, limit: int = 5) -> List[Dict]:
        users = self.get_all_users()
        users.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return users[:limit]

    def search_users(self, query: str) -> List[Dict]:
        users = self.get_all_users()
        query = query.lower()
        results = []

        for user in users:
            if (query in user.get('full_name', '').lower() or
                    query in user.get('login', '').lower() or
                    query in user.get('email', '').lower() or
                    query in user.get('phone', '').lower()):
                results.append(user)

        return results