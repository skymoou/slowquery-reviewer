from flask import Blueprint, request
from auth import permission_required
from utils import api_response, handle_api_error
import logging
from db import get_db
from cache import cached_query, clear_user_stats_cache
from config import API_CONFIG

logger = logging.getLogger(__name__)

queries_bp = Blueprint('queries', __name__)

@queries_bp.route('/queries')
@permission_required('SLOW_QUERY_VIEW')
@handle_api_error("QUERY_ERROR")
def get_slow_queries():
    """获取慢查询列表"""
    db = None
    cursor = None
    count_cursor = None
    
    try:
        logger.debug("开始获取慢查询列表")
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # 构建查询条件
        conditions = []
        params = []
        
        # 处理时间过滤
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        if start_time and end_time:
            conditions.append("f.updated_at BETWEEN %s AND %s")
            params.extend([start_time, end_time])
        
        # 处理用户名过滤
        username = request.args.get('username')
        if username:
            conditions.append("username = %s")
            params.append(username)
        
        # 处理数据库名过滤
        dbname = request.args.get('dbname')
        if dbname:
            conditions.append("dbname = %s")
            params.append(dbname)
        
        # 构建基础查询
        base_query = '''
            SELECT SQL_CALC_FOUND_ROWS
                f.id,
                f.checksum,
                f.normalized_sql,
                f.raw_sql,
                f.username,
                f.dbname,
                f.comments,
                f.reviewed_status,
                f.first_seen,
                COALESCE(d.last_seen, f.last_seen) as last_occurrence,
                COALESCE(d.total_occurrences, 0) as total_occurrences,
                d.avg_query_time,
                d.total_rows_examined,
                d.total_rows_sent
            FROM slow_query_fingerprint f
            LEFT JOIN (
                SELECT 
                    checksum,
                    COUNT(*) as total_occurrences,
                    MAX(timestamp) as last_seen,
                    AVG(query_time) as avg_query_time,
                    SUM(rows_examined) as total_rows_examined,
                    SUM(rows_sent) as total_rows_sent
                FROM slow_query_detail
                GROUP BY checksum
            ) d ON f.checksum = d.checksum
            WHERE 1=1
        '''
        
        # 添加条件
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        # 添加分页 - 性能优化版本
        per_page = min(int(request.args.get('per_page', API_CONFIG['DEFAULT_PAGE_SIZE'])), 
                      API_CONFIG['MAX_PAGE_SIZE'])
        page = int(request.args.get('page', 1))
        offset = (page - 1) * per_page
        
        # 按执行次数倒序排序，如果有过滤条件则优先按执行次数排序
        if username or dbname:
            base_query += " ORDER BY total_occurrences DESC, last_occurrence DESC LIMIT %s OFFSET %s"
        else:
            base_query += " ORDER BY last_occurrence DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        # 执行查询
        cursor.execute(base_query, params)
        data = cursor.fetchall()
        
        # 获取总数
        count_cursor = db.cursor()
        count_cursor.execute("SELECT FOUND_ROWS()")
        total = count_cursor.fetchone()[0]
        
        logger.info(f"成功获取慢查询列表，共 {total} 条记录")
        return api_response(
            success=True,
            message="查询成功",
            data={'data': data, 'total': total}
        )
        
    except Exception as e:
        logger.error(f"获取慢查询列表失败: {str(e)}", exc_info=True)
        return api_response(
            success=False,
            message=f"获取慢查询列表失败: {str(e)}",
            status_code=500
        )
    finally:
        if cursor:
            cursor.close()
        if count_cursor:
            count_cursor.close()
        if db:
            db.close()

