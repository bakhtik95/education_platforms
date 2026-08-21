# services/file_service.py
import os
import uuid
import mimetypes
from typing import Optional, Dict, Any, List
from werkzeug.datastructures import FileStorage
from config import get_config
from core import JSONStorage, FileUtils, Utils
from core.utils import DateUtils


class FileService:
    def __init__(self, storage: Optional[JSONStorage] = None):
        if storage is None:
            self.storage = JSONStorage()
        else:
            self.storage = storage
        self.config = get_config()

    def save_video(self, lesson_id: str, file: FileStorage) -> Dict:
        """Сохранение видео для урока"""
        ext = FileUtils.get_file_extension(file.filename)
        if ext not in self.config.ALLOWED_VIDEO_EXTENSIONS:
            raise ValueError(f"Video format ruxsat etilmaydi: {ext}")

        file.seek(0, 2)
        size = file.tell()
        file.seek(0)

        if size > self.config.MAX_VIDEO_SIZE:
            raise ValueError(
                f"Video hajmi juda katta (maksimal: {FileUtils.get_file_size_str(self.config.MAX_VIDEO_SIZE)})")

        unique_name = f"{uuid.uuid4().hex[:8]}_{FileUtils.safe_filename(file.filename)}"

        video_path = os.path.join(self.config.VIDEO_DIR, unique_name)
        os.makedirs(self.config.VIDEO_DIR, exist_ok=True)
        file.save(video_path)

        duration = FileUtils.get_video_duration(video_path)

        video_data = {
            'filename': unique_name,
            'original_name': file.filename,
            'size': size,
            'duration': duration,
            'uploaded_at': DateUtils.now()
        }

        lesson = self.storage.get_lesson(lesson_id)
        if not lesson:
            raise ValueError("Lesson topilmadi")

        if lesson.get('video'):
            old_filename = lesson['video'].get('filename')
            if old_filename:
                old_path = os.path.join(self.config.VIDEO_DIR, old_filename)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except:
                        pass

        self.storage.update_lesson(lesson_id, {'video': video_data})

        return video_data

    def save_file(self, lesson_id: str, file: FileStorage) -> Dict:
        """Сохранение файла для урока"""
        ext = FileUtils.get_file_extension(file.filename)
        allowed_extensions = self.config.ALLOWED_DOCUMENT_EXTENSIONS | self.config.ALLOWED_IMAGE_EXTENSIONS

        if ext not in allowed_extensions:
            raise ValueError(f"Fayl formati ruxsat etilmaydi: {ext}")

        file.seek(0, 2)
        size = file.tell()
        file.seek(0)

        if size > self.config.MAX_FILE_SIZE:
            raise ValueError(
                f"Fayl hajmi juda katta (maksimal: {FileUtils.get_file_size_str(self.config.MAX_FILE_SIZE)})")

        file_type = FileUtils.get_file_type(file.filename)
        subdir = self._get_subdir(file_type)

        unique_name = f"{uuid.uuid4().hex[:8]}_{FileUtils.safe_filename(file.filename)}"

        file_path = os.path.join(subdir, unique_name)
        os.makedirs(subdir, exist_ok=True)
        file.save(file_path)

        file_data = {
            'filename': unique_name,
            'original_name': file.filename,
            'type': file_type,
            'size': size,
            'extension': ext
        }

        result = self.storage.add_file_to_lesson(lesson_id, file_data)
        if not result:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise ValueError("Faylni saqlashda xatolik yuz berdi")

        return result

    def _get_subdir(self, file_type: str) -> str:
        """Получение поддиректории для типа файла"""
        if file_type == 'video':
            return self.config.VIDEO_DIR
        elif file_type in ['document', 'spreadsheet']:
            return self.config.DOCUMENTS_DIR
        elif file_type == 'presentation':
            return self.config.PRESENTATIONS_DIR
        elif file_type == 'image':
            return self.config.IMAGES_DIR
        else:
            return self.config.OTHER_DIR

    def delete_video(self, lesson_id: str) -> bool:
        """Удаление видео из урока"""
        lesson = self.storage.get_lesson(lesson_id)
        if not lesson:
            return False

        video = lesson.get('video')
        if not video:
            return True

        filename = video.get('filename')
        if filename:
            file_path = os.path.join(self.config.VIDEO_DIR, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

        return self.storage.update_lesson(lesson_id, {'video': None})

    def delete_file(self, lesson_id: str, file_id: str) -> bool:
        """Удаление файла из урока"""
        lesson = self.storage.get_lesson(lesson_id)
        if not lesson:
            return False

        file_data = None
        for f in lesson.get('files', []):
            if f.get('id') == file_id:
                file_data = f
                break

        if not file_data:
            return True

        filename = file_data.get('filename')
        if filename:
            file_type = file_data.get('type', 'other')
            subdir = self._get_subdir(file_type)
            file_path = os.path.join(subdir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

        return self.storage.remove_file_from_lesson(lesson_id, file_id)

    def get_video_path(self, filename: str) -> Optional[str]:
        """Получение пути к видео"""
        path = os.path.join(self.config.VIDEO_DIR, filename)
        if os.path.exists(path):
            return path
        return None

    def get_file_path(self, filename: str, file_type: str = 'document') -> Optional[str]:
        """Получение пути к файлу"""
        subdir = self._get_subdir(file_type)
        path = os.path.join(subdir, filename)
        if os.path.exists(path):
            return path
        return None

    def get_file_by_id(self, file_id: str) -> Optional[Dict]:
        """Получение информации о файле по ID"""
        return self.storage.get_file(file_id)

    def get_lesson_file_data(self, file_id: str) -> Optional[Dict]:
        """Получение данных файла из урока"""
        data = self.storage.get_file(file_id)
        if data:
            lesson = self.storage.get_lesson_by_file(file_id)
            if lesson:
                data['lesson_id'] = lesson['id']
                data['course_id'] = lesson.get('course_id')

        return data

    def get_stats(self) -> Dict:
        """Получение статистики по файлам"""
        lessons = self.storage.get_lessons()
        videos_count = 0
        files_count = 0
        total_video_size = 0
        total_file_size = 0

        for lesson in lessons:
            if lesson.get('video'):
                videos_count += 1
                total_video_size += lesson['video'].get('size', 0)

            files_count += len(lesson.get('files', []))
            for file in lesson.get('files', []):
                total_file_size += file.get('size', 0)

        return {
            'videos_count': videos_count,
            'files_count': files_count,
            'total_video_size': total_video_size,
            'total_video_size_human': FileUtils.get_file_size_str(total_video_size),
            'total_file_size': total_file_size,
            'total_file_size_human': FileUtils.get_file_size_str(total_file_size)
        }

    # ========== МЕТОДЫ ДЛЯ ОПРЕДЕЛЕНИЯ ТИПА ФАЙЛА ==========

    def get_mime_type(self, filename: str) -> str:
        """
        Получение MIME типа файла для правильного отображения в браузере
        """
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            # Определяем по расширению вручную
            ext = os.path.splitext(filename)[1].lower()
            mime_types = {
                '.pdf': 'application/pdf',
                '.doc': 'application/msword',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.ppt': 'application/vnd.ms-powerpoint',
                '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                '.xls': 'application/vnd.ms-excel',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.webp': 'image/webp',
                '.bmp': 'image/bmp',
                '.ico': 'image/x-icon',
                '.mp4': 'video/mp4',
                '.webm': 'video/webm',
                '.mov': 'video/quicktime',
                '.avi': 'video/x-msvideo',
                '.mkv': 'video/x-matroska',
                '.flv': 'video/x-flv',
                '.wmv': 'video/x-ms-wmv',
                '.zip': 'application/zip',
                '.rar': 'application/vnd.rar',
                '.7z': 'application/x-7z-compressed',
                '.txt': 'text/plain',
                '.html': 'text/html',
                '.htm': 'text/html',
                '.css': 'text/css',
                '.js': 'application/javascript',
                '.json': 'application/json',
                '.xml': 'application/xml',
                '.csv': 'text/csv'
            }
            return mime_types.get(ext, 'application/octet-stream')
        return mime_type

    def is_inline_viewable(self, filename: str) -> bool:
        """
        Проверка можно ли просмотреть файл непосредственно в браузере (inline)
        Без автоматической загрузки
        """
        ext = os.path.splitext(filename)[1].lower()
        inline_extensions = {
            '.pdf',
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp', '.ico',
            '.mp4', '.webm', '.mov', '.avi',
            '.txt', '.html', '.htm', '.css', '.js', '.xml', '.json', '.csv'
        }
        return ext in inline_extensions

    def get_file_icon_html(self, filename: str) -> str:
        """
        Получение HTML иконки для файла по его расширению
        """
        ext = os.path.splitext(filename)[1].lower()
        icons = {
            '.pdf': '📄',
            '.doc': '📝',
            '.docx': '📝',
            '.ppt': '📊',
            '.pptx': '📊',
            '.xls': '📈',
            '.xlsx': '📈',
            '.jpg': '🖼️',
            '.jpeg': '🖼️',
            '.png': '🖼️',
            '.gif': '🖼️',
            '.svg': '🖼️',
            '.webp': '🖼️',
            '.mp4': '🎬',
            '.webm': '🎬',
            '.mov': '🎬',
            '.avi': '🎬',
            '.zip': '📦',
            '.rar': '📦',
            '.7z': '📦',
            '.txt': '📃',
            '.html': '🌐',
            '.htm': '🌐',
            '.css': '🎨',
            '.js': '⚙️',
            '.json': '📊',
            '.xml': '📋',
            '.csv': '📊'
        }
        return icons.get(ext, '📎')

    def get_file_category(self, filename: str) -> str:
        """
        Получение категории файла для группировки
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext in {'.pdf'}:
            return 'document'
        elif ext in {'.doc', '.docx'}:
            return 'word'
        elif ext in {'.ppt', '.pptx'}:
            return 'presentation'
        elif ext in {'.xls', '.xlsx'}:
            return 'spreadsheet'
        elif ext in {'.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp', '.ico'}:
            return 'image'
        elif ext in {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv'}:
            return 'video'
        elif ext in {'.zip', '.rar', '.7z'}:
            return 'archive'
        elif ext in {'.txt', '.html', '.htm', '.css', '.js', '.json', '.xml', '.csv'}:
            return 'text'
        else:
            return 'other'

    def get_file_preview_html(self, file_id: str, filename: str) -> str:
        """
        Получение HTML кода для предварительного просмотра файла
        """
        ext = os.path.splitext(filename)[1].lower()

        if ext == '.pdf':
            return f'''
                <div class="preview-content pdf-container">
                    <iframe src="/media/file/{file_id}#toolbar=0&navpanes=0&scrollbar=0" 
                            onload="this.style.height='600px';"></iframe>
                </div>
            '''
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp']:
            return f'''
                <div class="preview-content">
                    <img src="/media/file/{file_id}" alt="{filename}">
                </div>
            '''
        elif ext in ['.mp4', '.webm', '.mov', '.avi']:
            return f'''
                <div class="preview-content">
                    <div class="video-preview">
                        <video controls style="width:100%; max-height:500px;">
                            <source src="/media/file/{file_id}" type="video/{ext[1:]}">
                            <p>Brauzeringiz video player-ni qo'llab-quvvatlamaydi</p>
                        </video>
                    </div>
                </div>
            '''
        elif ext in ['.doc', '.docx']:
            return f'''
                <div class="preview-content">
                    <div class="doc-viewer">
                        <i class="fas fa-file-word"></i>
                        <h4>Microsoft Word hujjati</h4>
                        <p>Hujjatni ko'rish uchun yuklab oling</p>
                        <a href="/media/file/{file_id}" class="btn-download" download>
                            <i class="fas fa-download"></i> Yuklab olish
                        </a>
                    </div>
                </div>
            '''
        elif ext in ['.ppt', '.pptx']:
            return f'''
                <div class="preview-content">
                    <div class="doc-viewer">
                        <i class="fas fa-file-powerpoint" style="color: #D24726;"></i>
                        <h4>PowerPoint taqdimoti</h4>
                        <p>Taqdimotni ko'rish uchun yuklab oling</p>
                        <a href="/media/file/{file_id}" class="btn-download" style="background: #D24726;" download>
                            <i class="fas fa-download"></i> Yuklab olish
                        </a>
                    </div>
                </div>
            '''
        elif ext in ['.xls', '.xlsx']:
            return f'''
                <div class="preview-content">
                    <div class="doc-viewer">
                        <i class="fas fa-file-excel" style="color: #217346;"></i>
                        <h4>Excel jadvali</h4>
                        <p>Jadvalni ko'rish uchun yuklab oling</p>
                        <a href="/media/file/{file_id}" class="btn-download" style="background: #217346;" download>
                            <i class="fas fa-download"></i> Yuklab olish
                        </a>
                    </div>
                </div>
            '''
        else:
            return f'''
                <div class="preview-content">
                    <div class="doc-viewer">
                        <i class="fas fa-file" style="color: var(--text-muted);"></i>
                        <h4>Fayl</h4>
                        <p>Faylni ko'rish uchun yuklab oling</p>
                        <a href="/media/file/{file_id}" class="btn-download" style="background: #666;" download>
                            <i class="fas fa-download"></i> Yuklab olish
                        </a>
                    </div>
                </div>
            '''