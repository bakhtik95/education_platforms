# routes/user.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from core import AuthManager, login_required
from services import UserService, AccessService, ProgressService, CourseService
from core.storage import JSONStorage
from core.utils import FileUtils, DateUtils

user_bp = Blueprint('user', __name__)
storage = JSONStorage()
auth_manager = AuthManager(storage)
user_service = UserService(storage)
access_service = AccessService(storage)
progress_service = ProgressService(storage)
course_service = CourseService(storage)


@user_bp.route('/courses')
@login_required
def courses():
    user_id = session.get('user_id')
    user = user_service.get_user(user_id)

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    courses = access_service.get_user_courses(user_id)

    for course in courses:
        progress = progress_service.get_course_progress(user_id, course['id'])
        course['progress'] = progress.get('progress', 0)
        course['progress_status'] = progress.get('status', 'not_started')

        modules = course_service.get_course_modules(course['id'])
        course['modules_count'] = len(modules)

        lessons = course_service.get_course_lessons(course['id'])
        course['lessons_count'] = len(lessons)

    return render_template('user/courses.html',
                           user=user,
                           courses=courses)


@user_bp.route('/course/<course_id>')
@login_required
def course_detail(course_id):
    user_id = session.get('user_id')
    user = user_service.get_user(user_id)

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    if not access_service.check_access(user_id, course_id):
        flash('Sizda bu kursga kirish huquqi yo\'q', 'error')
        return redirect(url_for('user.courses'))

    course = course_service.get_course(course_id)
    if not course:
        flash('Kurs topilmadi', 'error')
        return redirect(url_for('user.courses'))

    modules = course_service.get_course_modules(course_id)

    for module in modules:
        lessons = course_service.get_module_lessons(module['id'])
        module['lessons'] = lessons
        module['lessons_count'] = len(lessons)

        module_progress = progress_service.get_module_progress(user_id, module['id'])
        module['progress'] = module_progress.get('progress', 0)

        for lesson in lessons:
            lesson_progress = progress_service.get_lesson_progress(user_id, lesson['id'])
            lesson['completed'] = lesson_progress.get('completed', False)
            lesson['video_position'] = lesson_progress.get('video_position', 0)

    course_progress = progress_service.get_course_progress(user_id, course_id)
    course['progress'] = course_progress.get('progress', 0)

    stats = course_service.get_course_stats_with_details(course_id)

    return render_template('user/course.html',
                           user=user,
                           course=course,
                           modules=modules,
                           stats=stats)


@user_bp.route('/lesson/<lesson_id>')
@login_required
def lesson_detail(lesson_id):
    user_id = session.get('user_id')
    user = user_service.get_user(user_id)

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    lesson = course_service.get_lesson(lesson_id)
    if not lesson:
        flash('Dars topilmadi', 'error')
        return redirect(url_for('user.courses'))

    module = course_service.get_module(lesson.get('module_id'))
    if not module:
        flash('Modul topilmadi', 'error')
        return redirect(url_for('user.courses'))

    course_id = module.get('course_id')
    if not access_service.check_access(user_id, course_id):
        flash('Sizda bu darsga kirish huquqi yo\'q', 'error')
        return redirect(url_for('user.courses'))

    course = course_service.get_course(course_id)
    if not course:
        flash('Kurs topilmadi', 'error')
        return redirect(url_for('user.courses'))

    progress = progress_service.get_lesson_progress(user_id, lesson_id)

    navigation = course_service.get_lesson_navigation(lesson_id)

    modules = course_service.get_course_modules(course_id)
    for module in modules:
        module_lessons = course_service.get_module_lessons(module['id'])
        module['lessons'] = module_lessons
        for l in module_lessons:
            l_progress = progress_service.get_lesson_progress(user_id, l['id'])
            l['completed'] = l_progress.get('completed', False)

    return render_template('user/lesson.html',
                           user=user,
                           course=course,
                           lesson=lesson,
                           modules=modules,
                           progress=progress,
                           navigation=navigation)


@user_bp.route('/lesson/<lesson_id>/progress', methods=['POST'])
@login_required
def update_lesson_progress(lesson_id):
    user_id = session.get('user_id')

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid data'}), 400

    position = data.get('position', 0)
    completed = data.get('completed', False)

    lesson = course_service.get_lesson(lesson_id)
    if not lesson:
        return jsonify({'error': 'Lesson not found'}), 404

    module = course_service.get_module(lesson.get('module_id'))
    if not module:
        return jsonify({'error': 'Module not found'}), 404

    course_id = module.get('course_id')
    if not access_service.check_access(user_id, course_id):
        return jsonify({'error': 'Access denied'}), 403

    success = progress_service.update_progress(user_id, lesson_id, position, completed)

    if success:
        return jsonify({
            'success': True,
            'position': position,
            'completed': completed
        })
    else:
        return jsonify({'error': 'Failed to update progress'}), 500


@user_bp.route('/profile')
@login_required
def profile():
    user_id = session.get('user_id')
    user = user_service.get_user(user_id)

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    stats = progress_service.get_user_stats(user_id)

    return render_template('user/profile.html',
                           user=user,
                           stats=stats)


@user_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    user_id = session.get('user_id')
    user = user_service.get_user(user_id)

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()

    update_data = {}

    if full_name:
        update_data['full_name'] = full_name

    if email:
        update_data['email'] = email

    if phone:
        update_data['phone'] = phone

    if update_data:
        try:
            user_service.update_user(user_id, update_data)
            flash('Profil muvaffaqiyatli yangilandi', 'success')
        except ValueError as e:
            flash(str(e), 'error')

    return redirect(url_for('user.profile'))


@user_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    user_id = session.get('user_id')
    user = user_service.get_user(user_id)

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not user_service.verify_user_password(user_id, current_password):
        flash('Joriy parol noto\'g\'ri', 'error')
        return redirect(url_for('user.profile'))

    if new_password != confirm_password:
        flash('Yangi parollar mos kelmadi', 'error')
        return redirect(url_for('user.profile'))

    try:
        user_service.change_user_password(user_id, new_password)
        flash('Parol muvaffaqiyatli o\'zgartirildi', 'success')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(url_for('user.profile'))