@queries_bp.route('/queries/<checksum>')
@permission_required('SLOW_QUERY_VIEW')
@handle_api_error("QUERY_DETAIL_ERROR")
def get_query_details(checksum):
    """获取慢查询详情，包括趋势数据"""
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # 获取基本信息和最新的优化建议
        detail_query = """
            SELECT 
                f.checksum,
                f.normalized_sql,
                d.sql_text,
                f.username,
                f.dbname,
                d.timestamp,
                d.query_time,
                d.rows_examined,
                d.rows_sent,
                f.reviewed_status,
                f.comments
            FROM slow_query_fingerprint f
            LEFT JOIN slow_query_detail d ON f.checksum = d.checksum
            WHERE f.checksum = %s
            ORDER BY d.timestamp DESC
            LIMIT 1
        """
        cursor.execute(detail_query, (checksum,))
        details = cursor.fetchall()
        
        if not details:
            return api_response(
                success=False,
                message="查询不存在",
                status_code=404
            )
            
        # 获取趋势数据（最近30天）
        trend_query = """
            SELECT 
                DATE(timestamp) as date,
                AVG(query_time) as query_time,
                COUNT(*) as occurrences,
                AVG(rows_examined) as rows_examined,
                AVG(rows_sent) as rows_sent
            FROM slow_query_detail
            WHERE checksum = %s
                AND timestamp >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
            GROUP BY DATE(timestamp)
            ORDER BY date ASC
        """
        cursor.execute(trend_query, (checksum,))
        trend = cursor.fetchall()
        
        return api_response(
            success=True,
            message="查询成功",
            data={
                'details': details,
                'trend': trend
            }
        )
        
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

@queries_bp.route('/queries/<checksum>/review', methods=['POST'])
@permission_required('OPTIMIZATION_EDIT')
@handle_api_error("UPDATE_REVIEW_ERROR")
def update_query_review(checksum):
    """更新查询的优化建议和状态"""
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor()
        
        data = request.get_json()
        comments = data.get('comments', '')
        reviewed_status = data.get('reviewed_status', '')
        
        # 更新慢查询指纹表
        update_query = """
            UPDATE slow_query_fingerprint
            SET comments = %s,
                reviewed_status = %s,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE checksum = %s
        """
        cursor.execute(update_query, (comments, reviewed_status, checksum))
        db.commit()
        
        return api_response(
            success=True,
            message="更新成功"
        )
        
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

@queries_bp.route('/queries/stats/by-user')
@permission_required('SLOW_QUERY_VIEW')
@handle_api_error("STATS_ERROR")
@cached_query(timeout=300)  # 缓存5分钟
def get_user_query_stats():
    """获取按用户统计的慢查询次数 - 性能优化版本"""
    db = None
    cursor = None
    
    try:
        logger.debug("开始获取用户慢查询统计")
        
        # 清除缓存以确保获取最新数据
        clear_user_stats_cache()
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # 构建查询条件
        conditions = []
        params = []
        
        # 处理时间过滤
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        time_condition = ""
        if start_time and end_time:
            time_condition = " AND d.timestamp BETWEEN %s AND %s"
            params.extend([start_time, end_time])
        
        # 构建优化的统计查询，包含所有查询（含已优化）
        stats_query = f'''
            SELECT 
                f.username,
                COUNT(DISTINCT f.id) as unique_queries,
                COUNT(d.id) as total_occurrences,
                ROUND(AVG(d.query_time), 4) as avg_query_time,
                MAX(d.timestamp) as last_query_time,
                MIN(d.timestamp) as first_query_time
            FROM slow_query_fingerprint f
            INNER JOIN slow_query_detail d ON f.checksum = d.checksum
            WHERE f.username IS NOT NULL 
                AND f.username != '' and f.reviewed_status = '待优化'
                {time_condition}
            GROUP BY f.username
            HAVING unique_queries > 0
            ORDER BY total_occurrences DESC, avg_query_time DESC
        '''
        
        logger.debug(f"执行统计查询: {stats_query} 参数: {params}")
        cursor.execute(stats_query, params)
        user_stats = cursor.fetchall()
        
        # 获取总体统计
        total_query = f'''
            SELECT 
                COUNT(DISTINCT f.id) as total_unique_queries,
                COUNT(d.id) as total_occurrences,
                COUNT(DISTINCT f.username) as total_users
            FROM slow_query_fingerprint f
            INNER JOIN slow_query_detail d ON f.checksum = d.checksum
            WHERE f.username IS NOT NULL 
                AND f.username != ''
                {time_condition}
        '''
        
        cursor.execute(total_query, params)
        total_stats = cursor.fetchone()
        
        logger.info(f"成功获取用户慢查询统计，共 {len(user_stats)} 个用户")
        return api_response(
            success=True,
            message="统计查询成功",
            data={
                'user_stats': user_stats,
                'total_stats': total_stats,
                'time_range': {
                    'start_time': start_time,
                    'end_time': end_time
                }
            }
        )
        
    except Exception as e:
        logger.error(f"获取用户慢查询统计失败: {str(e)}", exc_info=True)
        return api_response(
            success=False,
            message=f"获取用户慢查询统计失败: {str(e)}",
            status_code=500
        )
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

