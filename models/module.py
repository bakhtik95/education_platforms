# models/module.py
from datetime import datetime
from typing import Optional, Dict, Any, List
from core.utils import DateUtils


class Module:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.course_id = data.get('course_id')
        self.title = data.get('title', '')
        self.description = data.get('description', '')
        self.order = data.get('order', 0)
        self.created_at = data.get('created_at', DateUtils.now())
        self.updated_at = data.get('updated_at')

        # Дополнительные поля
        self.lessons_count = data.get('lessons_count', 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'order': self.order,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'lessons_count': self.lessons_count
        }

    def get_display_title(self) -> str:
        return self.title or f"Modul {self.order}"