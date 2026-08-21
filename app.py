# app.py
import os
import sys
import json
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, session, request, g
from werkzeug.middleware.proxy_fix import ProxyFix

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_config
from core import JSONStorage, AuthManager
from core.utils import FileUtils, DateUtils

# Инициализация приложения
config = get_config()
app = Flask(__name__)
app.config.from_object(config)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Инициализация хранилища
storage = JSONStorage(config.DATA_DIR)


# ========== Создание необходимых директорий ==========
def create_directories():
    """Создание всех необходимых директорий"""
    dirs = [
        config.DATA_DIR,
        config.STORAGE_DIR,
        config.VIDEO_DIR,
        os.path.join(config.VIDEO_DIR, 'courses'),
        config.DOCUMENTS_DIR,
        config.IMAGES_DIR,
        os.path.join(config.IMAGES_DIR, 'courses'),
        config.PRESENTATIONS_DIR,
        config.OTHER_DIR,
        config.RECEIPTS_DIR,
        config.BACKUP_DIR,
        config.LOGS_DIR,
        os.path.join(config.BASE_DIR, 'static', 'images', 'courses')
    ]

    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)


# ========== Инициализация данных ==========
def initialize_data():
    """Инициализация начальных данных"""
    # Создаем пользователей
    users = storage.get_users()
    if not users:
        # Создаем администратора
        from services import UserService
        from models import UserRoles, UserStatus, AccessType

        user_service = UserService(storage)

        admin_data = {
            'full_name': config.DEFAULT_ADMIN['full_name'],
            'login': config.DEFAULT_ADMIN['login'],
            'email': config.DEFAULT_ADMIN['email'],
            'phone': config.DEFAULT_ADMIN['phone'],
            'password': config.DEFAULT_ADMIN['password'],
            'role': UserRoles.ADMIN,
            'status': UserStatus.ACTIVE,
            'access_type': AccessType.FREE
        }

        try:
            user = user_service.create_user(admin_data)
            logging.info(f"Admin user created: {user['login']}")
        except Exception as e:
            logging.error(f"Failed to create admin: {e}")

    # Создаем настройки
    settings = storage.get_settings()
    if not settings:
        storage.update_settings({
            'theme': 'dark',
            'language': 'uz',
            'max_video_size': config.MAX_VIDEO_SIZE,
            'max_file_size': config.MAX_FILE_SIZE,
            'backup_interval': config.BACKUP_INTERVAL,
            'maintenance_mode': False,
            'initialized_at': DateUtils.now()
        })

    # Создаем пустые файлы если их нет
    json_files = ['courses.json', 'modules.json', 'lessons.json', 'access.json', 'progress.json']
    for filename in json_files:
        filepath = os.path.join(config.DATA_DIR, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)


# ========== Настройка логирования ==========
def setup_logging():
    """Настройка логирования"""
    log_file = os.path.join(config.LOGS_DIR, 'system.log')

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    # Логируем запуск
    logging.info("=" * 60)
    logging.info(f"Application started at {DateUtils.now()}")
    logging.info(f"Data directory: {config.DATA_DIR}")
    logging.info(f"Storage directory: {config.STORAGE_DIR}")
    logging.info("=" * 60)


# ========== Регистрация маршрутов ==========
def register_blueprints():
    """Регистрация всех маршрутов"""
    from routes import auth_bp, user_bp, course_bp, admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(admin_bp)

    logging.info("All blueprints registered")


# ========== Контекстные процессоры ==========
@app.context_processor
def inject_user():
    """Добавление пользователя в контекст шаблонов"""
    user = None
    if 'user_id' in session:
        user = storage.get_user(session['user_id'])
    return {'user': user}


# ========== Фильтры Jinja2 ==========
@app.template_filter('filesize')
def filesize_filter(size):
    """Фильтр для отображения размера файла"""
    return FileUtils.get_file_size_str(size)


@app.template_filter('datetime')
def datetime_filter(date_str):
    """Фильтр для форматирования даты"""
    if not date_str:
        return ''
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%d.%m.%Y %H:%M')
    except:
        return date_str


@app.template_filter('date')
def date_filter(date_str):
    """Фильтр для форматирования даты"""
    if not date_str:
        return ''
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%d.%m.%Y')
    except:
        return date_str


@app.template_filter('user_role_display')
def user_role_display_filter(user):
    """Фильтр для отображения роли пользователя"""
    if not user:
        return 'Foydalanuvchi'
    role_map = {
        'admin': 'Administrator',
        'user': 'Foydalanuvchi'
    }
    return role_map.get(user.get('role'), 'Foydalanuvchi')


@app.template_filter('user_status_display')
def user_status_display_filter(user):
    """Фильтр для отображения статуса пользователя"""
    if not user:
        return 'Noma\'lum'
    status_map = {
        'active': 'Faol',
        'inactive': 'Faol emas',
        'blocked': 'Bloklangan',
        'pending': 'Kutilmoqda',
        'pending_payment': 'To\'lov kutilmoqda',
        'payment_confirmed': 'To\'lov tasdiqlangan',
        'payment_rejected': 'To\'lov rad etilgan'
    }
    return status_map.get(user.get('status'), user.get('status', 'Noma\'lum'))


@app.template_filter('user_access_type_display')
def user_access_type_display_filter(user):
    """Фильтр для отображения типа доступа пользователя"""
    if not user:
        return 'Noma\'lum'
    type_map = {
        'free': 'Bepul',
        'paid': 'Pullik'
    }
    return type_map.get(user.get('access_type'), user.get('access_type', 'Noma\'lum'))