@queries_bp.route('/queries/stats/by-user/<username>')
@permission_required('SLOW_QUERY_VIEW')
@handle_api_error("USER_DETAIL_STATS_ERROR")
def get_user_detail_stats(username):
    """获取指定用户的详细慢查询统计"""
    db = None
    cursor = None
    
    try:
        logger.debug(f"开始获取用户 {username} 的详细慢查询统计")
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # 构建查询条件
        conditions = ["f.username = %s"]
        params = [username]
        
        # 处理时间过滤
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        if start_time and end_time:
            conditions.append("d.timestamp BETWEEN %s AND %s")
            params.extend([start_time, end_time])
        
        # 包含所有查询（含已优化）
        where_clause = " AND ".join(conditions)
        
        # 获取用户的详细查询列表
        detail_query = f'''
            SELECT 
                f.id,
                f.checksum,
                f.normalized_sql,
                f.dbname,
                f.reviewed_status,
                f.first_seen,
                f.last_seen,
                COUNT(d.id) as occurrences,
                AVG(d.query_time) as avg_query_time,
                MAX(d.query_time) as max_query_time,
                MIN(d.query_time) as min_query_time,
                MAX(d.timestamp) as last_occurrence,
                SUM(d.rows_examined) as total_rows_examined,
                SUM(d.rows_sent) as total_rows_sent
            FROM slow_query_fingerprint f
            INNER JOIN slow_query_detail d ON f.checksum = d.checksum
            WHERE {where_clause}
            GROUP BY f.id, f.checksum, f.normalized_sql, f.dbname, f.reviewed_status, f.first_seen, f.last_seen
            ORDER BY occurrences DESC, avg_query_time DESC
        '''
        
        cursor.execute(detail_query, params)
        user_queries = cursor.fetchall()
        
        # 获取时间分布统计
        time_distribution_query = f'''
            SELECT 
                DATE(d.timestamp) as query_date,
                COUNT(d.id) as daily_count,
                AVG(d.query_time) as avg_daily_time
            FROM slow_query_fingerprint f
            INNER JOIN slow_query_detail d ON f.checksum = d.checksum
            WHERE {where_clause}
            GROUP BY DATE(d.timestamp)
            ORDER BY query_date DESC
            LIMIT 30
        '''
        
        cursor.execute(time_distribution_query, params)
        time_distribution = cursor.fetchall()
        
        # 获取数据库分布统计
        db_distribution_query = f'''
            SELECT 
                f.dbname,
                COUNT(DISTINCT f.id) as unique_queries,
                COUNT(d.id) as total_occurrences,
                AVG(d.query_time) as avg_query_time
            FROM slow_query_fingerprint f
            INNER JOIN slow_query_detail d ON f.checksum = d.checksum
            WHERE {where_clause}
            GROUP BY f.dbname
            ORDER BY total_occurrences DESC
        '''
        
        cursor.execute(db_distribution_query, params)
        db_distribution = cursor.fetchall()
        
        logger.info(f"成功获取用户 {username} 的详细统计，共 {len(user_queries)} 个查询")
        return api_response(
            success=True,
            message="用户详细统计查询成功",
            data={
                'username': username,
                'queries': user_queries,
                'time_distribution': time_distribution,
                'db_distribution': db_distribution,
                'time_range': {
                    'start_time': start_time,
                    'end_time': end_time
                }
            }
        )
        
    except Exception as e:
        logger.error(f"获取用户 {username} 详细统计失败: {str(e)}", exc_info=True)
        return api_response(
            success=False,
            message=f"获取用户详细统计失败: {str(e)}",
            status_code=500
        )
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()
