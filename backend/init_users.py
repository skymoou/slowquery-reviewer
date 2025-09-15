import mysql.connector
from config import DB_CONFIG
import bcrypt
from datetime import datetime

def create_roles_and_permissions():
    """创建角色和权限表"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # 创建角色表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建权限表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建角色-权限关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id INT,
                permission_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (role_id, permission_id),
                FOREIGN KEY (role_id) REFERENCES roles(id),
                FOREIGN KEY (permission_id) REFERENCES permissions(id)
            )
        """)
        
        # 创建用户表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES roles(id)
            )
        """)
        
        # 插入基本权限
        permissions = [
            ('SLOW_QUERY_VIEW', '查看慢查询列表和详情'),
            ('SLOW_QUERY_EXPORT', '导出慢查询数据'),
            ('OPTIMIZATION_EDIT', '编辑优化建议和状态'),
            ('USER_MANAGE', '用户管理'),
            ('SYSTEM_MANAGE', '系统管理')
        ]
        
        for name, description in permissions:
            cursor.execute("""
                INSERT IGNORE INTO permissions (name, description) 
                VALUES (%s, %s)
            """, (name, description))
        
        # 插入角色
        roles = [
            ('dev', '开发人员'),
            ('dba', '数据库管理员'),
            ('admin', '系统管理员')
        ]
        
        for name, description in roles:
            cursor.execute("""
                INSERT IGNORE INTO roles (name, description) 
                VALUES (%s, %s)
            """, (name, description))
        
        # 设置角色权限
        # 获取角色ID
        cursor.execute("SELECT id, name FROM roles")
        role_ids = {row[1]: row[0] for row in cursor.fetchall()}
        
        # 获取权限ID
        cursor.execute("SELECT id, name FROM permissions")
        perm_ids = {row[1]: row[0] for row in cursor.fetchall()}
        
        # 设置权限映射
        role_permissions = {
            'dev': ['SLOW_QUERY_VIEW'],
            'dba': ['SLOW_QUERY_VIEW', 'SLOW_QUERY_EXPORT', 'OPTIMIZATION_EDIT'],
            'admin': ['SLOW_QUERY_VIEW', 'SLOW_QUERY_EXPORT', 'OPTIMIZATION_EDIT', 'USER_MANAGE', 'SYSTEM_MANAGE']
        }
        
        # 插入角色-权限关联
        for role, perms in role_permissions.items():
            role_id = role_ids[role]
            for perm in perms:
                perm_id = perm_ids[perm]
                cursor.execute("""
                    INSERT IGNORE INTO role_permissions (role_id, permission_id)
                    VALUES (%s, %s)
                """, (role_id, perm_id))
        
        # 提交事务
        conn.commit()
        print("角色和权限初始化成功！")
        
        return role_ids
        
    except Exception as e:
        conn.rollback()
        print(f"初始化失败: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def create_user(username, password, role_name):
    """创建用户"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # 获取角色ID
        cursor.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
        role_id = cursor.fetchone()
        
        if not role_id:
            raise ValueError(f"角色 {role_name} 不存在")
            
        # 生成密码哈希
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # 创建用户
        cursor.execute("""
            INSERT INTO users (username, password_hash, role_id)
            VALUES (%s, %s, %s)
        """, (username, password_hash, role_id[0]))
        
        conn.commit()
        print(f"用户 {username} 创建成功！")
        
    except Exception as e:
        conn.rollback()
        print(f"创建用户失败: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def main():
    try:
        # 初始化角色和权限
        print("开始初始化角色和权限...")
        create_roles_and_permissions()
        
        # 创建管理员账号
        print("\n创建管理员账号...")
        create_user('admin', 'Admin@123', 'admin')
        
        # 创建DBA账号
        print("\n创建DBA账号...")
        create_user('dba', 'Dba@123', 'dba')
        
        # 创建开发账号
        print("\n创建开发账号...")
        create_user('dev', 'Dev@123', 'dev')
        
        print("\n账号创建完成！")
        print("管理员账号 - 用户名：admin，密码：Admin@123")
        print("DBA账号 - 用户名：dba，密码：Dba@123")
        print("开发账号 - 用户名：dev，密码：Dev@123")
        
    except Exception as e:
        print(f"操作失败: {str(e)}")

if __name__ == '__main__':
    main()
