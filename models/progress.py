# models/progress.py
from datetime import datetime
from typing import Optional, Dict, Any
from core.utils import DateUtils


class Progress:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.course_id = data.get('course_id')
        self.module_id = data.get('module_id')
        self.lesson_id = data.get('lesson_id')
        self.completed = data.get('completed', False)
        self.video_position = data.get('video_position', 0)
        self.created_at = data.get('created_at', DateUtils.now())
        self.updated_at = data.get('updated_at', DateUtils.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'module_id': self.module_id,
            'lesson_id': self.lesson_id,
            'completed': self.completed,
            'video_position': self.video_position,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def get_video_position_display(self) -> str:
        if self.video_position:
            minutes = self.video_position // 60
            seconds = self.video_position % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"

    def get_status_icon(self) -> str:
        return '✓' if self.completed else '○'