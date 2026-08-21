# core/storage.py
import os
import json
import tempfile
import shutil
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from filelock import FileLock
from .utils import Utils, FileUtils, DateUtils
from config import get_config


class JSONStorage:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            config = get_config()
            data_dir = config.DATA_DIR

        self.data_dir = data_dir
        self.lock_dir = os.path.join(data_dir, '.locks')
        self._ensure_directories()

    def _ensure_directories(self):
        dirs = [
            self.data_dir,
            self.lock_dir,
            os.path.join(self.data_dir, 'users'),
            os.path.join(self.data_dir, 'courses'),
            os.path.join(self.data_dir, 'modules'),
            os.path.join(self.data_dir, 'lessons'),
            os.path.join(self.data_dir, 'access'),
            os.path.join(self.data_dir, 'progress'),
            os.path.join(self.data_dir, 'settings')
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)

    def _get_lock_path(self, filename: str) -> str:
        return os.path.join(self.lock_dir, f'{filename}.lock')

    def _read_json(self, filename: str) -> Optional[Dict]:
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            backup_path = f'{filepath}.backup'
            if os.path.exists(backup_path):
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    pass
            return None

    def _write_json(self, filename: str, data: Dict, create_backup: bool = True):
        filepath = os.path.join(self.data_dir, filename)
        lock_path = self._get_lock_path(filename)

        if create_backup and os.path.exists(filepath):
            backup_path = f'{filepath}.backup'
            shutil.copy2(filepath, backup_path)

        lock = FileLock(lock_path, timeout=10)

        with lock:
            try:
                fd, temp_path = tempfile.mkstemp(
                    dir=self.data_dir,
                    prefix=f'.tmp_{filename}_',
                    suffix='.tmp'
                )

                try:
                    with os.fdopen(fd, 'w', encoding='utf-8') as temp_file:
                        json.dump(data, temp_file, indent=2, ensure_ascii=False)
                        temp_file.flush()
                        os.fsync(fd)

                    os.replace(temp_path, filepath)

                except Exception as e:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    raise e

            except Exception as e:
                raise e

    def _get_next_id(self, data: Dict, key: str = 'last_id') -> int:
        return data.get(key, 0) + 1

    def get_users(self) -> List[Dict]:
        data = self._read_json('users.json')
        return data.get('users', []) if data else []

    def get_user(self, user_id: str) -> Optional[Dict]:
        users = self.get_users()
        for user in users:
            if user.get('id') == user_id:
                return user
        return None

    def find_user_by_login(self, login: str) -> Optional[Dict]:
        users = self.get_users()
        for user in users:
            if user.get('login', '').lower() == login.lower():
                return user
        return None

    def find_user_by_email(self, email: str) -> Optional[Dict]:
        users = self.get_users()
        for user in users:
            if user.get('email', '').lower() == email.lower():
                return user
        return None

    def create_user(self, user_data: Dict) -> Dict:
        data = self._read_json('users.json') or {'users': [], 'last_id': 0}

        user_id = f"USR-{str(self._get_next_id(data)).zfill(6)}"
        data['last_id'] = self._get_next_id(data)

        user_data['id'] = user_id
        user_data['created_at'] = DateUtils.now()

        data['users'].append(user_data)
        self._write_json('users.json', data)

        return user_data

    def update_user(self, user_id: str, update_data: Dict) -> bool:
        data = self._read_json('users.json')
        if not data:
            return False

        for i, user in enumerate(data['users']):
            if user.get('id') == user_id:
                for key, value in update_data.items():
                    if key not in ['id', 'created_at']:
                        user[key] = value
                data['users'][i] = user
                self._write_json('users.json', data)
                return True

        return False

    def delete_user(self, user_id: str) -> bool:
        data = self._read_json('users.json')
        if not data:
            return False

        data['users'] = [u for u in data['users'] if u.get('id') != user_id]
        self._write_json('users.json', data)

        self.delete_user_access(user_id)
        self.delete_user_progress(user_id)

        return True

    def get_courses(self) -> List[Dict]:
        data = self._read_json('courses.json')
        return data.get('courses', []) if data else []

    def get_course(self, course_id: str) -> Optional[Dict]:
        courses = self.get_courses()
        for course in courses:
            if course.get('id') == course_id:
                return course
        return None

    def create_course(self, course_data: Dict) -> Dict:
        data = self._read_json('courses.json') or {'courses': [], 'last_id': 0}

        course_id = f"CRS-{str(self._get_next_id(data)).zfill(6)}"
        data['last_id'] = self._get_next_id(data)

        course_data['id'] = course_id
        course_data['created_at'] = DateUtils.now()

        data['courses'].append(course_data)
        self._write_json('courses.json', data)

        return course_data

    def update_course(self, course_id: str, update_data: Dict) -> bool:
        data = self._read_json('courses.json')
        if not data:
            return False

        for i, course in enumerate(data['courses']):
            if course.get('id') == course_id:
                for key, value in update_data.items():
                    if key not in ['id', 'created_at']:
                        course[key] = value
                data['courses'][i] = course
                self._write_json('courses.json', data)
                return True

        return False

    def delete_course(self, course_id: str) -> bool:
        data = self._read_json('courses.json')
        if not data:
            return False

        data['courses'] = [c for c in data['courses'] if c.get('id') != course_id]
        self._write_json('courses.json', data)

        self.delete_course_modules(course_id)
        self.delete_course_access(course_id)

        return True

    def get_modules(self, course_id: str = None) -> List[Dict]:
        data = self._read_json('modules.json')
        modules = data.get('modules', []) if data else []

        if course_id:
            modules = [m for m in modules if m.get('course_id') == course_id]
            modules.sort(key=lambda x: x.get('order', 0))

        return modules

    def get_module(self, module_id: str) -> Optional[Dict]:
        data = self._read_json('modules.json')
        if not data:
            return None

        for module in data.get('modules', []):
            if module.get('id') == module_id:
                return module
        return None

    def create_module(self, module_data: Dict) -> Dict:
        data = self._read_json('modules.json') or {'modules': [], 'last_id': 0}

        module_id = f"MOD-{str(self._get_next_id(data)).zfill(6)}"
        data['last_id'] = self._get_next_id(data)

        module_data['id'] = module_id
        module_data['created_at'] = DateUtils.now()

        data['modules'].append(module_data)
        self._write_json('modules.json', data)

        return module_data

    def update_module(self, module_id: str, update_data: Dict) -> bool:
        data = self._read_json('modules.json')
        if not data:
            return False

        for i, module in enumerate(data['modules']):
            if module.get('id') == module_id:
                for key, value in update_data.items():
                    if key not in ['id', 'created_at']:
                        module[key] = value
                data['modules'][i] = module
                self._write_json('modules.json', data)
                return True

        return False

    def delete_module(self, module_id: str) -> bool:
        data = self._read_json('modules.json')
        if not data:
            return False

        data['modules'] = [m for m in data['modules'] if m.get('id') != module_id]
        self._write_json('modules.json', data)

        self.delete_module_lessons(module_id)

        return True

    def delete_course_modules(self, course_id: str):
        data = self._read_json('modules.json')
        if not data:
            return

        modules_to_delete = [m for m in data['modules'] if m.get('course_id') == course_id]
        for module in modules_to_delete:
            self.delete_module(module['id'])

    def get_lessons(self, module_id: str = None) -> List[Dict]:
        data = self._read_json('lessons.json')
        lessons = data.get('lessons', []) if data else []

        if module_id:
            lessons = [l for l in lessons if l.get('module_id') == module_id]
            lessons.sort(key=lambda x: x.get('order', 0))

        return lessons

    def get_lesson(self, lesson_id: str) -> Optional[Dict]:
        data = self._read_json('lessons.json')
        if not data:
            return None

        for lesson in data.get('lessons', []):
            if lesson.get('id') == lesson_id:
                return lesson
        return None

    def get_lesson_by_video(self, video_filename: str) -> Optional[Dict]:
        data = self._read_json('lessons.json')
        if not data:
            return None

        for lesson in data.get('lessons', []):
            video = lesson.get('video')
            if video and video.get('filename') == video_filename:
                return lesson
        return None

    def get_lesson_by_file(self, file_id: str) -> Optional[Dict]:
        data = self._read_json('lessons.json')
        if not data:
            return None

        for lesson in data.get('lessons', []):
            for file in lesson.get('files', []):
                if file.get('id') == file_id:
                    return lesson
        return None

    def create_lesson(self, lesson_data: Dict) -> Dict:
        data = self._read_json('lessons.json') or {'lessons': [], 'last_id': 0, 'last_file_id': 0}

        lesson_id = f"LSN-{str(self._get_next_id(data)).zfill(6)}"
        data['last_id'] = self._get_next_id(data)

        lesson_data['id'] = lesson_id
        lesson_data['created_at'] = DateUtils.now()
        lesson_data.setdefault('files', [])

        data['lessons'].append(lesson_data)
        self._write_json('lessons.json', data)

        return lesson_data

    def update_lesson(self, lesson_id: str, update_data: Dict) -> bool:
        data = self._read_json('lessons.json')
        if not data:
            return False

        for i, lesson in enumerate(data['lessons']):
            if lesson.get('id') == lesson_id:
                for key, value in update_data.items():
                    if key not in ['id', 'created_at']:
                        lesson[key] = value
                data['lessons'][i] = lesson
                self._write_json('lessons.json', data)
                return True

        return False

    def delete_lesson(self, lesson_id: str) -> bool:
        data = self._read_json('lessons.json')
        if not data:
            return False

        lesson = self.get_lesson(lesson_id)
        if lesson:
            video = lesson.get('video')
            if video:
                video_path = os.path.join('storage/videos', video['filename'])
                if os.path.exists(video_path):
                    try:
                        os.remove(video_path)
                    except:
                        pass

            for file in lesson.get('files', []):
                file_path = os.path.join('storage/documents', file['filename'])
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass

        data['lessons'] = [l for l in data['lessons'] if l.get('id') != lesson_id]
        self._write_json('lessons.json', data)

        return True

    def delete_module_lessons(self, module_id: str):
        data = self._read_json('lessons.json')
        if not data:
            return

        lessons_to_delete = [l for l in data['lessons'] if l.get('module_id') == module_id]
        for lesson in lessons_to_delete:
            self.delete_lesson(lesson['id'])

    def get_access(self, user_id: str = None, course_id: str = None) -> Union[List[Dict], Optional[Dict]]:
        data = self._read_json('access.json')
        accesses = data.get('access', []) if data else []

        if user_id and course_id:
            for access in accesses:
                if access.get('user_id') == user_id and access.get('course_id') == course_id:
                    return access
            return None
        elif user_id:
            return [a for a in accesses if a.get('user_id') == user_id]
        elif course_id:
            return [a for a in accesses if a.get('course_id') == course_id]

        return accesses

    def get_user_accesses(self, user_id: str) -> List[Dict]:
        return self.get_access(user_id=user_id) or []

    def create_access(self, access_data: Dict) -> Dict:
        data = self._read_json('access.json') or {'access': [], 'last_id': 0}

        access_id = f"ACS-{str(self._get_next_id(data)).zfill(6)}"
        data['last_id'] = self._get_next_id(data)

        access_data['id'] = access_id
        access_data['created_at'] = DateUtils.now()

        data['access'].append(access_data)
        self._write_json('access.json', data)

        return access_data

    def update_access(self, access_id: str, update_data: Dict) -> bool:
        data = self._read_json('access.json')
        if not data:
            return False

        for i, access in enumerate(data['access']):
            if access.get('id') == access_id:
                for key, value in update_data.items():
                    if key not in ['id', 'created_at']:
                        access[key] = value
                data['access'][i] = access
                self._write_json('access.json', data)
                return True

        return False

    def update_access_status(self, access_id: str, status: str) -> bool:
        return self.update_access(access_id, {'status': status})

    def delete_access(self, user_id: str, course_id: str) -> bool:
        data = self._read_json('access.json')
        if not data:
            return False

        data['access'] = [a for a in data['access'] if
                          not (a.get('user_id') == user_id and a.get('course_id') == course_id)]
        self._write_json('access.json', data)
        return True

    def delete_user_access(self, user_id: str):
        data = self._read_json('access.json')
        if not data:
            return

        data['access'] = [a for a in data['access'] if a.get('user_id') != user_id]
        self._write_json('access.json', data)

    def delete_course_access(self, course_id: str):
        data = self._read_json('access.json')
        if not data:
            return

        data['access'] = [a for a in data['access'] if a.get('course_id') != course_id]
        self._write_json('access.json', data)

    def get_progress(self, user_id: str = None, lesson_id: str = None) -> Union[List[Dict], Optional[Dict]]:
        data = self._read_json('progress.json')
        progresses = data.get('progress', []) if data else []

        if user_id and lesson_id:
            for progress in progresses:
                if progress.get('user_id') == user_id and progress.get('lesson_id') == lesson_id:
                    return progress
            return None
        elif user_id:
            return [p for p in progresses if p.get('user_id') == user_id]
        elif lesson_id:
            return [p for p in progresses if p.get('lesson_id') == lesson_id]

        return progresses

    def get_user_progress(self, user_id: str) -> List[Dict]:
        return self.get_progress(user_id=user_id) or []

    def create_progress(self, progress_data: Dict) -> Dict:
        data = self._read_json('progress.json') or {'progress': [], 'last_id': 0}

        progress_id = f"PRG-{str(self._get_next_id(data)).zfill(6)}"
        data['last_id'] = self._get_next_id(data)

        progress_data['id'] = progress_id
        progress_data['updated_at'] = DateUtils.now()

        data['progress'].append(progress_data)
        self._write_json('progress.json', data)

        return progress_data

    def update_progress(self, user_id: str, lesson_id: str, update_data: Dict) -> bool:
        data = self._read_json('progress.json')
        if not data:
            return False

        for i, progress in enumerate(data['progress']):
            if progress.get('user_id') == user_id and progress.get('lesson_id') == lesson_id:
                for key, value in update_data.items():
                    if key not in ['id', 'user_id', 'lesson_id']:
                        progress[key] = value
                progress['updated_at'] = DateUtils.now()
                data['progress'][i] = progress
                self._write_json('progress.json', data)
                return True

        return False

    def delete_user_progress(self, user_id: str):
        data = self._read_json('progress.json')
        if not data:
            return

        data['progress'] = [p for p in data['progress'] if p.get('user_id') != user_id]
        self._write_json('progress.json', data)

    def add_file_to_lesson(self, lesson_id: str, file_data: Dict) -> Dict:
        data = self._read_json('lessons.json')
        if not data:
            return None

        for i, lesson in enumerate(data['lessons']):
            if lesson.get('id') == lesson_id:
                file_id = f"FIL-{str(data.get('last_file_id', 0) + 1).zfill(6)}"
                data['last_file_id'] = data.get('last_file_id', 0) + 1

                file_data['id'] = file_id
                file_data['uploaded_at'] = DateUtils.now()

                lesson.setdefault('files', [])
                lesson['files'].append(file_data)

                data['lessons'][i] = lesson
                self._write_json('lessons.json', data)
                return file_data

        return None

    def remove_file_from_lesson(self, lesson_id: str, file_id: str) -> bool:
        data = self._read_json('lessons.json')
        if not data:
            return False

        for i, lesson in enumerate(data['lessons']):
            if lesson.get('id') == lesson_id:
                lesson['files'] = [f for f in lesson.get('files', []) if f.get('id') != file_id]
                data['lessons'][i] = lesson
                self._write_json('lessons.json', data)
                return True

        return False

    def get_file(self, file_id: str) -> Optional[Dict]:
        data = self._read_json('lessons.json')
        if not data:
            return None

        for lesson in data.get('lessons', []):
            for file in lesson.get('files', []):
                if file.get('id') == file_id:
                    return file
        return None

    def get_settings(self) -> Dict:
        settings = self._read_json('settings.json')
        if not settings:
            settings = {
                'theme': 'dark',
                'language': 'uz',
                'max_video_size': 5368709120,
                'max_file_size': 104857600,
                'backup_interval': 3600,
                'maintenance_mode': False
            }
            self._write_json('settings.json', settings)
        return settings

    def update_settings(self, update_data: Dict) -> bool:
        settings = self.get_settings()
        for key, value in update_data.items():
            settings[key] = value
        self._write_json('settings.json', settings)
        return True


