# services/progress_service.py
from typing import Optional, Dict, Any, List
from core import JSONStorage
from core.utils import DateUtils


class ProgressService:
    def __init__(self, storage: Optional[JSONStorage] = None):
        if storage is None:
            self.storage = JSONStorage()
        else:
            self.storage = storage

    def update_progress(self, user_id: str, lesson_id: str,
                        video_position: int = 0, completed: bool = False) -> bool:
        lesson = self.storage.get_lesson(lesson_id)
        if not lesson:
            return False

        module = self.storage.get_module(lesson.get('module_id'))
        if not module:
            return False

        course_id = module.get('course_id')

        existing = self.storage.get_progress(user_id, lesson_id)

        if existing:
            update_data = {
                'video_position': video_position,
                'completed': completed,
                'updated_at': DateUtils.now()
            }
            return self.storage.update_progress(user_id, lesson_id, update_data)
        else:
            progress_data = {
                'user_id': user_id,
                'course_id': course_id,
                'module_id': lesson.get('module_id'),
                'lesson_id': lesson_id,
                'video_position': video_position,
                'completed': completed
            }
            self.storage.create_progress(progress_data)
            return True

    def get_lesson_progress(self, user_id: str, lesson_id: str) -> Dict:
        progress = self.storage.get_progress(user_id, lesson_id)
        if progress:
            return progress

        return {
            'user_id': user_id,
            'lesson_id': lesson_id,
            'completed': False,
            'video_position': 0
        }

    def get_course_progress(self, user_id: str, course_id: str) -> Dict:
        from .course_service import CourseService
        course_service = CourseService(self.storage)
        lessons = course_service.get_course_lessons(course_id)

        if not lessons:
            return {
                'progress': 0,
                'completed': 0,
                'total': 0,
                'status': 'not_started'
            }

        total = len(lessons)
        completed = 0
        lesson_progress = []

        for lesson in lessons:
            progress = self.get_lesson_progress(user_id, lesson['id'])
            if progress.get('completed', False):
                completed += 1
            lesson_progress.append({
                'lesson_id': lesson['id'],
                'title': lesson.get('title'),
                'completed': progress.get('completed', False),
                'video_position': progress.get('video_position', 0)
            })

        progress_percent = int((completed / total) * 100) if total > 0 else 0

        status = 'not_started'
        if progress_percent == 100:
            status = 'completed'
        elif progress_percent > 0:
            status = 'in_progress'

        return {
            'progress': progress_percent,
            'completed': completed,
            'total': total,
            'status': status,
            'lessons': lesson_progress
        }

    def get_module_progress(self, user_id: str, module_id: str) -> Dict:
        lessons = self.storage.get_lessons(module_id)

        if not lessons:
            return {
                'progress': 0,
                'completed': 0,
                'total': 0
            }

        total = len(lessons)
        completed = 0

        for lesson in lessons:
            progress = self.get_lesson_progress(user_id, lesson['id'])
            if progress.get('completed', False):
                completed += 1

        progress_percent = int((completed / total) * 100) if total > 0 else 0

        return {
            'progress': progress_percent,
            'completed': completed,
            'total': total
        }

    def get_user_courses_progress(self, user_id: str) -> List[Dict]:
        from .access_service import AccessService
        access_service = AccessService(self.storage)
        courses = access_service.get_user_courses(user_id)

        result = []
        for course in courses:
            progress = self.get_course_progress(user_id, course['id'])
            result.append({
                'course': course,
                'progress': progress
            })

        return result

    def get_user_stats(self, user_id: str) -> Dict:
        progress_list = self.storage.get_user_progress(user_id)

        total_lessons = len(progress_list)
        completed_lessons = len([p for p in progress_list if p.get('completed', False)])

        course_ids = set()
        for p in progress_list:
            if p.get('course_id'):
                course_ids.add(p['course_id'])

        total_courses = len(course_ids)
        completed_courses = 0

        for course_id in course_ids:
            progress = self.get_course_progress(user_id, course_id)
            if progress.get('progress') == 100:
                completed_courses += 1

        total_watch_time = sum([p.get('video_position', 0) for p in progress_list])

        return {
            'total_courses': total_courses,
            'completed_courses': completed_courses,
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'total_watch_time': total_watch_time,
            'total_watch_time_hours': round(total_watch_time / 3600, 1)
        }

    def mark_lesson_completed(self, user_id: str, lesson_id: str) -> bool:
        return self.update_progress(user_id, lesson_id, completed=True)

    def reset_lesson_progress(self, user_id: str, lesson_id: str) -> bool:
        progress = self.storage.get_progress(user_id, lesson_id)
        if not progress:
            return True

        return self.storage.update_progress(user_id, lesson_id, {
            'completed': False,
            'video_position': 0,
            'updated_at': DateUtils.now()
        })

    def reset_course_progress(self, user_id: str, course_id: str) -> bool:
        from .course_service import CourseService
        course_service = CourseService(self.storage)
        lessons = course_service.get_course_lessons(course_id)

        for lesson in lessons:
            self.reset_lesson_progress(user_id, lesson['id'])

        return True