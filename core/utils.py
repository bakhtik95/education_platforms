# core/utils.py
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List


class Utils:
    @staticmethod
    def generate_id(prefix: str) -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_part = uuid.uuid4().hex[:6].upper()
        return f"{prefix}-{timestamp}-{random_part}"

    @staticmethod
    def sanitize_string(text: str) -> str:
        if not text:
            return ''
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('"', '&quot;').replace("'", '&#39;')
        return text.strip()

    @staticmethod
    def format_datetime(dt: datetime) -> str:
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def parse_datetime(dt_str: str) -> Optional[datetime]:
        try:
            return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        except:
            return None

    @staticmethod
    def format_date(dt: datetime) -> str:
        return dt.strftime('%Y-%m-%d')


class FileUtils:
    @staticmethod
    def get_file_size_str(size_bytes: int) -> str:
        if not size_bytes:
            return '0 B'
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    @staticmethod
    def get_file_extension(filename: str) -> str:
        return os.path.splitext(filename)[1].lower()

    @staticmethod
    def get_file_type(filename: str) -> str:
        ext = FileUtils.get_file_extension(filename)
        if ext in {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v'}:
            return 'video'
        elif ext in {'.pdf', '.doc', '.docx'}:
            return 'document'
        elif ext in {'.xls', '.xlsx'}:
            return 'spreadsheet'
        elif ext in {'.ppt', '.pptx'}:
            return 'presentation'
        elif ext in {'.jpg', '.jpeg', '.png', '.gif', '.svg'}:
            return 'image'
        elif ext in {'.zip', '.rar', '.7z'}:
            return 'archive'
        else:
            return 'other'

    @staticmethod
    def get_file_icon(filename: str) -> str:
        ext = FileUtils.get_file_extension(filename)
        icons = {
            '.pdf': '📄',
            '.doc': '📝',
            '.docx': '📝',
            '.xls': '📊',
            '.xlsx': '📊',
            '.ppt': '📊',
            '.pptx': '📊',
            '.zip': '📦',
            '.jpg': '🖼️',
            '.jpeg': '🖼️',
            '.png': '🖼️',
            '.gif': '🖼️',
            '.svg': '🖼️',
            '.txt': '📃',
            '.mp4': '🎬',
            '.webm': '🎬',
            '.mov': '🎬',
            '.avi': '🎬'
        }
        return icons.get(ext, '📎')

    @staticmethod
    def get_video_duration(filepath: str) -> int:
        try:
            import subprocess
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                filepath
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                return int(float(result.stdout.strip()))
        except:
            pass
        return 0

    @staticmethod
    def ensure_directory(path: str) -> bool:
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except:
            return False

    @staticmethod
    def safe_filename(filename: str) -> str:
        filename = re.sub(r'[^a-zA-Zа-яА-Я0-9_.-]', '_', filename)
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:245] + ext
        return filename


class DateUtils:
    @staticmethod
    def now() -> str:
        return Utils.format_datetime(datetime.now())

    @staticmethod
    def today() -> str:
        return datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return None

    @staticmethod
    def days_diff(date1: str, date2: str) -> int:
        d1 = DateUtils.parse_date(date1)
        d2 = DateUtils.parse_date(date2)
        if d1 and d2:
            return abs((d2 - d1).days)
        return 0

    @staticmethod
    def is_expired(end_date: str) -> bool:
        if not end_date:
            return False
        end = DateUtils.parse_date(end_date)
        if end:
            return end.date() < datetime.now().date()
        return False

    @staticmethod
    def format_date_uz(date_str: str) -> str:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            months = ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
                      'Iyul', 'Avgust', 'Sentyabr', 'Oktyabr', 'Noyabr', 'Dekabr']
            return f"{dt.day} {months[dt.month - 1]} {dt.year}"
        except:
            return date_str

        # core/utils.py - ДОБАВИТЬ В КОНЕЦ ФАЙЛА

class DateUtils:
            @staticmethod
            def now() -> str:
                """Текущая дата и время в строковом формате"""
                return Utils.format_datetime(datetime.now())

            @staticmethod
            def today() -> str:
                """Текущая дата в строковом формате"""
                return datetime.now().strftime('%Y-%m-%d')

            @staticmethod
            def parse_date(date_str: str) -> Optional[datetime]:
                """Парсинг даты"""
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    return None

            @staticmethod
            def days_diff(date1: str, date2: str) -> int:
                """Разница в днях между датами"""
                d1 = DateUtils.parse_date(date1)
                d2 = DateUtils.parse_date(date2)
                if d1 and d2:
                    return abs((d2 - d1).days)
                return 0

            @staticmethod
            def is_expired(end_date: str) -> bool:
                """Проверка истекла ли дата"""
                if not end_date:
                    return False
                end = DateUtils.parse_date(end_date)
                if end:
                    return end.date() < datetime.now().date()
                return False

            @staticmethod
            def format_date_uz(date_str: str) -> str:
                """Форматирование даты на узбекском"""
                try:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                    months = ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
                              'Iyul', 'Avgust', 'Sentyabr', 'Oktyabr', 'Noyabr', 'Dekabr']
                    return f"{dt.day} {months[dt.month - 1]} {dt.year}"
                except:
                    return date_str

            @staticmethod
            def get_time_ago(date_str: str) -> str:
                """Получение времени прошедшего с даты"""
                try:
                    dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    now = datetime.now()
                    diff = now - dt

                    if diff.days > 30:
                        return DateUtils.format_date_uz(date_str)
                    elif diff.days > 0:
                        return f"{diff.days} kun oldin"
                    elif diff.seconds > 3600:
                        return f"{diff.seconds // 3600} soat oldin"
                    elif diff.seconds > 60:
                        return f"{diff.seconds // 60} daqiqa oldin"
                    else:
                        return "hozir"
                except:
                    return date_str