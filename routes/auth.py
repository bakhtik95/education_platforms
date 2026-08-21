# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import User, UserStatus
from core import AuthManager, PasswordManager
from services import UserService
from core.storage import JSONStorage
from core.utils import DateUtils
import os
import uuid
from werkzeug.utils import secure_filename
from config import get_config

auth_bp = Blueprint('auth', __name__)
storage = JSONStorage()
auth_manager = AuthManager(storage)
user_service = UserService(storage)
config = get_config()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if auth_manager.is_authenticated():
        user = storage.get_user(session['user_id'])
        if user and user.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('user.courses'))

    if request.method == 'POST':
        login = request.form.get('login', '').strip()
        password = request.form.get('password', '')

        if not login or not password:
            flash('Iltimos, login va parolni kiriting', 'error')
            return render_template('auth/login.html')

        user = storage.find_user_by_login(login)
        if not user:
            flash('Login yoki parol noto\'g\'ri', 'error')
            return render_template('auth/login.html')

        # Проверка статуса
        if user.get('status') == UserStatus.BLOCKED:
            flash('Sizning hisobingiz bloklangan. Admin bilan bog\'laning', 'error')
            return render_template('auth/login.html')

        if user.get('status') == UserStatus.PENDING_PAYMENT:
            flash('To\'lov kutilmoqda. Iltimos, to\'lovni amalga oshiring va kvitansiyani yuklang', 'warning')
            return redirect(url_for('auth.payment', user_id=user['id']))

        if user.get('status') == UserStatus.PAYMENT_CONFIRMED:
            flash('Hisobingiz hali faollashtirilmagan. Admin tasdiqlashini kuting', 'warning')
            return render_template('auth/login.html')

        if user.get('status') == UserStatus.PAYMENT_REJECTED:
            flash('To\'lovingiz rad etilgan. Iltimos, admin bilan bog\'laning', 'error')
            return render_template('auth/login.html')

        if user.get('status') != UserStatus.ACTIVE:
            flash('Hisobingiz faollashtirilmagan. Admin bilan bog\'laning', 'error')
            return render_template('auth/login.html')

        # Проверка пароля
        if PasswordManager.verify_password(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['role'] = user.get('role', 'user')
            session.permanent = True

            flash('Tizimga muvaffaqiyatli kirdingiz', 'success')

            if user.get('role') == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('user.courses'))
        else:
            flash('Login yoki parol noto\'g\'ri', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if auth_manager.is_authenticated():
        user = storage.get_user(session['user_id'])
        if user and user.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('user.courses'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        login = request.form.get('login', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        errors = []

        if not full_name:
            errors.append('F.I.Sh. kiritish majburiy')

        if not login or len(login) < 3:
            errors.append('Login kamida 3 ta belgidan iborat bo\'lishi kerak')

        if not password:
            errors.append('Parol kiritish majburiy')
        elif password != password_confirm:
            errors.append('Parollar mos kelmadi')

        if email:
            valid, msg = User.validate_email(email)
            if not valid:
                errors.append(msg)

        if phone:
            valid, msg = User.validate_phone(phone)
            if not valid:
                errors.append(msg)

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html',
                                   full_name=full_name, login=login,
                                   email=email, phone=phone)

        if storage.find_user_by_login(login):
            flash('Bu login allaqachon mavjud', 'error')
            return render_template('auth/register.html',
                                   full_name=full_name, email=email, phone=phone)

        if email and storage.find_user_by_email(email):
            flash('Bu email allaqachon mavjud', 'error')
            return render_template('auth/register.html',
                                   full_name=full_name, login=login, phone=phone)

        # Создание пользователя со статусом PENDING_PAYMENT
        user_data = {
            'full_name': full_name,
            'login': login,
            'email': email if email else None,
            'phone': phone if phone else None,
            'password': password,
            'role': 'user',
            'status': UserStatus.PENDING_PAYMENT,
            'access_type': 'free',
            'payment_status': 'pending',
            'payment_amount': 50000,  # Сумма пошлины в узбекских сумах
            'login_sent': False
        }

        try:
            user = user_service.create_user(user_data)
            flash('Ro\'yxatdan o\'tish muvaffaqiyatli! Iltimos, to\'lovni amalga oshiring', 'success')
            return redirect(url_for('auth.payment', user_id=user['id']))
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('auth/register.html',
                                   full_name=full_name, login=login,
                                   email=email, phone=phone)

    return render_template('auth/register.html')


@auth_bp.route('/payment/<user_id>', methods=['GET', 'POST'])
def payment(user_id):
    """Страница оплаты и загрузки квитанции"""
    user = storage.get_user(user_id)
    if not user:
        flash('Foydalanuvchi topilmadi', 'error')
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        payment_method = request.form.get('payment_method', '')
        if payment_method == 'bank_transfer':
            flash('To\'lov ma\'lumotlari: ...', 'info')
            return render_template('auth/payment.html', user=user)
        elif payment_method == 'payme':
            flash('Payme orqali to\'lov: ...', 'info')
            return render_template('auth/payment.html', user=user)
        elif payment_method == 'click':
            flash('Click orqali to\'lov: ...', 'info')
            return render_template('auth/payment.html', user=user)

        flash('Iltimos, to\'lov usulini tanlang', 'warning')
        return render_template('auth/payment.html', user=user)

    return render_template('auth/payment.html', user=user)


@auth_bp.route('/upload-receipt/<user_id>', methods=['GET', 'POST'])
def upload_receipt(user_id):
    """Загрузка квитанции об оплате"""
    user = storage.get_user(user_id)
    if not user:
        flash('Foydalanuvchi topilmadi', 'error')
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        if 'receipt' not in request.files:
            flash('Kvitansiya faylini tanlang', 'error')
            return render_template('auth/upload_receipt.html', user=user)

        file = request.files['receipt']
        if file.filename == '':
            flash('Kvitansiya faylini tanlang', 'error')
            return render_template('auth/upload_receipt.html', user=user)

        # Проверка расширения
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.pdf', '.gif', '.svg'}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            flash('Ruxsat etilgan formatlar: JPG, PNG, PDF, GIF, SVG', 'error')
            return render_template('auth/upload_receipt.html', user=user)

        # Сохранение квитанции
        receipts_dir = config.RECEIPTS_DIR
        os.makedirs(receipts_dir, exist_ok=True)

        unique_name = f"{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
        file_path = os.path.join(receipts_dir, unique_name)
        file.save(file_path)

        # Обновление пользователя
        update_data = {
            'receipt_file': unique_name,
            'receipt_uploaded_at': DateUtils.now(),
            'status': UserStatus.PAYMENT_CONFIRMED,
            'payment_status': 'paid',
            'payment_date': DateUtils.now(),
            'updated_at': DateUtils.now()
        }
        storage.update_user(user_id, update_data)

        flash('Kvitansiya muvaffaqiyatli yuklandi! Admin tasdiqlashini kuting', 'success')
        return redirect(url_for('auth.payment_success', user_id=user_id))

    return render_template('auth/upload_receipt.html', user=user)


@auth_bp.route('/payment-success/<user_id>')
def payment_success(user_id):
    """Страница успешной оплаты"""
    user = storage.get_user(user_id)
    if not user:
        flash('Foydalanuvchi topilmadi', 'error')
        return redirect(url_for('auth.register'))

    return render_template('auth/payment_success.html', user=user)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Siz tizimdan chiqdingiz', 'info')
    return redirect(url_for('auth.login'))