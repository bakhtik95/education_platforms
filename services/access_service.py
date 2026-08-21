# services/access_service.py
from typing import Optional, Dict, Any, List
from datetime import datetime
from models import AccessType, UserStatus
from core import JSONStorage, Utils
from core.utils import DateUtils


class AccessService:
    def __init__(self, storage: Optional[JSONStorage] = None):
        if storage is None:
            self.storage = JSONStorage()
        else:
            self.storage = storage

    def grant_access(self, user_id: str, course_id: str, access_type: str = 'free',
                     start_date: str = None, end_date: str = None) -> Dict:
        user = self.storage.get_user(user_id)
        if not user:
            raise ValueError("Foydalanuvchi topilmadi")

        course = self.storage.get_course(course_id)
        if not course:
            raise ValueError("Kurs topilmadi")

        existing = self.storage.get_access(user_id, course_id)
        if existing:
            update_data = {
                'type': access_type,
                'start_date': start_date,
                'end_date': end_date,
                'status': 'active',
                'updated_at': DateUtils.now()
            }
            self.storage.update_access(existing['id'], update_data)
            return self.storage.get_access(user_id, course_id)

        access_data = {
            'user_id': user_id,
            'course_id': course_id,
            'type': access_type,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'active'
        }

        return self.storage.create_access(access_data)

    def revoke_access(self, user_id: str, course_id: str) -> bool:
        return self.storage.delete_access(user_id, course_id)

    def check_access(self, user_id: str, course_id: str) -> bool:
        user = self.storage.get_user(user_id)
        if not user:
            return False

        if user.get('role') == 'admin':
            return True

        access = self.storage.get_access(user_id, course_id)
        if not access:
            return False

        if access.get('status') != 'active':
            return False

        if access.get('end_date'):
            if DateUtils.is_expired(access['end_date']):
                self.storage.update_access_status(access['id'], 'expired')
                return False

        return True

    def get_user_courses(self, user_id: str) -> List[Dict]:
        user = self.storage.get_user(user_id)
        if not user:
            return []

        if user.get('role') == 'admin':
            return self.storage.get_courses()

        accesses = self.storage.get_user_accesses(user_id)
        courses = []

        for access in accesses:
            if self.check_access(user_id, access['course_id']):
                course = self.storage.get_course(access['course_id'])
                if course and course.get('status') == 'active':
                    course['access_type'] = access.get('type')
                    course['access_start'] = access.get('start_date')
                    course['access_end'] = access.get('end_date')
                    courses.append(course)

        return courses

    def get_user_access_details(self, user_id: str) -> List[Dict]:
        accesses = self.storage.get_user_accesses(user_id)
        result = []

        for access in accesses:
            course = self.storage.get_course(access['course_id'])
            if course:
                result.append({
                    'access': access,
                    'course': course,
                    'is_active': self.check_access(user_id, access['course_id'])
                })

        return result

    def get_users_with_access(self, course_id: str) -> List[Dict]:
        accesses = self.storage.get_access(course_id=course_id)
        users = []

        for access in accesses:
            user = self.storage.get_user(access['user_id'])
            if user:
                access['user'] = user
                users.append(access)

        return users

    def update_access_status(self, user_id: str, course_id: str, status: str) -> bool:
        access = self.storage.get_access(user_id, course_id)
        if not access:
            return False

        return self.storage.update_access_status(access['id'], status)

    def extend_access(self, user_id: str, course_id: str, days: int) -> bool:
        access = self.storage.get_access(user_id, course_id)
        if not access:
            return False

        end_date = None
        if access.get('end_date'):
            end = DateUtils.parse_date(access['end_date'])
            if end:
                from datetime import timedelta
                new_end = end + timedelta(days=days)
                end_date = new_end.strftime('%Y-%m-%d')
        else:
            from datetime import timedelta
            new_end = datetime.now() + timedelta(days=days)
            end_date = new_end.strftime('%Y-%m-%d')

        return self.storage.update_access(access['id'], {
            'end_date': end_date,
            'updated_at': DateUtils.now()
        })

    def get_expired_accesses(self) -> List[Dict]:
        accesses = self.storage.get_access()
        expired = []

        for access in accesses:
            if access.get('end_date') and access.get('status') == 'active':
                if DateUtils.is_expired(access['end_date']):
                    expired.append(access)

        return expired

    def cleanup_expired_accesses(self) -> int:
        expired = self.get_expired_accesses()
        count = 0

        for access in expired:
            if self.storage.update_access_status(access['id'], 'expired'):
                count += 1

        return count

    def get_stats(self) -> Dict:
        accesses = self.storage.get_access()
        total = len(accesses)
        active = len([a for a in accesses if a.get('status') == 'active'])
        expired = len([a for a in accesses if a.get('status') == 'expired'])
        free = len([a for a in accesses if a.get('type') == 'free'])
        paid = len([a for a in accesses if a.get('type') == 'paid'])

        return {
            'total': total,
            'active': active,
            'expired': expired,
            'free': free,
            'paid': paid
        }