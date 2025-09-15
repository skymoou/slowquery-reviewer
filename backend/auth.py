from functools import wraps
from flask import request, g, Blueprint
import jwt
import hashlib
import logging
from datetime import datetime, timedelta
from config import JWT_SECRET_KEY
from utils import api_response
from db import get_db

# 创建蓝图
auth_bp = Blueprint('auth', __name__)

# 配置日志
logger = logging.getLogger(__name__)

def hash_password(password):
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token(user_data):
    """生成JWT token"""
    payload = {
        'user_id': user_data['id'],
        'username': user_data['username'],
        'exp': datetime.utcnow() + timedelta(days=1)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """验证JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_user_permissions(db, user_id):
    """获取用户权限"""
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute('''
            SELECT DISTINCT p.name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            JOIN role_permissions rp ON r.id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE u.id = %s
        ''', (user_id,))
        permissions = cursor.fetchall()
        return [p['name'] for p in permissions]
    finally:
        cursor.close()

def get_user_roles(db, user_id):
    """获取用户角色"""
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute('''
            SELECT DISTINCT r.name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = %s
        ''', (user_id,))
        roles = cursor.fetchall()
        return [r['name'] for r in roles]
    finally:
        cursor.close()

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f"Request headers: {dict(request.headers)}")
        token = request.headers.get('Authorization')
        if not token:
            logger.warning("No Authorization header found")
            return api_response(success=False, message='未登录', status_code=401)
        
        logger.debug(f"Raw token: {token}")
        clean_token = token.replace('Bearer ', '')
        logger.debug(f"Clean token: {clean_token}")
        
        payload = verify_token(clean_token)
        if not payload:
            logger.warning("Token verification failed")
            return api_response(success=False, message='登录已过期', status_code=401)
        
        logger.debug(f"Token payload: {payload}")
        
        g.user_id = payload['user_id']
        g.username = payload['username']
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_code):
    """权限验证装饰器"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            from db import get_db
            db = get_db()
            try:
                permissions = get_user_permissions(db, g.user_id)
                roles = get_user_roles(db, g.user_id)
                
                # 管理员角色拥有所有权限
                if 'admin' in roles:
                    return f(*args, **kwargs)
                
                if permission_code not in permissions:
                    return api_response(
                        success=False, 
                        message='权限不足',
                        status_code=403
                    )
                return f(*args, **kwargs)
            finally:
                db.close()
        return decorated_function
    return decorator
