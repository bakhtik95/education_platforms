# routes/course.py
import os
import mimetypes
from flask import Blueprint, request, Response, stream_with_context, abort, send_file, session, render_template, \
    current_app, make_response
from core import login_required
from services import AccessService, CourseService, FileService
from core.storage import JSONStorage
from config import get_config

course_bp = Blueprint('media', __name__)
storage = JSONStorage()
access_service = AccessService(storage)
course_service = CourseService(storage)
file_service = FileService(storage)
config = get_config()


@course_bp.route('/media/video/<filename>')
@login_required
def stream_video(filename):
    user_id = session.get('user_id')

    lesson = storage.get_lesson_by_video(filename)
    if lesson:
        module = storage.get_module(lesson.get('module_id'))
        if module:
            course_id = module.get('course_id')
            if not access_service.check_access(user_id, course_id):
                abort(403)

    video_path = file_service.get_video_path(filename)
    if not video_path:
        courses_video_path = os.path.join(config.VIDEO_DIR, 'courses', filename)
        if os.path.exists(courses_video_path):
            video_path = courses_video_path
        else:
            abort(404)

    file_size = os.path.getsize(video_path)
    range_header = request.headers.get('Range', None)

    if not range_header:
        return send_file(
            video_path,
            mimetype='video/mp4',
            as_attachment=False,
            conditional=True,
            etag=False
        )

    byte_range = range_header.replace('bytes=', '').split('-')
    start = int(byte_range[0]) if byte_range[0] else 0
    end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1

    if start >= file_size or end >= file_size:
        return '', 416

    chunk_size = end - start + 1

    def generate():
        with open(video_path, 'rb') as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                read_size = min(1024 * 1024, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    response = Response(
        stream_with_context(generate()),
        status=206,
        mimetype='video/mp4',
        direct_passthrough=True
    )

    response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Content-Length'] = chunk_size
    response.headers['Cache-Control'] = 'public, max-age=3600'

    return response


@course_bp.route('/media/file/<file_id>')
@login_required
def download_file(file_id):
    user_id = session.get('user_id')

    file_data = storage.get_file(file_id)
    if not file_data:
        abort(404)

    lesson = storage.get_lesson_by_file(file_id)
    if not lesson:
        abort(404)

    module = storage.get_module(lesson.get('module_id'))
    if not module:
        abort(404)

    course_id = module.get('course_id')
    if not access_service.check_access(user_id, course_id):
        abort(403)

    file_type = file_data.get('type', 'other')
    filename = file_data.get('filename')
    original_name = file_data.get('original_name', filename)

    file_path = file_service.get_file_path(filename, file_type)
    if not file_path:
        abort(404)

    # Определяем MIME тип
    mime_type = file_service.get_mime_type(original_name)

    # Проверяем можно ли просмотреть файл в браузере
    is_inline = file_service.is_inline_viewable(original_name)

    # Для PDF используем специальную обработку для корректного отображения
    if mime_type == 'application/pdf' or original_name.lower().endswith('.pdf'):
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()

            response = make_response(file_content)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename="{original_name}"'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['Content-Length'] = str(len(file_content))
            return response
        except Exception as e:
            abort(500)

    # Для изображений и видео отправляем как inline
    if is_inline:
        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=False,
            download_name=original_name,
            conditional=False,
            etag=False,
            max_age=0
        )

    # Для остальных файлов - как attachment (загрузка)
    return send_file(
        file_path,
        mimetype=mime_type,
        as_attachment=True,
        download_name=original_name,
        conditional=False,
        etag=False,
        max_age=0
    )


@course_bp.route('/media/file/view/<file_id>')
@login_required
def view_file(file_id):
    """
    Специальный маршрут для просмотра файлов в браузере
    без блокировки iframe
    """
    user_id = session.get('user_id')

    file_data = storage.get_file(file_id)
    if not file_data:
        abort(404)

    lesson = storage.get_lesson_by_file(file_id)
    if not lesson:
        abort(404)

    module = storage.get_module(lesson.get('module_id'))
    if not module:
        abort(404)

    course_id = module.get('course_id')
    if not access_service.check_access(user_id, course_id):
        abort(403)

    file_type = file_data.get('type', 'other')
    filename = file_data.get('filename')
    original_name = file_data.get('original_name', filename)

    file_path = file_service.get_file_path(filename, file_type)
    if not file_path:
        abort(404)

    # Определяем MIME тип
    mime_type = file_service.get_mime_type(original_name)

    # Для PDF используем специальную обработку
    if mime_type == 'application/pdf' or original_name.lower().endswith('.pdf'):
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()

            response = make_response(file_content)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename="{original_name}"'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['Content-Length'] = str(len(file_content))
            return response
        except Exception as e:
            abort(500)

    # Для изображений и видео отправляем как inline
    is_inline = file_service.is_inline_viewable(original_name)

    return send_file(
        file_path,
        mimetype=mime_type,
        as_attachment=not is_inline,
        download_name=original_name,
        conditional=False,
        etag=False,
        max_age=0
    )