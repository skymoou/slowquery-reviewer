import os
from dotenv import load_dotenv

# 加载.env文件（如果存在）
load_dotenv()

# JWT配置
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-super-secret-key-2024')
JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '86400'))  # 24小时

# 生产环境警告
if JWT_SECRET_KEY == 'your-super-secret-key-2024':
    import warnings
    warnings.warn(
        "⚠️  警告: 使用默认JWT密钥！生产环境请设置环境变量 JWT_SECRET_KEY",
        UserWarning,
        stacklevel=2
    )

# 数据库配置
DB_CONFIG = {
    "host": os.getenv('DB_HOST', '10.41.0.91'),
    "user": os.getenv('DB_USER', 'root'),
    "password": os.getenv('DB_PASSWORD', 'Wp.stg3'),
    "database": os.getenv('DB_NAME', 'slow_query_analysis'),
}

# 连接池配置 - 优化版本
POOL_CONFIG = {
    "pool_name": "mypool",
    "pool_size": int(os.getenv('DB_POOL_SIZE', '15')),  # 增加连接池大小
    "pool_reset_session": True,
    "autocommit": True,  # 自动提交提高性能
}

# 应用配置
APP_CONFIG = {
    "host": os.getenv('APP_HOST', '0.0.0.0'),  # 改为监听所有网络接口
    "port": int(os.getenv('APP_PORT', '5172')),  # 改为5172端口
    "debug": os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
}

# API配置 - 性能优化版本
API_CONFIG = {
    "DEFAULT_PAGE_SIZE": int(os.getenv('DEFAULT_PAGE_SIZE', '20')),
    "MAX_PAGE_SIZE": int(os.getenv('MAX_PAGE_SIZE', '100')),
    "QUERY_TIMEOUT": int(os.getenv('QUERY_TIMEOUT', '30')),  # 秒
    "CACHE_TIMEOUT": int(os.getenv('CACHE_TIMEOUT', '300')),  # 缓存5分钟
    "ENABLE_QUERY_CACHE": os.getenv('ENABLE_QUERY_CACHE', 'True').lower() == 'true',
}

# 安全配置
SECURITY_CONFIG = {
    "CORS_ORIGINS": os.getenv('CORS_ORIGINS', '*').split(','),
    "MAX_CONTENT_LENGTH": int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
}

# 响应状态码
class StatusCode:
    SUCCESS = 200
    BAD_REQUEST = 400
    NOT_FOUND = 404
    INTERNAL_ERROR = 500

# 响应消息
class Messages:
    QUERY_SUCCESS = "查询成功"
    UPDATE_SUCCESS = "更新成功"
    QUERY_ERROR = "查询失败"
    UPDATE_ERROR = "更新失败"
    INVALID_PARAMS = "无效的参数"
    NOT_FOUND = "未找到相关数据"
