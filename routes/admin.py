# routes/admin.py
import os
import json
import secrets
import string
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.utils import secure_filename
from core import AuthManager, admin_required, login_required
from services import UserService, CourseService, AccessService, ProgressService, FileService, BackupService
from core.storage import JSONStorage
from core.utils import FileUtils, DateUtils
from core.security import PasswordManager
from config import get_config
from models import UserStatus, AccessType, CourseStatus, CourseType, LessonType

# Создание Blueprint
admin_bp = Blueprint('admin', __name__)

storage = JSONStorage()
auth_manager = AuthManager(storage)
user_service = UserService(storage)
course_service = CourseService(storage)
access_service = AccessService(storage)
progress_service = ProgressService(storage)
file_service = FileService(storage)
backup_service = BackupService(storage)
config = get_config()


# ========== Контекстный процессор для шаблонов ==========

@admin_bp.context_processor
def admin_context_processor():
    """Добавляет storage в контекст шаблонов"""
    return {'storage': storage}


# ========== Dashboard ==========

@admin_bp.route('/admin')
@login_required
@admin_required
def dashboard():
    """Панель администратора"""
    user_stats = user_service.get_stats()
    course_stats = course_service.get_course_stats()
    access_stats = access_service.get_stats()
    file_stats = file_service.get_stats()
    backup_stats = backup_service.get_stats()

    recent_users = user_service.get_recent_users(5)
    active_courses = course_service.get_active_courses()

    return render_template('admin/dashboard.html',
                           user_stats=user_stats,
                           course_stats=course_stats,
                           access_stats=access_stats,
                           file_stats=file_stats,
                           backup_stats=backup_stats,
                           recent_users=recent_users,
                           active_courses=active_courses)


# ========== Управление пользователями ==========

