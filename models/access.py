# models/access.py
from datetime import datetime
from typing import Optional, Dict, Any
from core.utils import DateUtils


class Access:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.course_id = data.get('course_id')
        self.type = data.get('type', 'free')
        self.start_date = data.get('start_date')
        self.end_date = data.get('end_date')
        self.status = data.get('status', 'active')
        self.created_at = data.get('created_at', DateUtils.now())
        self.updated_at = data.get('updated_at')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'type': self.type,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def is_active(self) -> bool:
        if self.status != 'active':
            return False
        if self.end_date and DateUtils.is_expired(self.end_date):
            return False
        return True

    def get_type_display(self) -> str:
        type_map = {
            'free': 'Bepul',
            'paid': 'Pullik'
        }
        return type_map.get(self.type, self.type)

    def get_status_display(self) -> str:
        status_map = {
            'active': 'Faol',
            'expired': 'Muddati o\'tgan',
            'pending': 'Kutilmoqda'
        }
        return status_map.get(self.status, self.status)

    def get_duration_display(self) -> str:
        if self.start_date and self.end_date:
            days = DateUtils.days_diff(self.start_date, self.end_date)
            return f"{days} kun"
        return "Cheksiz"