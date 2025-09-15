#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
慢查询分析系统 - 用户初始化脚本
=================================

此脚本用于初始化系统默认用户账户，包括：
- admin (管理员)
- dba (数据库管理员) 
- dev (开发者)

使用方法：
1. 确保数据库连接配置正确
2. 运行: python init_default_users.py
3. 使用生成的账户登录系统

默认账户信息：
- 管理员: admin / Admin@123
- DBA: dba / Dba@123  
- 开发者: dev / Dev@123
"""

import sys
import os
import mysql.connector
import bcrypt
from datetime import datetime

# 添加当前目录到Python路径，以便导入config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import DB_CONFIG
except ImportError:
    print("❌ 错误: 无法导入数据库配置")
    print("请确保当前目录存在 config.py 文件")
    sys.exit(1)

# 默认用户配置
DEFAULT_USERS = [
    {
        'username': 'admin',
        'password': 'Admin@123', 
        'role': 'admin',
        'description': '系统管理员账户'
    },
    {
        'username': 'dba',
        'password': 'Dba@123',
        'role': 'dba', 
        'description': '数据库管理员账户'
    },
    {
        'username': 'dev',
        'password': 'Dev@123',
        'role': 'dev',
        'description': '开发者账户'
    }
]

def print_banner():
    """打印横幅"""
    print("=" * 60)
    print("🚀 慢查询分析系统 - 用户初始化脚本")
    print("=" * 60)
    print()

def test_database_connection():
    """测试数据库连接"""
    try:
        print("🔗 测试数据库连接...")
        conn = mysql.connector.connect(**DB_CONFIG)
        conn.close()
        print("✅ 数据库连接成功")
        return True
    except mysql.connector.Error as e:
        print(f"❌ 数据库连接失败: {e}")
        print("\n请检查以下配置:")
        print(f"   - 主机: {DB_CONFIG.get('host', 'N/A')}")
        print(f"   - 端口: {DB_CONFIG.get('port', 'N/A')}")
        print(f"   - 数据库: {DB_CONFIG.get('database', 'N/A')}")
        print(f"   - 用户: {DB_CONFIG.get('user', 'N/A')}")
        return False

def create_tables_if_not_exists():
    """创建必要的表（如果不存在）"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("📋 检查并创建必要的数据表...")
        
        # 创建角色表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 创建权限表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 创建角色-权限关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id INT,
                permission_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (role_id, permission_id),
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role_id INT,
                email VARCHAR(100),
                full_name VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL,
                INDEX idx_username (username),
                INDEX idx_is_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        conn.commit()
        print("✅ 数据表检查完成")
        
    except mysql.connector.Error as e:
        conn.rollback()
        print(f"❌ 创建表失败: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def initialize_roles_and_permissions():
    """初始化角色和权限"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("🛡️ 初始化角色和权限...")
        
        # 定义权限
        permissions = [
            ('SLOW_QUERY_VIEW', '查看慢查询列表和详情'),
            ('SLOW_QUERY_EXPORT', '导出慢查询数据'), 
            ('SLOW_QUERY_ANALYZE', '分析慢查询并生成优化建议'),
            ('OPTIMIZATION_EDIT', '编辑优化建议和状态'),
            ('USER_VIEW', '查看用户列表'),
            ('USER_MANAGE', '用户管理(增删改)'),
            ('SYSTEM_CONFIG', '系统配置管理'),
            ('SYSTEM_LOGS', '查看系统日志'),
            ('DATABASE_MANAGE', '数据库管理操作')
        ]
        
        # 插入权限
        for name, description in permissions:
            cursor.execute("""
                INSERT IGNORE INTO permissions (name, description) 
                VALUES (%s, %s)
            """, (name, description))
        
        # 定义角色
        roles = [
            ('dev', '开发人员 - 可以查看慢查询信息'),
            ('dba', '数据库管理员 - 可以分析和优化慢查询'),
            ('admin', '系统管理员 - 拥有所有权限')
        ]
        
        # 插入角色
        for name, description in roles:
            cursor.execute("""
                INSERT IGNORE INTO roles (name, description) 
                VALUES (%s, %s)
            """, (name, description))
        
        # 获取角色和权限ID
        cursor.execute("SELECT id, name FROM roles")
        role_ids = {row[1]: row[0] for row in cursor.fetchall()}
        
        cursor.execute("SELECT id, name FROM permissions")
        perm_ids = {row[1]: row[0] for row in cursor.fetchall()}
        
        # 设置角色权限映射
        role_permissions = {
            'dev': [
                'SLOW_QUERY_VIEW'
            ],
            'dba': [
                'SLOW_QUERY_VIEW', 
                'SLOW_QUERY_EXPORT', 
                'SLOW_QUERY_ANALYZE',
                'OPTIMIZATION_EDIT',
                'DATABASE_MANAGE'
            ],
            'admin': [
                'SLOW_QUERY_VIEW', 
                'SLOW_QUERY_EXPORT', 
                'SLOW_QUERY_ANALYZE',
                'OPTIMIZATION_EDIT', 
                'USER_VIEW',
                'USER_MANAGE', 
                'SYSTEM_CONFIG',
                'SYSTEM_LOGS',
                'DATABASE_MANAGE'
            ]
        }
        
        # 清除现有的角色权限关联（重新设置）
        cursor.execute("DELETE FROM role_permissions")
        
        # 插入角色-权限关联
        for role, perms in role_permissions.items():
            if role in role_ids:
                role_id = role_ids[role]
                for perm in perms:
                    if perm in perm_ids:
                        perm_id = perm_ids[perm]
                        cursor.execute("""
                            INSERT INTO role_permissions (role_id, permission_id)
                            VALUES (%s, %s)
                        """, (role_id, perm_id))
        
        conn.commit()
        print("✅ 角色和权限初始化完成")
        return role_ids
        
    except mysql.connector.Error as e:
        conn.rollback()
        print(f"❌ 角色权限初始化失败: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def create_default_users(role_ids):
    """创建默认用户"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("👥 创建默认用户账户...")
        
        for user_config in DEFAULT_USERS:
            username = user_config['username']
            password = user_config['password']
            role_name = user_config['role']
            description = user_config['description']
            
            print(f"   🔧 创建用户: {username}")
            
            # 检查用户是否已存在
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                print(f"   ⚠️  用户 {username} 已存在，更新密码...")
                # 更新现有用户的密码
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                cursor.execute("""
                    UPDATE users 
                    SET password_hash = %s, role_id = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE username = %s
                """, (password_hash, role_ids[role_name], username))
            else:
                # 创建新用户
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                cursor.execute("""
                    INSERT INTO users (username, password_hash, role_id, full_name, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """, (username, password_hash, role_ids[role_name], description, True))
            
            print(f"   ✅ 用户 {username} 配置完成")
        
        conn.commit()
        print("✅ 所有默认用户创建完成")
        
    except mysql.connector.Error as e:
        conn.rollback()
        print(f"❌ 创建用户失败: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def verify_users():
    """验证用户创建结果"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("🔍 验证用户创建结果...")
        
        cursor.execute("""
            SELECT u.username, r.name as role_name, u.is_active, u.created_at
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE u.username IN ('admin', 'dba', 'dev')
            ORDER BY u.username
        """)
        
        users = cursor.fetchall()
        
        if users:
            print("\n📋 用户列表:")
            print("-" * 60)
            print(f"{'用户名':<10} {'角色':<10} {'状态':<10} {'创建时间':<20}")
            print("-" * 60)
            
            for username, role_name, is_active, created_at in users:
                status = "✅ 激活" if is_active else "❌ 禁用"
                print(f"{username:<10} {role_name:<10} {status:<10} {created_at}")
            
            print("-" * 60)
            return True
        else:
            print("❌ 未找到任何用户")
            return False
            
    except mysql.connector.Error as e:
        print(f"❌ 验证用户失败: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def print_login_info():
    """打印登录信息"""
    print("\n🎉 用户初始化完成！")
    print("\n" + "=" * 60)
    print("📝 默认登录账户信息")
    print("=" * 60)
    
    for user_config in DEFAULT_USERS:
        username = user_config['username']
        password = user_config['password'] 
        description = user_config['description']
        print(f"• {description}")
        print(f"  用户名: {username}")
        print(f"  密码:   {password}")
        print()
    
    print("🔒 安全提醒:")
    print("1. 首次登录后请立即修改默认密码")
    print("2. 建议定期更换密码")
    print("3. 不要在生产环境使用默认密码")
    print("\n" + "=" * 60)

def main():
    """主函数"""
    print_banner()
    
    # 测试数据库连接
    if not test_database_connection():
        print("\n❌ 初始化终止：数据库连接失败")
        sys.exit(1)
    
    try:
        # 创建必要的表
        create_tables_if_not_exists()
        
        # 初始化角色和权限
        role_ids = initialize_roles_and_permissions()
        
        # 创建默认用户
        create_default_users(role_ids)
        
        # 验证结果
        if verify_users():
            print_login_info()
        else:
            print("❌ 用户验证失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ 初始化过程中发生错误: {e}")
        print("\n🔧 故障排除建议:")
        print("1. 检查数据库服务是否正常运行")
        print("2. 检查数据库连接配置 (config.py)")
        print("3. 检查数据库用户权限")
        print("4. 查看详细错误信息并联系技术支持")
        sys.exit(1)

if __name__ == '__main__':
    main()