@admin_bp.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Список пользователей"""
    query = request.args.get('search', '').strip()

    if query:
        users = user_service.search_users(query)
    else:
        users = user_service.get_all_users()

    for user in users:
        accesses = storage.get_user_accesses(user['id'])
        user['courses_count'] = len(accesses)
        user['access_details'] = accesses

    return render_template('admin/users.html', users=users, query=query)


@admin_bp.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_user_create():
    """Создание пользователя"""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        login = request.form.get('login', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user')
        access_type = request.form.get('access_type', 'free')
        status = request.form.get('status', 'active')

        user_data = {
            'full_name': full_name,
            'login': login,
            'email': email if email else None,
            'phone': phone if phone else None,
            'password': password,
            'role': role,
            'access_type': access_type,
            'status': status
        }

        try:
            user = user_service.create_user(user_data)
            flash('Foydalanuvchi muvaffaqiyatli yaratildi', 'success')
            return redirect(url_for('admin.admin_users'))
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('admin/user_edit.html',
                                   user=user_data,
                                   is_new=True,
                                   roles=['admin', 'user'],
                                   access_types=['free', 'paid'],
                                   statuses=UserStatus.get_all())

    return render_template('admin/user_edit.html',
                           user=None,
                           is_new=True,
                           roles=['admin', 'user'],
                           access_types=['free', 'paid'],
                           statuses=UserStatus.get_all())


@admin_bp.route('/admin/users/<user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_user_edit(user_id):
    """Редактирование пользователя"""
    user = user_service.get_user(user_id)
    if not user:
        flash('Foydalanuvchi topilmadi', 'error')
        return redirect(url_for('admin.admin_users'))

    if request.method == 'POST':
        update_data = {}

        full_name = request.form.get('full_name', '').strip()
        if full_name:
            update_data['full_name'] = full_name

        email = request.form.get('email', '').strip()
        if email:
            update_data['email'] = email

        phone = request.form.get('phone', '').strip()
        if phone:
            update_data['phone'] = phone

        role = request.form.get('role')
        if role:
            update_data['role'] = role

        access_type = request.form.get('access_type')
        if access_type:
            update_data['access_type'] = access_type

        status = request.form.get('status')
        if status:
            update_data['status'] = status

        new_password = request.form.get('new_password', '')
        if new_password:
            update_data['password'] = new_password

        try:
            user_service.update_user(user_id, update_data)
            flash('Foydalanuvchi muvaffaqiyatli yangilandi', 'success')
            return redirect(url_for('admin.admin_users'))
        except ValueError as e:
            flash(str(e), 'error')

    accesses = storage.get_user_accesses(user_id)
    courses = course_service.get_all_courses()

    for access in accesses:
        course = course_service.get_course(access['course_id'])
        if course:
            access['course_title'] = course['title']

    return render_template('admin/user_edit.html',
                           user=user,
                           is_new=False,
                           accesses=accesses,
                           courses=courses,
                           roles=['admin', 'user'],
                           access_types=['free', 'paid'],
                           statuses=UserStatus.get_all())


@admin_bp.route('/admin/users/<user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_user_delete(user_id):
    """Удаление пользователя"""
    if user_id == session.get('user_id'):
        flash('O\'zingizni o\'chira olmaysiz', 'error')
        return redirect(url_for('admin.admin_users'))

    if user_service.delete_user(user_id):
        flash('Foydalanuvchi o\'chirildi', 'success')
    else:
        flash('Foydalanuvchini o\'chirishda xatolik', 'error')

    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/admin/users/<user_id>/block', methods=['POST'])
@login_required
@admin_required
def admin_user_block(user_id):
    """Блокировка пользователя"""
    if user_id == session.get('user_id'):
        flash('O\'zingizni bloklay olmaysiz', 'error')
        return redirect(url_for('admin.admin_users'))

    if user_service.block_user(user_id):
        flash('Foydalanuvchi bloklandi', 'success')
    else:
        flash('Xatolik yuz berdi', 'error')

    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/admin/users/<user_id>/unblock', methods=['POST'])
@login_required
@admin_required
def admin_user_unblock(user_id):
    """Разблокировка пользователя"""
    if user_service.unblock_user(user_id):
        flash('Foydalanuvchi blokdan chiqarildi', 'success')
    else:
        flash('Xatolik yuz berdi', 'error')

    return redirect(url_for('admin.admin_users'))


# ========== Управление доступом ==========

@admin_bp.route('/admin/users/<user_id>/access', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_user_access(user_id):
    """Управление доступом пользователя"""
    user = user_service.get_user(user_id)
    if not user:
        flash('Foydalanuvchi topilmadi', 'error')
        return redirect(url_for('admin.admin_users'))

    if request.method == 'POST':
        course_ids = request.form.getlist('courses[]')
        access_type = request.form.get('access_type', 'free')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        current_accesses = storage.get_user_accesses(user_id)
        current_course_ids = [a['course_id'] for a in current_accesses]

        for access in current_accesses:
            if access['course_id'] not in course_ids:
                storage.delete_access(user_id, access['course_id'])

        for course_id in course_ids:
            access_service.grant_access(user_id, course_id, access_type, start_date, end_date)

        flash('Foydalanuvchi kirish huquqi yangilandi', 'success')
        return redirect(url_for('admin.admin_users'))

    accesses = storage.get_user_accesses(user_id)
    user_course_ids = [a['course_id'] for a in accesses]
    all_courses = course_service.get_all_courses()

    return render_template('admin/user_access.html',
                           user=user,
                           all_courses=all_courses,
                           user_course_ids=user_course_ids,
                           accesses=accesses)


# ========== Управление курсами ==========

@admin_bp.route('/admin/courses')
@login_required
@admin_required
def admin_courses():
    """Список курсов"""
    courses = course_service.get_all_courses()

    for course in courses:
        modules = course_service.get_course_modules(course['id'])
        course['modules_count'] = len(modules)

        lessons = course_service.get_course_lessons(course['id'])
        course['lessons_count'] = len(lessons)

    return render_template('admin/courses.html', courses=courses)


@admin_bp.route('/admin/courses/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_course_create():
    """Создание курса"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        course_type = request.form.get('type', 'asosiy')
        status = request.form.get('status', 'draft')

        if not title:
            flash('Kurs nomi kiritish majburiy', 'error')
            return render_template('admin/course_edit.html',
                                   is_new=True,
                                   course=None,
                                   types=CourseType.get_all(),
                                   statuses=CourseStatus.get_all())

        # Обработка изображения
        image_file = request.files.get('image')
        image_name = 'default_course.jpg'

        if image_file and image_file.filename:
            ext = FileUtils.get_file_extension(image_file.filename)
            if ext in config.ALLOWED_IMAGE_EXTENSIONS:
                courses_img_dir = os.path.join(config.IMAGES_DIR, 'courses')
                os.makedirs(courses_img_dir, exist_ok=True)

                unique_name = f"{__import__('uuid').uuid4().hex[:8]}_{FileUtils.safe_filename(image_file.filename)}"
                image_path = os.path.join(courses_img_dir, unique_name)
                image_file.save(image_path)
                image_name = unique_name
            else:
                flash('Rasm formati ruxsat etilmaydi. JPG, PNG, GIF, SVG formatlarini ishlating', 'error')
                return render_template('admin/course_edit.html',
                                       is_new=True,
                                       course=None,
                                       types=CourseType.get_all(),
                                       statuses=CourseStatus.get_all())

        course_data = {
            'title': title,
            'description': description,
            'image': image_name,
            'type': course_type,
            'status': status
        }

        try:
            course = course_service.create_course(course_data)
            flash('Kurs muvaffaqiyatli yaratildi', 'success')
            return redirect(url_for('admin.admin_courses'))
        except Exception as e:
            flash(f'Xatolik yuz berdi: {str(e)}', 'error')
            return render_template('admin/course_edit.html',
                                   is_new=True,
                                   course=None,
                                   types=CourseType.get_all(),
                                   statuses=CourseStatus.get_all())

    return render_template('admin/course_edit.html',
                           is_new=True,
                           course=None,
                           types=CourseType.get_all(),
                           statuses=CourseStatus.get_all())


