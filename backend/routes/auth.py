from flask import Blueprint, request, g
from auth import generate_token, login_required, get_user_permissions, get_user_roles
from utils import api_response
from db import get_db
import logging
import bcrypt

# 配置日志
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    if not data or 'username' not in data or 'password' not in data:
        return api_response(success=False, message='用户名和密码不能为空')
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # 获取用户信息
        logger.debug(f"Login attempt - Username: {data['username']}")
        
        cursor.execute("""
            SELECT u.id, u.username, u.password_hash, r.name as role_name 
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE u.username = %s
        """, (data['username'],))
        user = cursor.fetchone()
        
        if not user:
            logger.debug(f"User not found: {data['username']}")
            return api_response(success=False, message='用户名或密码错误')
        
        # 验证密码
        if not bcrypt.checkpw(data['password'].encode('utf-8'), user['password_hash'].encode('utf-8')):
            logger.debug("Password hash mismatch")
            return api_response(success=False, message='用户名或密码错误')
        
        # 获取用户权限和角色
        permissions = get_user_permissions(db, user['id'])
        roles = get_user_roles(db, user['id'])
        
        # 生成token
        token = generate_token(user)
        
        return api_response(success=True, message='登录成功', data={
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'permissions': permissions,
                'roles': roles
            }
        })
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/user/info', methods=['GET'])
@login_required
def get_user_info():
    """获取当前用户信息"""
    from app import get_db
    
    db = get_db()
    try:
        permissions = get_user_permissions(db, g.user_id)
        roles = get_user_roles(db, g.user_id)
        
        return api_response(success=True, data={
            'id': g.user_id,
            'username': g.username,
            'permissions': permissions,
            'roles': roles
        })
    finally:
        db.close()

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    # JWT采用无状态设计，客户端删除token即可
    return api_response(success=True, message='登出成功')
