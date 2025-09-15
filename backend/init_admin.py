from auth import hash_password
import mysql.connector
from config import DB_CONFIG

def init_admin():
    """初始化管理员用户"""
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    try:
        # 检查users表是否存在
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                status TINYINT(1) DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # 创建roles表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                code VARCHAR(50) NOT NULL UNIQUE,
                description VARCHAR(200),
                status TINYINT(1) DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # 创建user_roles表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                role_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_role (user_id, role_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
            )
        """)
        
        # 创建permissions表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                code VARCHAR(50) NOT NULL UNIQUE,
                description VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建role_permissions表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                role_id INT NOT NULL,
                permission_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_role_permission (role_id, permission_id),
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            )
        """)
        
        # 插入管理员用户
        admin_password = hash_password('admin')
        cursor.execute("""
            INSERT INTO users (username, password, email) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE password = VALUES(password)
        """, ('admin', admin_password, 'admin@example.com'))
        
        # 插入角色
        cursor.execute("""
            INSERT INTO roles (name, code, description) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                name = VALUES(name),
                description = VALUES(description)
        """, ('系统管理员', 'ADMIN', '系统管理员，拥有所有权限'))
        
        # 插入权限
        permissions = [
            ('用户管理', 'USER_MANAGE', '用户的增删改查权限'),
            ('角色管理', 'ROLE_MANAGE', '角色的增删改查权限'),
            ('查看慢查询', 'SLOW_QUERY_VIEW', '查看慢查询列表和详情'),
            ('编辑优化建议', 'OPTIMIZATION_EDIT', '编辑慢查询的优化建议和状态')
        ]
        
        for perm in permissions:
            cursor.execute("""
                INSERT INTO permissions (name, code, description)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    name = VALUES(name),
                    description = VALUES(description)
            """, perm)
        
        # 获取admin用户ID和角色ID
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM roles WHERE code = 'ADMIN'")
        admin_role_id = cursor.fetchone()[0]
        
        # 关联用户和角色
        cursor.execute("""
            INSERT INTO user_roles (user_id, role_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE user_id = VALUES(user_id)
        """, (admin_id, admin_role_id))
        
        # 获取所有权限ID
        cursor.execute("SELECT id FROM permissions")
        permission_ids = [row[0] for row in cursor.fetchall()]
        
        # 给管理员角色分配所有权限
        for perm_id in permission_ids:
            cursor.execute("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE role_id = VALUES(role_id)
            """, (admin_role_id, perm_id))
        
        connection.commit()
        print("管理员用户初始化成功！")
        print(f"用户名: admin")
        print(f"密码: admin")
        print(f"密码哈希: {admin_password}")
        
    except Exception as e:
        connection.rollback()
        print(f"初始化失败: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()

if __name__ == '__main__':
    init_admin()