@admin_bp.route('/admin/courses/<course_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_course_edit(course_id):
    """Редактирование курса"""
    course = course_service.get_course(course_id)
    if not course:
        flash('Kurs topilmadi', 'error')
        return redirect(url_for('admin.admin_courses'))

    if request.method == 'POST':
        update_data = {}

        title = request.form.get('title', '').strip()
        if title:
            update_data['title'] = title
        else:
            flash('Kurs nomi kiritish majburiy', 'error')
            return render_template('admin/course_edit.html',
                                   course=course,
                                   is_new=False,
                                   types=CourseType.get_all(),
                                   statuses=CourseStatus.get_all())

        description = request.form.get('description', '').strip()
        if description:
            update_data['description'] = description

        course_type = request.form.get('type')
        if course_type:
            update_data['type'] = course_type

        status = request.form.get('status')
        if status:
            update_data['status'] = status

        # Обработка изображения
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            ext = FileUtils.get_file_extension(image_file.filename)
            if ext in config.ALLOWED_IMAGE_EXTENSIONS:
                # Удаляем старое изображение
                old_image = course.get('image')
                if old_image and old_image != 'default_course.jpg':
                    old_path = os.path.join(config.IMAGES_DIR, 'courses', old_image)
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except:
                            pass

                courses_img_dir = os.path.join(config.IMAGES_DIR, 'courses')
                os.makedirs(courses_img_dir, exist_ok=True)

                unique_name = f"{__import__('uuid').uuid4().hex[:8]}_{FileUtils.safe_filename(image_file.filename)}"
                image_path = os.path.join(courses_img_dir, unique_name)
                image_file.save(image_path)
                update_data['image'] = unique_name
            else:
                flash('Rasm formati ruxsat etilmaydi. JPG, PNG, GIF, SVG formatlarini ishlating', 'error')
                return render_template('admin/course_edit.html',
                                       course=course,
                                       is_new=False,
                                       types=CourseType.get_all(),
                                       statuses=CourseStatus.get_all())

        if update_data:
            try:
                course_service.update_course(course_id, update_data)
                flash('Kurs muvaffaqiyatli yangilandi', 'success')
            except Exception as e:
                flash(f'Xatolik yuz berdi: {str(e)}', 'error')

        return redirect(url_for('admin.admin_courses'))

    return render_template('admin/course_edit.html',
                           course=course,
                           is_new=False,
                           types=CourseType.get_all(),
                           statuses=CourseStatus.get_all())


@admin_bp.route('/admin/courses/<course_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_course_delete(course_id):
    """Удаление курса"""
    if course_service.delete_course(course_id):
        flash('Kurs o\'chirildi', 'success')
    else:
        flash('Kursni o\'chirishda xatolik', 'error')

    return redirect(url_for('admin.admin_courses'))


# ========== Управление модулями ==========

@admin_bp.route('/admin/courses/<course_id>/modules')
@login_required
@admin_required
def admin_modules(course_id):
    """Модули курса"""
    course = course_service.get_course(course_id)
    if not course:
        flash('Kurs topilmadi', 'error')
        return redirect(url_for('admin.admin_courses'))

    modules = course_service.get_course_modules(course_id)

    for module in modules:
        lessons = course_service.get_module_lessons(module['id'])
        module['lessons_count'] = len(lessons)

    return render_template('admin/modules.html', course=course, modules=modules)


@admin_bp.route('/admin/modules/create', methods=['POST'])
@login_required
@admin_required
def admin_module_create():
    """Создание модуля"""
    course_id = request.form.get('course_id')
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()

    if not title:
        flash('Modul nomi kiritish majburiy', 'error')
        return redirect(url_for('admin.admin_modules', course_id=course_id))

    module_data = {
        'course_id': course_id,
        'title': title,
        'description': description
    }

    module = course_service.create_module(module_data)
    flash('Modul muvaffaqiyatli yaratildi', 'success')
    return redirect(url_for('admin.admin_modules', course_id=course_id))


@admin_bp.route('/admin/modules/<module_id>/edit', methods=['POST'])
@login_required
@admin_required
def admin_module_edit(module_id):
    """Редактирование модуля"""
    module = course_service.get_module(module_id)
    if not module:
        flash('Modul topilmadi', 'error')
        return redirect(url_for('admin.admin_courses'))

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()

    update_data = {}
    if title:
        update_data['title'] = title
    if description:
        update_data['description'] = description

    if update_data:
        course_service.update_module(module_id, update_data)
        flash('Modul yangilandi', 'success')

    return redirect(url_for('admin.admin_modules', course_id=module['course_id']))


@admin_bp.route('/admin/modules/<module_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_module_delete(module_id):
    """Удаление модуля"""
    module = course_service.get_module(module_id)
    if not module:
        flash('Modul topilmadi', 'error')
        return redirect(url_for('admin.admin_courses'))

    course_id = module['course_id']

    if course_service.delete_module(module_id):
        flash('Modul o\'chirildi', 'success')
    else:
        flash('Xatolik yuz berdi', 'error')

    return redirect(url_for('admin.admin_modules', course_id=course_id))


# ========== Управление уроками ==========

@admin_bp.route('/admin/modules/<module_id>/lessons')
@login_required
@admin_required
def admin_lessons(module_id):
    """Уроки модуля"""
    module = course_service.get_module(module_id)
    if not module:
        flash('Modul topilmadi', 'error')
        return redirect(url_for('admin.admin_courses'))

    lessons = course_service.get_module_lessons(module_id)

    return render_template('admin/lessons.html', module=module, lessons=lessons)


@admin_bp.route('/admin/lessons/create', methods=['POST'])
@login_required
@admin_required
def admin_lesson_create():
    """Создание урока"""
    module_id = request.form.get('module_id')
    title = request.form.get('title', '').strip()
    lesson_type = request.form.get('type', 'text')
    description = request.form.get('description', '').strip()
    content = request.form.get('content', '').strip()

    if not title:
        flash('Dars nomi kiritish majburiy', 'error')
        return redirect(url_for('admin.admin_lessons', module_id=module_id))

    lesson_data = {
        'module_id': module_id,
        'title': title,
        'type': lesson_type,
        'description': description,
        'content': content
    }

    lesson = course_service.create_lesson(lesson_data)
    flash('Dars muvaffaqiyatli yaratildi', 'success')
    return redirect(url_for('admin.admin_lessons', module_id=module_id))


@admin_bp.route('/admin/lessons/<lesson_id>/edit', methods=['POST'])
@login_required
@admin_required
def admin_lesson_edit(lesson_id):
    """Редактирование урока"""
    lesson = course_service.get_lesson(lesson_id)
    if not lesson:
        flash('Dars topilmadi', 'error')
        return redirect(url_for('admin.admin_courses'))

    title = request.form.get('title', '').strip()
    lesson_type = request.form.get('type', 'text')
    description = request.form.get('description', '').strip()
    content = request.form.get('content', '').strip()

    update_data = {}
    if title:
        update_data['title'] = title
    if lesson_type:
        update_data['type'] = lesson_type
    if description:
        update_data['description'] = description
    if content:
        update_data['content'] = content

    if update_data:
        course_service.update_lesson(lesson_id, update_data)
        flash('Dars yangilandi', 'success')

    return redirect(url_for('admin.admin_lessons', module_id=lesson['module_id']))


@admin_bp.route('/admin/lessons/<lesson_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_lesson_delete(lesson_id):
    """Удаление урока"""
    lesson = course_service.get_lesson(lesson_id)
    if not lesson:
        flash('Dars topilmadi', 'error')
        return redirect(url_for('admin.admin_courses'))

    module_id = lesson['module_id']

    if course_service.delete_lesson(lesson_id):
        flash('Dars o\'chirildi', 'success')
    else:
        flash('Xatolik yuz berdi', 'error')

    return redirect(url_for('admin.admin_lessons', module_id=module_id))


# ========== Загрузка видео и файлов ==========

@admin_bp.route('/admin/lessons/<lesson_id>/video', methods=['POST'])
@login_required
@admin_required
def admin_upload_video(lesson_id):
    """Загрузка видео к уроку"""
    lesson = course_service.get_lesson(lesson_id)
    if not lesson:
        flash('Dars topilmadi', 'error')
        return redirect(url_for('admin.admin_courses'))

    if 'video' not in request.files:
        flash('Video fayl tanlanmagan', 'error')
        return redirect(url_for('admin.admin_lessons', module_id=lesson['module_id']))

    file = request.files['video']
    if file.filename == '':
        flash('Video fayl tanlanmagan', 'error')
        return redirect(url_for('admin.admin_lessons', module_id=lesson['module_id']))

    try:
        video_data = file_service.save_video(lesson_id, file)
        flash('Video muvaffaqiyatli yuklandi', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Xatolik yuz berdi: {str(e)}', 'error')

    return redirect(url_for('admin.admin_lessons', module_id=lesson['module_id']))


@admin_bp.route('/admin/lessons/<lesson_id>/video/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_video(lesson_id):
    """Удаление видео из урока"""
    if file_service.delete_video(lesson_id):
        flash('Video o\'chirildi', 'success')
    else:
        flash('Xatolik yuz berdi', 'error')

    lesson = course_service.get_lesson(lesson_id)
    return redirect(url_for('admin.admin_lessons', module_id=lesson['module_id']))


@admin_bp.route('/admin/lessons/<lesson_id>/file', methods=['POST'])
@login_required
@admin_required
def admin_upload_file(lesson_id):
    """Загрузка файла к уроку"""
    lesson = course_service.get_lesson(lesson_id)
    if not lesson:
        flash('Dars topilmadi', 'error')
        return redirect(url_for('admin.admin_courses'))

    if 'file' not in request.files:
        flash('Fayl tanlanmagan', 'error')
        return redirect(url_for('admin.admin_lessons', module_id=lesson['module_id']))

    file = request.files['file']
    if file.filename == '':
        flash('Fayl tanlanmagan', 'error')
        return redirect(url_for('admin.admin_lessons', module_id=lesson['module_id']))

    try:
        file_data = file_service.save_file(lesson_id, file)
        flash('Fayl muvaffaqiyatli yuklandi', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Xatolik yuz berdi: {str(e)}', 'error')

    return redirect(url_for('admin.admin_lessons', module_id=lesson['module_id']))


@admin_bp.route('/admin/lessons/<lesson_id>/file/<file_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_file(lesson_id, file_id):
    """Удаление файла из урока"""
    if file_service.delete_file(lesson_id, file_id):
        flash('Fayl o\'chirildi', 'success')
    else:
        flash('Xatolik yuz berdi', 'error')

    return redirect(url_for('admin.admin_lessons', module_id=course_service.get_lesson(lesson_id)['module_id']))


# ========== Управление бэкапами ==========

@admin_bp.route('/admin/backups')
@login_required
@admin_required
def admin_backups():
    """Список бэкапов"""
    backups = backup_service.get_backups()
    return render_template('admin/backups.html', backups=backups)


@admin_bp.route('/admin/backups/create', methods=['POST'])
@login_required
@admin_required
def admin_backup_create():
    """Создание бэкапа"""
    timestamp = backup_service.create_backup()
    flash(f'Zaxira nusxasi yaratildi: {timestamp}', 'success')
    return redirect(url_for('admin.admin_backups'))


@admin_bp.route('/admin/backups/<timestamp>/restore', methods=['POST'])
@login_required
@admin_required
def admin_backup_restore(timestamp):
    """Восстановление из бэкапа"""
    if backup_service.restore_backup(timestamp):
        flash('Zaxira nusxadan tiklandi', 'success')
    else:
        flash('Xatolik yuz berdi', 'error')

    return redirect(url_for('admin.admin_backups'))


@admin_bp.route('/admin/backups/<timestamp>/delete', methods=['POST'])
@login_required
@admin_required
def admin_backup_delete(timestamp):
    """Удаление бэкапа"""
    if backup_service.delete_backup(timestamp):
        flash('Zaxira nusxa o\'chirildi', 'success')
    else:
        flash('Xatolik yuz berdi', 'error')

    return redirect(url_for('admin.admin_backups'))


# ========== Логи ==========

@admin_bp.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    """Просмотр логов"""
    log_file = os.path.join(config.LOGS_DIR, 'system.log')
    logs = []

    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            logs = lines[-500:]

    return render_template('admin/logs.html', logs=logs)


# ========== Управление платежами ==========

@admin_bp.route('/admin/payments')
@login_required
@admin_required
def admin_payments():
    """Список платежей"""
    users = storage.get_users()
    pending_payments = []

    for user in users:
        if user.get('status') in ['pending_payment', 'payment_confirmed']:
            pending_payments.append(user)

    return render_template('admin/payments.html', users=pending_payments)


@admin_bp.route('/admin/payments/<user_id>/view')
@login_required
@admin_required
def admin_payment_view(user_id):
    """Просмотр квитанции"""
    user = storage.get_user(user_id)
    if not user:
        flash('Foydalanuvchi topilmadi', 'error')
        return redirect(url_for('admin.admin_payments'))

    return render_template('admin/payment_view.html', user=user)


@admin_bp.route('/admin/payments/<user_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_payment_approve(user_id):
    """Подтверждение платежа и отправка логина/пароля"""
    user = storage.get_user(user_id)
    if not user:
        flash('Foydalanuvchi topilmadi', 'error')
        return redirect(url_for('admin.admin_payments'))

    login = user.get('login')
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(10))

    update_data = {
        'status': UserStatus.ACTIVE,
        'verified_by': session.get('user_id'),
        'verified_at': DateUtils.now(),
        'login_sent': True,
        'updated_at': DateUtils.now()
    }

    if password:
        update_data['password_hash'] = PasswordManager.hash_password(password)

    storage.update_user(user_id, update_data)

    flash(f'To\'lov tasdiqlandi! Foydalanuvchiga SMS yuborildi. Login: {login}, Parol: {password}', 'success')
    return redirect(url_for('admin.admin_payments'))


@admin_bp.route('/admin/payments/<user_id>/reject', methods=['POST'])
@login_required
@admin_required
def admin_payment_reject(user_id):
    """Отклонение платежа"""
    user = storage.get_user(user_id)
    if not user:
        flash('Foydalanuvchi topilmadi', 'error')
        return redirect(url_for('admin.admin_payments'))

    reason = request.form.get('reason', 'Kvitansiya talablarga mos emas')

    update_data = {
        'status': UserStatus.PAYMENT_REJECTED,
        'payment_status': 'rejected',
        'verified_by': session.get('user_id'),
        'verified_at': DateUtils.now(),
        'updated_at': DateUtils.now()
    }
    storage.update_user(user_id, update_data)

    flash(f'To\'lov rad etildi. Sabab: {reason}', 'warning')
    return redirect(url_for('admin.admin_payments'))


@admin_bp.route('/admin/payments/<user_id>/resend', methods=['POST'])
@login_required
@admin_required
def admin_payment_resend(user_id):
    """Повторная отправка логина/пароля"""
    user = storage.get_user(user_id)
    if not user:
        flash('Foydalanuvchi topilmadi', 'error')
        return redirect(url_for('admin.admin_payments'))

    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(10))

    storage.update_user(user_id, {
        'password_hash': PasswordManager.hash_password(password),
        'login_sent': True,
        'updated_at': DateUtils.now()
    })

    flash(f'SMS qayta yuborildi. Parol: {password}', 'success')
    return redirect(url_for('admin.admin_payments'))


# ========== История оплат ==========

@admin_bp.route('/admin/payments/history')
@login_required
@admin_required
def admin_payments_history():
    """История всех оплат"""
    users = storage.get_users()
    payment_history = []

    for user in users:
        if user.get('payment_status') in ['paid', 'rejected'] or user.get('status') in ['active', 'payment_rejected']:
            payment_history.append(user)

    payment_history.sort(key=lambda x: x.get('payment_date', ''), reverse=True)

    return render_template('admin/payments_history.html', users=payment_history)