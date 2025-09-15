"""
性能优化的查询缓存模块
使用内存缓存减少数据库查询
"""
import time
from functools import wraps
from typing import Dict, Any, Optional
import hashlib
import json

class QueryCache:
    def __init__(self, default_timeout: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_timeout = default_timeout
    
    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry['expires']:
                return entry['value']
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """设置缓存值"""
        timeout = timeout or self.default_timeout
        self.cache[key] = {
            'value': value,
            'expires': time.time() + timeout
        }
    
    def clear_expired(self) -> None:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items() 
            if current_time >= entry['expires']
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def cache_result(self, timeout: Optional[int] = None):
        """装饰器：缓存函数结果"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = f"{func.__name__}:{self._generate_key(*args, **kwargs)}"
                
                # 尝试从缓存获取
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # 执行函数并缓存结果
                result = func(*args, **kwargs)
                self.set(cache_key, result, timeout)
                return result
            return wrapper
        return decorator

# 全局缓存实例
query_cache = QueryCache(default_timeout=300)  # 5分钟默认缓存

def cached_query(timeout: int = 300):
    """查询缓存装饰器"""
    return query_cache.cache_result(timeout)

def clear_cache():
    """清理所有缓存"""
    query_cache.cache.clear()

def clear_user_stats_cache():
    """清理用户统计相关缓存"""
    keys_to_remove = [
        key for key in query_cache.cache.keys() 
        if 'get_user_query_stats' in key or 'get_user_detail_stats' in key
    ]
    for key in keys_to_remove:
        del query_cache.cache[key]
