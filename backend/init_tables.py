import mysql.connector
from config import DB_CONFIG

def init_tables():
    """初始化慢查询相关表"""
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    try:
        # 创建慢查询指纹表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS slow_query_fingerprint (
                id INT AUTO_INCREMENT PRIMARY KEY,
                checksum VARCHAR(32) NOT NULL UNIQUE,
                normalized_sql TEXT NOT NULL,
                raw_sql TEXT,
                username VARCHAR(100),
                dbname VARCHAR(100),
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                comments TEXT,
                reviewed_status VARCHAR(50) DEFAULT '待优化',
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_checksum (checksum),
                INDEX idx_username (username),
                INDEX idx_dbname (dbname),
                INDEX idx_last_seen (last_seen)
            )
        """)
        
        # 创建慢查询详情表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS slow_query_detail (
                id INT AUTO_INCREMENT PRIMARY KEY,
                checksum VARCHAR(32) NOT NULL,
                sql_text TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                query_time FLOAT NOT NULL,
                lock_time FLOAT,
                rows_sent INT,
                rows_examined INT,
                rows_affected INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_checksum (checksum),
                INDEX idx_timestamp (timestamp),
                FOREIGN KEY (checksum) REFERENCES slow_query_fingerprint(checksum) ON DELETE CASCADE
            )
        """)
        
        connection.commit()
        print("数据表初始化成功！")
        
    except Exception as e:
        connection.rollback()
        print(f"初始化失败，错误详情:")
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
    init_tables()
