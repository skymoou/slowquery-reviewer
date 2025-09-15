import mysql.connector
from config import DB_CONFIG

def check_status():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT checksum, normalized_sql, reviewed_status FROM slow_query_fingerprint')
    results = cursor.fetchall()
    
    print('当前SQL优化状态：')
    for row in results:
        print(f'\nChecksum: {row["checksum"]}')
        print(f'SQL: {row["normalized_sql"][:100]}...')
        print(f'状态: {row["reviewed_status"]}')
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    check_status()