class StorageManager:
    def __init__(self, storage: JSONStorage):
        self.storage = storage

    def save_uploaded_file(self, file, subdir: str, allowed_extensions: List[str] = None) -> Dict:
        if not file:
            return None

        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()

        if allowed_extensions and ext not in allowed_extensions:
            raise ValueError(f"Fayl formati ruxsat etilmaydi: {ext}")

        unique_name = f"{Utils.generate_id('')[:8]}_{filename}"

        if subdir == 'videos':
            save_dir = get_config().VIDEO_DIR
        elif subdir == 'documents':
            save_dir = get_config().DOCUMENTS_DIR
        elif subdir == 'images':
            save_dir = get_config().IMAGES_DIR
        elif subdir == 'presentations':
            save_dir = get_config().PRESENTATIONS_DIR
        else:
            save_dir = get_config().OTHER_DIR

        os.makedirs(save_dir, exist_ok=True)

        file_path = os.path.join(save_dir, unique_name)
        file.save(file_path)

        return {
            'filename': unique_name,
            'original_name': filename,
            'size': os.path.getsize(file_path),
            'type': FileUtils.get_file_type(filename),
            'extension': ext
        }

    def delete_file(self, subdir: str, filename: str) -> bool:
        if subdir == 'videos':
            file_dir = get_config().VIDEO_DIR
        elif subdir == 'documents':
            file_dir = get_config().DOCUMENTS_DIR
        elif subdir == 'images':
            file_dir = get_config().IMAGES_DIR
        elif subdir == 'presentations':
            file_dir = get_config().PRESENTATIONS_DIR
        else:
            file_dir = get_config().OTHER_DIR

        file_path = os.path.join(file_dir, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except:
                return False
        return False

    def get_file_path(self, subdir: str, filename: str) -> str:
        if subdir == 'videos':
            return os.path.join(get_config().VIDEO_DIR, filename)
        elif subdir == 'documents':
            return os.path.join(get_config().DOCUMENTS_DIR, filename)
        elif subdir == 'images':
            return os.path.join(get_config().IMAGES_DIR, filename)
        elif subdir == 'presentations':
            return os.path.join(get_config().PRESENTATIONS_DIR, filename)
        else:
            return os.path.join(get_config().OTHER_DIR, filename)