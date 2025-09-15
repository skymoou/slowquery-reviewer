from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import logging
import os
from datetime import datetime
from config import DB_CONFIG, POOL_CONFIG, API_CONFIG, APP_CONFIG, SECURITY_CONFIG, StatusCode, Messages
from utils import api_response, handle_api_error
from routes.auth import auth_bp
from routes.queries import queries_bp
from auth import permission_required
from db import get_db

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置CORS - 禁用HTTPS强制
cors_origins = SECURITY_CONFIG.get('CORS_ORIGINS', ['*'])
if cors_origins == ['*']:
    CORS(app, supports_credentials=True, 
         expose_headers=['Content-Type', 'Authorization'],
         allow_headers=['Content-Type', 'Authorization'])
else:
    CORS(app, origins=cors_origins, supports_credentials=True,
         expose_headers=['Content-Type', 'Authorization'],
         allow_headers=['Content-Type', 'Authorization'])

# 禁用HTTPS强制跳转
app.config['PREFERRED_URL_SCHEME'] = 'http'

# 配置最大内容长度
app.config['MAX_CONTENT_LENGTH'] = SECURITY_CONFIG.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)

# 注册蓝图
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(queries_bp, url_prefix='/api')

def check_tables_exist():
    """检查必要的数据表是否存在 - 缓存结果避免重复查询"""
    if not hasattr(check_tables_exist, 'cached_result'):
        db = None
        cursor = None
        try:
            db = get_db()
            cursor = db.cursor()
            
            # 检查慢查询相关表是否存在
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                AND table_name IN ('slow_query_fingerprint', 'slow_query_detail')
            """)
            count = cursor.fetchone()[0]
            check_tables_exist.cached_result = count == 2
            
            if not check_tables_exist.cached_result:
                logger.error("慢查询相关表不存在，请先运行 init_tables.py 初始化")
        except Exception as e:
            logger.error(f"检查表失败: {str(e)}")
            check_tables_exist.cached_result = False
        finally:
            if cursor:
                cursor.close()
            if db:
                db.close()
    
    return check_tables_exist.cached_result

@app.route('/api/comments', methods=['PUT'])
@permission_required('OPTIMIZATION_EDIT')
def update_comments():
    """更新评论和状态 - 优化版本"""
    data = request.json
    if not data or 'checksum' not in data or 'comments' not in data:
        return api_response(success=False, message="请求参数不完整")
    
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor()
        
        comments = data.get('comments', '')
        reviewed_status = data.get('reviewed_status', '待优化')
        
        # 验证状态
        valid_statuses = [
            '待优化', '已加索引优化', '已自主添加索引优化', '周期性跑批', 
            'SQL已最优', '需研发修改SQL~SQL改写', '需研发修改SQL~隐式转换',
            '放弃-1.全表扫描', '放弃-2.全表聚合', '放弃-3.扫描行数超40W',
            '放弃-模糊查询', '放弃-模糊查询+or查询', '放弃-分页查询', '放弃-or查询'
        ]
        
        if reviewed_status not in valid_statuses:
            return api_response(success=False, message=f"无效的状态值: {reviewed_status}")
        
        # 更新记录
        update_sql = '''UPDATE slow_query_fingerprint 
                       SET comments = %s, reviewed_status = %s
                       WHERE checksum = %s'''
        
        cursor.execute(update_sql, (comments, reviewed_status, data['checksum']))
        
        if cursor.rowcount == 0:
            return api_response(success=False, message="未找到相关记录或更新失败")
        
        db.commit()
        return api_response(success=True, message=f"更新成功，状态已更新为{reviewed_status}")
        
    except Exception as e:
        logger.error(f"更新评论失败: {str(e)}")
        if db:
            db.rollback()
        return api_response(success=False, message=f"操作失败: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()



@app.route('/api/health')
def health_check():
    """健康检查接口"""
    return api_response(
        success=True,
        message="服务正常运行",
        data={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    )

@app.route('/')
def index():
    """根路径重定向到前端页面"""
    # 使用绝对路径确保路径正确
    frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist'))
    index_file = os.path.join(frontend_path, 'index.html')
    
    # 调试信息
    logger.debug(f"Frontend path: {frontend_path}")
    logger.debug(f"Index file path: {index_file}")
    logger.debug(f"Index file exists: {os.path.exists(index_file)}")
    
    if os.path.exists(index_file):
        return send_from_directory(frontend_path, 'index.html')
    else:
        return jsonify({
            "message": "慢查询分析系统后端API",
            "api_docs": "/api/health",
            "version": "1.0.0",
            "frontend": f"前端文件未找到，路径: {frontend_path}",
            "debug": {
                "frontend_path": frontend_path,
                "index_exists": os.path.exists(index_file),
                "current_dir": os.getcwd()
            }
        })

@app.route('/<path:path>')
def serve_static(path):
    """提供前端静态文件 - 优化版本"""
    # 使用绝对路径确保路径正确
    frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist'))
    
    # 检查文件是否存在
    file_path = os.path.join(frontend_path, path)
    logger.debug(f"Serving static file: {path}, full path: {file_path}")
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        response = send_from_directory(frontend_path, path)
        
        # 添加缓存头以提高加载速度
        if path.endswith(('.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2', '.ttf', '.eot')):
            response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1年缓存
            response.headers['Expires'] = 'Thu, 31 Dec 2025 23:59:59 GMT'
        elif path.endswith('.html'):
            response.headers['Cache-Control'] = 'public, max-age=3600'  # 1小时缓存
        
        # 启用压缩
        if path.endswith(('.js', '.css', '.html', '.json')):
            response.headers['Content-Encoding'] = 'gzip'
            
        return response
    
    # 如果文件不存在且不是API路径，返回index.html (SPA路由)
    if not path.startswith('api/'):
        index_file = os.path.join(frontend_path, 'index.html')
        if os.path.exists(index_file):
            response = send_from_directory(frontend_path, 'index.html')
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response
    
    # API路径或其他情况返回404
    return jsonify({"error": "Not Found", "path": path}), 404

if __name__ == '__main__':
    # 获取应用配置
    host = APP_CONFIG.get('host', '127.0.0.1')
    port = APP_CONFIG.get('port', 5000)
    debug = APP_CONFIG.get('debug', True)
    
    logger.info(f"Starting application on {host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug)