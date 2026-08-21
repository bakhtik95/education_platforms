# services/course_service.py
from typing import Optional, Dict, Any, List
from models import Course, CourseStatus, CourseType, Module, Lesson, LessonType
from core import JSONStorage, FileUtils, Utils
from core.utils import DateUtils


class CourseService:
    def __init__(self, storage: Optional[JSONStorage] = None):
        if storage is None:
            self.storage = JSONStorage()
        else:
            self.storage = storage

    def get_all_courses(self, status: str = None) -> List[Dict]:
        courses = self.storage.get_courses()
        if status:
            courses = [c for c in courses if c.get('status') == status]
        return courses

    def get_course(self, course_id: str) -> Optional[Dict]:
        return self.storage.get_course(course_id)

    def create_course(self, course_data: Dict) -> Dict:
        if 'status' not in course_data:
            course_data['status'] = CourseStatus.DRAFT

        if 'type' not in course_data:
            course_data['type'] = CourseType.BASIC

        return self.storage.create_course(course_data)

    def update_course(self, course_id: str, update_data: Dict) -> bool:
        update_data['updated_at'] = DateUtils.now()
        return self.storage.update_course(course_id, update_data)

    def delete_course(self, course_id: str) -> bool:
        return self.storage.delete_course(course_id)

    def get_course_stats(self) -> Dict:
        courses = self.get_all_courses()
        total = len(courses)
        active = len([c for c in courses if c.get('status') == CourseStatus.ACTIVE])
        draft = len([c for c in courses if c.get('status') == CourseStatus.DRAFT])
        archived = len([c for c in courses if c.get('status') == CourseStatus.ARCHIVED])

        return {
            'total': total,
            'active': active,
            'draft': draft,
            'archived': archived
        }

    def get_active_courses(self) -> List[Dict]:
        return self.get_all_courses(status=CourseStatus.ACTIVE)

    def get_course_modules(self, course_id: str) -> List[Dict]:
        return self.storage.get_modules(course_id)

    def get_module(self, module_id: str) -> Optional[Dict]:
        return self.storage.get_module(module_id)

    def create_module(self, module_data: Dict) -> Dict:
        modules = self.get_course_modules(module_data.get('course_id'))
        if modules:
            module_data['order'] = max([m.get('order', 0) for m in modules]) + 1
        else:
            module_data['order'] = 1

        return self.storage.create_module(module_data)

    def update_module(self, module_id: str, update_data: Dict) -> bool:
        update_data['updated_at'] = DateUtils.now()
        return self.storage.update_module(module_id, update_data)

    def delete_module(self, module_id: str) -> bool:
        return self.storage.delete_module(module_id)

    def reorder_modules(self, module_ids: List[str]) -> bool:
        for i, module_id in enumerate(module_ids, 1):
            self.storage.update_module(module_id, {'order': i})
        return True

    def get_module_lessons(self, module_id: str) -> List[Dict]:
        return self.storage.get_lessons(module_id)

    def get_course_lessons(self, course_id: str) -> List[Dict]:
        modules = self.get_course_modules(course_id)
        lessons = []
        for module in modules:
            module_lessons = self.get_module_lessons(module['id'])
            for lesson in module_lessons:
                lesson['course_id'] = course_id
                lesson['module_title'] = module['title']
                lessons.append(lesson)
        return lessons

    def get_lesson(self, lesson_id: str) -> Optional[Dict]:
        return self.storage.get_lesson(lesson_id)

    def create_lesson(self, lesson_data: Dict) -> Dict:
        lessons = self.get_module_lessons(lesson_data.get('module_id'))
        if lessons:
            lesson_data['order'] = max([l.get('order', 0) for l in lessons]) + 1
        else:
            lesson_data['order'] = 1

        if 'type' not in lesson_data:
            lesson_data['type'] = LessonType.TEXT

        return self.storage.create_lesson(lesson_data)

    def update_lesson(self, lesson_id: str, update_data: Dict) -> bool:
        update_data['updated_at'] = DateUtils.now()
        return self.storage.update_lesson(lesson_id, update_data)

    def delete_lesson(self, lesson_id: str) -> bool:
        return self.storage.delete_lesson(lesson_id)

    def reorder_lessons(self, lesson_ids: List[str]) -> bool:
        for i, lesson_id in enumerate(lesson_ids, 1):
            self.storage.update_lesson(lesson_id, {'order': i})
        return True

    def get_course_stats_with_details(self, course_id: str) -> Dict:
        course = self.get_course(course_id)
        if not course:
            return {}

        modules = self.get_course_modules(course_id)
        total_modules = len(modules)
        total_lessons = 0
        total_videos = 0
        total_duration = 0

        for module in modules:
            lessons = self.get_module_lessons(module['id'])
            total_lessons += len(lessons)
            for lesson in lessons:
                if lesson.get('type') == LessonType.VIDEO:
                    total_videos += 1
                    video = lesson.get('video')
                    if video:
                        total_duration += video.get('duration', 0)

        return {
            'course_id': course_id,
            'total_modules': total_modules,
            'total_lessons': total_lessons,
            'total_videos': total_videos,
            'total_duration': total_duration,
            'total_duration_hours': round(total_duration / 3600, 1)
        }

    def get_lesson_navigation(self, lesson_id: str) -> Dict:
        lesson = self.get_lesson(lesson_id)
        if not lesson:
            return {}

        lessons = self.get_module_lessons(lesson['module_id'])
        current_index = -1
        for i, l in enumerate(lessons):
            if l['id'] == lesson_id:
                current_index = i
                break

        return {
            'prev': lessons[current_index - 1] if current_index > 0 else None,
            'next': lessons[current_index + 1] if current_index < len(lessons) - 1 else None,
            'current': lesson
        }