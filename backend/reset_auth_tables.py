import mysql.connector
from config import DB_CONFIG
import bcrypt

def reset_auth_tables():
    """删除认证相关表"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # 删除表（注意顺序，因为有外键约束）
        cursor.execute("DROP TABLE IF EXISTS role_permissions")
        cursor.execute("DROP TABLE IF EXISTS user_roles")
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS permissions")
        cursor.execute("DROP TABLE IF EXISTS roles")
        
        conn.commit()
        print("认证相关表删除成功")
        
    except Exception as e:
        conn.rollback()
        print(f"删除表失败: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    reset_auth_tables()
