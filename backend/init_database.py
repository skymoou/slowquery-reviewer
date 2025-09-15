import mysql.connector
from config import DB_CONFIG

def init_database():
    """初始化数据库"""
    # 创建一个没有指定数据库的配置
    config = DB_CONFIG.copy()
    database = config.pop('database')
    
    connection = mysql.connector.connect(**config)
    cursor = connection.cursor()
    
    try:
        # 创建数据库
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
        print(f"数据库 {database} 创建成功！")
        
    except Exception as e:
        print(f"初始化数据库失败:")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        import traceback
        print("详细堆栈:")
        print(traceback.format_exc())
        raise
    finally:
        cursor.close()
        connection.close()

if __name__ == '__main__':
    init_database()
