# models/lesson.py
from datetime import datetime
from typing import Optional, Dict, Any, List
from core.utils import DateUtils, FileUtils


class LessonType:
    VIDEO = 'video'
    TEXT = 'text'
    ASSIGNMENT = 'assignment'
    TEST = 'test'

    @staticmethod
    def get_all():
        return [LessonType.VIDEO, LessonType.TEXT, LessonType.ASSIGNMENT, LessonType.TEST]

    @staticmethod
    def is_valid(lesson_type: str) -> bool:
        return lesson_type in LessonType.get_all()


class Lesson:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.module_id = data.get('module_id')
        self.title = data.get('title', '')
        self.type = data.get('type', LessonType.TEXT)
        self.description = data.get('description', '')
        self.content = data.get('content', '')
        self.video = data.get('video')
        self.files = data.get('files', [])
        self.order = data.get('order', 0)
        self.created_at = data.get('created_at', DateUtils.now())
        self.updated_at = data.get('updated_at')

        self.course_id = data.get('course_id')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'module_id': self.module_id,
            'title': self.title,
            'type': self.type,
            'description': self.description,
            'content': self.content,
            'video': self.video,
            'files': self.files,
            'order': self.order,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'course_id': self.course_id
        }

    def get_type_display(self) -> str:
        type_map = {
            LessonType.VIDEO: 'Video ma\'ruza',
            LessonType.TEXT: 'Ma\'ruza',
            LessonType.ASSIGNMENT: 'Topshiriq',
            LessonType.TEST: 'Test'
        }
        return type_map.get(self.type, self.type)

    def get_type_icon(self) -> str:
        icon_map = {
            LessonType.VIDEO: '🎬',
            LessonType.TEXT: '📝',
            LessonType.ASSIGNMENT: '📋',
            LessonType.TEST: '📊'
        }
        return icon_map.get(self.type, '📄')

    def has_video(self) -> bool:
        return self.video is not None and bool(self.video)

    def has_files(self) -> bool:
        return bool(self.files)

    def get_video_url(self) -> str:
        if self.has_video():
            return f'/media/video/{self.video["filename"]}'
        return None

    def get_video_duration_display(self) -> str:
        if self.has_video():
            duration = self.video.get('duration', 0)
            minutes = duration // 60
            seconds = duration % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"

    def get_file_size_display(self, file_data: Dict) -> str:
        return FileUtils.get_file_size_str(file_data.get('size', 0))