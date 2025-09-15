"""
慢查询系统性能监控工具
实时监控系统性能指标
"""
import time
import psutil
import mysql.connector
from datetime import datetime
import json
import os
from config import DB_CONFIG

class PerformanceMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            'requests_count': 0,
            'avg_response_time': 0.0,
            'error_count': 0,
            'db_connections': 0,
            'memory_usage': 0.0,
            'cpu_usage': 0.0
        }
    
    def log_request(self, response_time: float, success: bool = True):
        """记录请求"""
        self.metrics['requests_count'] += 1
        
        # 计算平均响应时间
        current_avg = self.metrics['avg_response_time']
        count = self.metrics['requests_count']
        self.metrics['avg_response_time'] = (current_avg * (count - 1) + response_time) / count
        
        if not success:
            self.metrics['error_count'] += 1
    
    def check_database_performance(self):
        """检查数据库性能"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # 检查活跃连接数
            cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
            result = cursor.fetchone()
            if result:
                self.metrics['db_connections'] = int(result[1])
            
            # 检查慢查询数量
            cursor.execute("SHOW STATUS LIKE 'Slow_queries'")
            result = cursor.fetchone()
            slow_queries = int(result[1]) if result else 0
            
            # 检查查询缓存命中率
            cursor.execute("SHOW STATUS LIKE 'Qcache_hits'")
            cache_hits = cursor.fetchone()
            cursor.execute("SHOW STATUS LIKE 'Qcache_inserts'")
            cache_inserts = cursor.fetchone()
            
            cache_hit_rate = 0
            if cache_hits and cache_inserts:
                total_queries = int(cache_hits[1]) + int(cache_inserts[1])
                if total_queries > 0:
                    cache_hit_rate = (int(cache_hits[1]) / total_queries) * 100
            
            conn.close()
            
            return {
                'active_connections': self.metrics['db_connections'],
                'slow_queries': slow_queries,
                'cache_hit_rate': round(cache_hit_rate, 2)
            }
            
        except Exception as e:
            print(f"数据库性能检查失败: {e}")
            return None
    
    def check_system_performance(self):
        """检查系统性能"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics['cpu_usage'] = cpu_percent
        
        # 内存使用率
        memory = psutil.virtual_memory()
        self.metrics['memory_usage'] = memory.percent
        
        # 磁盘使用率
        disk = psutil.disk_usage('/')
        disk_usage = (disk.used / disk.total) * 100
        
        return {
            'cpu_usage': cpu_percent,
            'memory_usage': memory.percent,
            'memory_available': memory.available // (1024 * 1024),  # MB
            'disk_usage': round(disk_usage, 2),
            'disk_free': disk.free // (1024 * 1024 * 1024)  # GB
        }
    
    def get_application_metrics(self):
        """获取应用性能指标"""
        uptime = time.time() - self.start_time
        error_rate = (self.metrics['error_count'] / max(self.metrics['requests_count'], 1)) * 100
        
        return {
            'uptime_seconds': round(uptime, 2),
            'total_requests': self.metrics['requests_count'],
            'avg_response_time': round(self.metrics['avg_response_time'], 3),
            'error_rate': round(error_rate, 2),
            'requests_per_second': round(self.metrics['requests_count'] / max(uptime, 1), 2)
        }
    
    def generate_report(self):
        """生成性能报告"""
        timestamp = datetime.now().isoformat()
        
        report = {
            'timestamp': timestamp,
            'application': self.get_application_metrics(),
            'system': self.check_system_performance(),
            'database': self.check_database_performance()
        }
        
        return report
    
    def save_report(self, filepath: str = None):
        """保存性能报告"""
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f'performance_report_{timestamp}.json'
        
        report = self.generate_report()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def print_realtime_stats(self):
        """打印实时统计信息"""
        report = self.generate_report()
        
        print("\n" + "="*60)
        print(f"📊 慢查询系统性能监控 - {report['timestamp']}")
        print("="*60)
        
        # 应用指标
        app = report['application']
        print(f"🚀 应用性能:")
        print(f"   运行时间: {app['uptime_seconds']}秒")
        print(f"   总请求数: {app['total_requests']}")
        print(f"   平均响应时间: {app['avg_response_time']}秒")
        print(f"   错误率: {app['error_rate']}%")
        print(f"   QPS: {app['requests_per_second']}")
        
        # 系统指标
        sys = report['system']
        print(f"\n💻 系统性能:")
        print(f"   CPU使用率: {sys['cpu_usage']}%")
        print(f"   内存使用率: {sys['memory_usage']}%")
        print(f"   可用内存: {sys['memory_available']}MB")
        print(f"   磁盘使用率: {sys['disk_usage']}%")
        print(f"   剩余磁盘: {sys['disk_free']}GB")
        
        # 数据库指标
        if report['database']:
            db = report['database']
            print(f"\n🗄️ 数据库性能:")
            print(f"   活跃连接数: {db['active_connections']}")
            print(f"   慢查询数: {db['slow_queries']}")
            print(f"   缓存命中率: {db['cache_hit_rate']}%")
        
        # 性能警告
        warnings = []
        if sys['cpu_usage'] > 80:
            warnings.append("⚠️ CPU使用率过高")
        if sys['memory_usage'] > 85:
            warnings.append("⚠️ 内存使用率过高")
        if app['error_rate'] > 5:
            warnings.append("⚠️ 错误率过高")
        if app['avg_response_time'] > 2:
            warnings.append("⚠️ 响应时间过长")
        
        if warnings:
            print(f"\n🔔 性能警告:")
            for warning in warnings:
                print(f"   {warning}")
        else:
            print(f"\n✅ 系统运行正常")

# 全局监控实例
performance_monitor = PerformanceMonitor()

# 性能监控装饰器
def monitor_performance(func):
    """性能监控装饰器"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            raise e
        finally:
            end_time = time.time()
            response_time = end_time - start_time
            performance_monitor.log_request(response_time, success)
    
    return wrapper

if __name__ == "__main__":
    # 实时监控模式
    print("🚀 启动慢查询系统性能监控...")
    
    try:
        while True:
            performance_monitor.print_realtime_stats()
            time.sleep(30)  # 每30秒更新一次
    except KeyboardInterrupt:
        print("\n👋 监控已停止")
        
        # 保存最终报告
        report_file = performance_monitor.save_report()
        print(f"📋 性能报告已保存: {report_file}")
