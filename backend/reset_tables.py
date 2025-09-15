import mysql.connector
from config import DB_CONFIG

def reset_tables():
    """删除并重新创建数据库表"""
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    try:
        # 删除表（注意顺序，因为有外键约束）
        cursor.execute("DROP TABLE IF EXISTS slow_query_detail")
        cursor.execute("DROP TABLE IF EXISTS slow_query_fingerprint")
        connection.commit()
        print("旧表删除成功")
        
    except Exception as e:
        connection.rollback()
        print(f"删除表失败: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()

if __name__ == '__main__':
    reset_tables()
