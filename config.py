# config.py
import os
from datetime import timedelta


class Config:
    # Базовые настройки
    SECRET_KEY = 'dev-secret-key-change-in-production-2026'
    DEBUG = True
    TESTING = False

    # Настройки сессий
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Пути к директориям
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
    BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')

    # Поддиректории storage
    VIDEO_DIR = os.path.join(STORAGE_DIR, 'videos')
    DOCUMENTS_DIR = os.path.join(STORAGE_DIR, 'documents')
    IMAGES_DIR = os.path.join(STORAGE_DIR, 'images')
    PRESENTATIONS_DIR = os.path.join(STORAGE_DIR, 'presentations')
    OTHER_DIR = os.path.join(STORAGE_DIR, 'other')
    RECEIPTS_DIR = os.path.join(STORAGE_DIR, 'receipts')

    # Ограничения на файлы
    MAX_VIDEO_SIZE = 5 * 1024 * 1024 * 1024  # 5 GB
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

    # Разрешенные расширения
    ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg'}
    ALLOWED_DOCUMENT_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',
        '.ppt', '.pptx', '.zip', '.txt'
    }
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.svg'}

    # Настройки бэкапов
    BACKUP_INTERVAL = 3600
    MAX_BACKUPS = 50

    # Настройки логов
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    # Настройки для видео
    VIDEO_CHUNK_SIZE = 1024 * 1024

    # Настройки пагинации
    ITEMS_PER_PAGE = 20

    # Настройки администратора по умолчанию
    DEFAULT_ADMIN = {
        'login': 'admin',
        'password': 'admin123',
        'full_name': 'Administrator',
        'email': 'admin@example.com',
        'phone': '+998901234567'
    }


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = 'dev-secret-key-2026'


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'production-secret-key-change-this')
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DATA_DIR = os.path.join(Config.BASE_DIR, 'test_data')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, DevelopmentConfig)()