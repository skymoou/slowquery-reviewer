import mysql.connector
from config import DB_CONFIG

def reset_status():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # 更新所有非标准状态为"待优化"
        cursor.execute('''
            UPDATE slow_query_fingerprint 
            SET reviewed_status = '待优化'
            WHERE reviewed_status NOT IN ('待优化', '已优化', '忽略')
        ''')
        
        conn.commit()
        print("已更新状态")
        
        # 检查更新后的状态
        cursor.execute('''
            SELECT reviewed_status, COUNT(*) as count 
            FROM slow_query_fingerprint 
            GROUP BY reviewed_status
        ''')
        
        print("\n当前状态统计：")
        for status, count in cursor.fetchall():
            print(f"{status}: {count}条")
            
    except Exception as e:
        conn.rollback()
        print(f"更新失败: {str(e)}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    reset_status()
