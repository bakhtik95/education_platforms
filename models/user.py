# models/user.py - ДОБАВИТЬ НОВЫЕ СТАТУСЫ
from datetime import datetime
from typing import Optional, Dict, Any
from core.utils import Utils, DateUtils


class UserRoles:
    ADMIN = 'admin'
    USER = 'user'

    @staticmethod
    def get_all():
        return [UserRoles.ADMIN, UserRoles.USER]

    @staticmethod
    def is_valid(role: str) -> bool:
        return role in UserRoles.get_all()


class UserStatus:
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    BLOCKED = 'blocked'
    PENDING = 'pending'
    PENDING_PAYMENT = 'pending_payment'  # НОВЫЙ СТАТУС - ожидание оплаты
    PAYMENT_CONFIRMED = 'payment_confirmed'  # НОВЫЙ СТАТУС - оплата подтверждена
    PAYMENT_REJECTED = 'payment_rejected'  # НОВЫЙ СТАТУС - оплата отклонена

    @staticmethod
    def get_all():
        return [UserStatus.ACTIVE, UserStatus.INACTIVE, UserStatus.BLOCKED,
                UserStatus.PENDING, UserStatus.PENDING_PAYMENT,
                UserStatus.PAYMENT_CONFIRMED, UserStatus.PAYMENT_REJECTED]

    @staticmethod
    def is_valid(status: str) -> bool:
        return status in UserStatus.get_all()


class AccessType:
    FREE = 'free'
    PAID = 'paid'

    @staticmethod
    def get_all():
        return [AccessType.FREE, AccessType.PAID]

    @staticmethod
    def is_valid(access_type: str) -> bool:
        return access_type in AccessType.get_all()


class User:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.full_name = data.get('full_name', '')
        self.login = data.get('login', '')
        self.email = data.get('email', '')
        self.phone = data.get('phone', '')
        self.password_hash = data.get('password_hash', '')
        self.role = data.get('role', UserRoles.USER)
        self.access_type = data.get('access_type', AccessType.FREE)
        self.status = data.get('status', UserStatus.PENDING)
        self.created_at = data.get('created_at', DateUtils.now())
        self.updated_at = data.get('updated_at')
        # Новые поля
        self.payment_status = data.get('payment_status', 'pending')  # pending, paid, rejected
        self.payment_amount = data.get('payment_amount', 0)
        self.payment_date = data.get('payment_date')
        self.receipt_file = data.get('receipt_file')  # имя файла квитанции
        self.receipt_uploaded_at = data.get('receipt_uploaded_at')
        self.verified_by = data.get('verified_by')  # ID администратора
        self.verified_at = data.get('verified_at')
        self.login_sent = data.get('login_sent', False)  # отправлен ли логин и пароль

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'full_name': self.full_name,
            'login': self.login,
            'email': self.email,
            'phone': self.phone,
            'password_hash': self.password_hash,
            'role': self.role,
            'access_type': self.access_type,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'payment_status': self.payment_status,
            'payment_amount': self.payment_amount,
            'payment_date': self.payment_date,
            'receipt_file': self.receipt_file,
            'receipt_uploaded_at': self.receipt_uploaded_at,
            'verified_by': self.verified_by,
            'verified_at': self.verified_at,
            'login_sent': self.login_sent
        }

    def is_admin(self) -> bool:
        return self.role == UserRoles.ADMIN

    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    def is_pending_payment(self) -> bool:
        return self.status == UserStatus.PENDING_PAYMENT

    def is_payment_confirmed(self) -> bool:
        return self.status == UserStatus.PAYMENT_CONFIRMED

    def can_access_course(self, course_id: str, access_service) -> bool:
        if self.is_admin():
            return True
        return access_service.check_access(self.id, course_id)

    def get_display_name(self) -> str:
        if self.full_name:
            return self.full_name
        return self.login

    def get_status_display(self) -> str:
        status_map = {
            UserStatus.ACTIVE: 'Faol',
            UserStatus.INACTIVE: 'Faol emas',
            UserStatus.BLOCKED: 'Bloklangan',
            UserStatus.PENDING: 'Kutilmoqda',
            UserStatus.PENDING_PAYMENT: 'To\'lov kutilmoqda',
            UserStatus.PAYMENT_CONFIRMED: 'To\'lov tasdiqlangan',
            UserStatus.PAYMENT_REJECTED: 'To\'lov rad etilgan'
        }
        return status_map.get(self.status, self.status)

    def get_payment_status_display(self) -> str:
        status_map = {
            'pending': 'Kutilmoqda',
            'paid': 'To\'langan',
            'rejected': 'Rad etilgan'
        }
        return status_map.get(self.payment_status, self.payment_status)

    def get_access_type_display(self) -> str:
        type_map = {
            AccessType.FREE: 'Bepul',
            AccessType.PAID: 'Pullik'
        }
        return type_map.get(self.access_type, self.access_type)

    def get_role_display(self) -> str:
        role_map = {
            UserRoles.ADMIN: 'Administrator',
            UserRoles.USER: 'Foydalanuvchi'
        }
        return role_map.get(self.role, self.role)

    @staticmethod
    def validate_login(login: str) -> tuple:
        if not login or len(login) < 3:
            return False, "Login kamida 3 ta belgidan iborat bo'lishi kerak"
        if not login.isalnum():
            return False, "Login faqat harflar va raqamlardan iborat bo'lishi kerak"
        return True, ""

    @staticmethod
    def validate_email(email: str) -> tuple:
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not email or not re.match(pattern, email):
            return False, "Email noto'g'ri formatda"
        return True, ""

    @staticmethod
    def validate_phone(phone: str) -> tuple:
        import re
        phone = re.sub(r'[\s\-()]', '', phone)
        pattern = r'^\+?998[0-9]{9}$|^[0-9]{9,12}$'
        if not phone or not re.match(pattern, phone):
            return False, "Telefon raqam noto'g'ri formatda"
        return True, ""