# create_admin.py
from core.storage import JSONStorage
from services import UserService
from models import UserRoles, UserStatus, AccessType

storage = JSONStorage()
user_service = UserService(storage)

admin_data = {
    'full_name': 'Administrator',
    'login': 'admin',
    'email': 'admin@example.com',
    'phone': '+998901234567',
    'password': 'admin123',
    'role': UserRoles.ADMIN,
    'status': UserStatus.ACTIVE,
    'access_type': AccessType.FREE
}

try:
    user = user_service.create_user(admin_data)
    print(f"✅ Admin created: {user['login']}")
    print(f"Password: admin123")
except Exception as e:
    print(f"❌ Failed: {e}")