@app.template_filter('course_status_display')
def course_status_display_filter(course):
    """Фильтр для отображения статуса курса"""
    if not course:
        return 'Noma\'lum'
    status_map = {
        'active': 'Faol',
        'inactive': 'Faol emas',
        'draft': 'Qoralama',
        'archived': 'Arxivlangan'
    }
    return status_map.get(course.get('status'), course.get('status', 'Noma\'lum'))


@app.template_filter('course_type_display')
def course_type_display_filter(course):
    """Фильтр для отображения типа курса"""
    if not course:
        return 'Noma\'lum'
    type_map = {
        'asosiy': 'Asosiy kurs',
        'ilg\'or': 'Ilg\'or kurs',
        'maxsus': 'Maxsus kurs'
    }
    return type_map.get(course.get('type'), course.get('type', 'Noma\'lum'))


@app.template_filter('get_admin_name')
def get_admin_name_filter(user_id):
    """Фильтр для получения имени администратора по ID"""
    if not user_id:
        return '-'
    user = storage.get_user(user_id)
    if user:
        return user.get('full_name', user.get('login', user_id))
    return user_id


@app.template_filter('escapejs')
def escapejs_filter(value):
    """Экранирование строки для использования в JavaScript"""
    if not value:
        return ''
    # Заменяем специальные символы
    value = value.replace('\\', '\\\\')
    value = value.replace("'", "\\'")
    value = value.replace('"', '\\"')
    value = value.replace('\n', '\\n')
    value = value.replace('\r', '\\r')
    value = value.replace('\t', '\\t')
    return value


# ========== Обработка ошибок ==========
@app.errorhandler(400)
def bad_request(e):
    return render_template('error.html',
                           code=400,
                           message="Noto'g'ri so'rov"), 400


@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html',
                           code=403,
                           message="Kirish taqiqlangan. Sizda ushbu sahifaga kirish huquqi mavjud emas."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html',
                           code=404,
                           message="Sahifa topilmadi"), 404


@app.errorhandler(413)
def too_large(e):
    return render_template('error.html',
                           code=413,
                           message="Fayl hajmi juda katta"), 413


@app.errorhandler(500)
def internal_error(e):
    logging.error(f"Internal error: {e}")
    return render_template('error.html',
                           code=500,
                           message="Serverda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."), 500


# ========== Запросы до и после ==========
@app.before_request
def before_request():
    """Действия перед каждым запросом"""
    # Проверка сессии
    if 'user_id' in session:
        user = storage.get_user(session['user_id'])
        if not user:
            session.clear()

    # Логирование запросов
    if request.method in ['POST', 'PUT', 'DELETE']:
        logging.info(f"{request.method} {request.path} - User: {session.get('user_id', 'anonymous')}")


@app.after_request
def after_request(response):
    """Действия после каждого запроса"""
    # Добавляем заголовки безопасности
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


# ========== Главная страница ==========
@app.route('/')
def index():
    """Перенаправление на страницу входа или курсы"""
    if 'user_id' in session:
        user = storage.get_user(session['user_id'])
        if user:
            if user.get('role') == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('user.courses'))
    return redirect(url_for('auth.login'))


# ========== Команды CLI ==========
@app.cli.command('create-admin')
def create_admin_command():
    """Создание администратора через CLI"""
    from services import UserService
    from models import UserRoles, UserStatus, AccessType

    login = input("Login: ")
    password = input("Password: ")
    full_name = input("Full name: ")
    email = input("Email: ")
    phone = input("Phone: ")

    user_service = UserService(storage)

    user_data = {
        'full_name': full_name,
        'login': login,
        'email': email,
        'phone': phone,
        'password': password,
        'role': UserRoles.ADMIN,
        'status': UserStatus.ACTIVE,
        'access_type': AccessType.FREE
    }

    try:
        user = user_service.create_user(user_data)
        print(f"✅ Admin created: {user['login']}")
    except Exception as e:
        print(f"❌ Failed to create admin: {e}")


@app.cli.command('backup')
def backup_command():
    """Создание бэкапа через CLI"""
    from services import BackupService

    backup_service = BackupService(storage)
    timestamp = backup_service.create_backup()
    print(f"✅ Backup created: {timestamp}")


@app.cli.command('cleanup')
def cleanup_command():
    """Очистка просроченных доступов"""
    from services import AccessService

    access_service = AccessService(storage)
    count = access_service.cleanup_expired_accesses()
    print(f"✅ Cleaned up {count} expired accesses")


# ========== Инициализация ==========
def init_app():
    """Инициализация приложения"""
    create_directories()
    setup_logging()
    initialize_data()
    register_blueprints()

    logging.info("Application initialization complete")
    logging.info(f"Server will run at http://127.0.0.1:5000")


# ========== Функция получения локального IP ==========
def get_local_ip():
    """Получение локального IP адреса"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


# ========== Запуск ==========
if __name__ == '__main__':
    init_app()

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'

    print("=" * 60)
    print("🚀 Сервер запущен!")
    print("=" * 60)
    print(f"📱 Локальный доступ: http://127.0.0.1:{port}")
    print(f"🌐 Локальная сеть (LAN): http://{get_local_ip()}:{port}")
    print(f"🔑 Админ панель: http://127.0.0.1:{port}/admin")
    print("=" * 60)
    print("⚠️ Для доступа с других устройств используйте LAN IP")
    print("⚠️ Убедитесь, что брандмауэр разрешает порт", port)
    print("=" * 60)

    app.run(host=host, port=port, debug=debug)