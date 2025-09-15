# 服务器端配置文件
# 请根据实际环境修改数据库连接信息

DB_CONFIG = {
    'host': 'localhost',      # 数据库服务器地址，如果数据库在同一台服务器上则为localhost
    'port': 3306,            # MySQL端口，默认3306
    'user': 'root',          # 数据库用户名
    'password': 'your_password_here',  # 数据库密码
    'database': 'slow_query_db',       # 慢查询数据库名
    'charset': 'utf8mb4',
    'autocommit': False,
    'connect_timeout': 60,
    'read_timeout': 60,
    'write_timeout': 60,
    'cursorclass': None      # PyMySQL 默认游标类型
}

# 慢日志文件路径（可选，也可以通过命令行参数指定）
SLOW_LOG_PATH = "/data/mysql/log/slow.log"

# 解析配置
PARSE_CONFIG = {
    'days_back': 7,          # 解析最近几天的日志
    'max_sql_length': 5000,  # SQL语句最大长度
    'batch_size': 1000,      # 批量插入大小
}
