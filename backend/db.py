import mysql.connector
from config import DB_CONFIG, POOL_CONFIG

# 创建连接池
connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    **DB_CONFIG,
    **POOL_CONFIG
)

def get_db():
    return connection_pool.get_connection()
