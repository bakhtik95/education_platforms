# models/course.py
from datetime import datetime
from typing import Optional, Dict, Any, List
from core.utils import DateUtils


class CourseStatus:
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    DRAFT = 'draft'
    ARCHIVED = 'archived'

    @staticmethod
    def get_all():
        return [CourseStatus.ACTIVE, CourseStatus.INACTIVE, CourseStatus.DRAFT, CourseStatus.ARCHIVED]

    @staticmethod
    def is_valid(status: str) -> bool:
        return status in CourseStatus.get_all()


class CourseType:
    BASIC = 'asosiy'
    ADVANCED = 'ilg\'or'
    SPECIAL = 'maxsus'

    @staticmethod
    def get_all():
        return [CourseType.BASIC, CourseType.ADVANCED, CourseType.SPECIAL]

    @staticmethod
    def is_valid(course_type: str) -> bool:
        return course_type in CourseType.get_all()


class Course:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.title = data.get('title', '')
        self.description = data.get('description', '')
        self.image = data.get('image', 'default_course.jpg')
        self.type = data.get('type', CourseType.BASIC)
        self.status = data.get('status', CourseStatus.DRAFT)
        self.created_at = data.get('created_at', DateUtils.now())
        self.updated_at = data.get('updated_at')

        # Дополнительные поля
        self.modules_count = data.get('modules_count', 0)
        self.lessons_count = data.get('lessons_count', 0)
        self.duration = data.get('duration', 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'image': self.image,
            'type': self.type,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'modules_count': self.modules_count,
            'lessons_count': self.lessons_count,
            'duration': self.duration
        }

    def is_active(self) -> bool:
        return self.status == CourseStatus.ACTIVE

    def get_status_display(self) -> str:
        status_map = {
            CourseStatus.ACTIVE: 'Faol',
            CourseStatus.INACTIVE: 'Faol emas',
            CourseStatus.DRAFT: 'Qoralama',
            CourseStatus.ARCHIVED: 'Arxivlangan'
        }
        return status_map.get(self.status, self.status)

    def get_type_display(self) -> str:
        type_map = {
            CourseType.BASIC: 'Asosiy kurs',
            CourseType.ADVANCED: 'Ilg\'or kurs',
            CourseType.SPECIAL: 'Maxsus kurs'
        }
        return type_map.get(self.type, self.type)

    def get_image_url(self) -> str:
        if self.image and self.image != 'default_course.jpg':
            return f'/static/images/courses/{self.image}'
        return '/static/images/default_course.jpg'