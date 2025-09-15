#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
服务器端慢日志解析脚本
直接在MySQL服务器上解析慢日志并导入到数据库
适用于在10.41.0.91服务器上执行
兼容Python 2.7
"""

from __future__ import print_function
from __future__ import unicode_literals
import re
import hashlib
import pymysql
from datetime import datetime, timedelta
import sys
import os
import codecs

# Python 2/3 兼容性处理
try:
    input = raw_input  # Python 2
except NameError:
    pass  # Python 3

# 尝试导入配置文件，如果不存在则使用默认配置
try:
    from server_config import DB_CONFIG, SLOW_LOG_PATH, PARSE_CONFIG
except ImportError:
    print("警告: 未找到server_config.py配置文件，使用默认配置")
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': 'your_db_password',  # 需要修改
        'database': 'slow_query_db',
        'charset': 'utf8mb4',
        'autocommit': False
    }
    SLOW_LOG_PATH = "/data/mysql/log/slow.log"
    PARSE_CONFIG = {
        'days_back': 7,
        'max_sql_length': 5000,
        'batch_size': 1000,
        'min_query_time': 5.0  # 最小查询时间（秒）
    }

class SlowLogParser:
    def __init__(self, min_query_time=5.0):
        self.fingerprints = {}
        self.details = []
        self.debug_mode = False  # 添加调试模式标志
        self.min_query_time = min_query_time  # 最小查询时间阈值
        self.stats = {
            'total_entries': 0,
            'parsed_entries': 0,
            'unique_fingerprints': 0,
            'date_range': {'start': None, 'end': None}
        }
    
    def normalize_sql(self, sql):
        """规范化SQL语句，生成指纹"""
        # 移除注释
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        sql = re.sub(r'--.*?\n', '\n', sql)
        
        # 移除多余空白
        sql = re.sub(r'\s+', ' ', sql).strip()
        
        # 替换数字和字符串为占位符
        sql = re.sub(r'\b\d+\b', '?', sql)
        sql = re.sub(r"'[^']*'", "'?'", sql)
        sql = re.sub(r'"[^"]*"', '"?"', sql)
        
        # 替换IN子句中的多个值
        sql = re.sub(r'IN\s*\([^)]+\)', 'IN (?)', sql, flags=re.IGNORECASE)
        
        # 标准化ORDER BY
        sql = re.sub(r'ORDER\s+BY\s+[^;]+', 'ORDER BY ?', sql, flags=re.IGNORECASE)
        
        # 标准化LIMIT
        sql = re.sub(r'LIMIT\s+\d+(?:\s*,\s*\d+)?', 'LIMIT ?', sql, flags=re.IGNORECASE)
        
        return sql.upper().strip()
    
    def generate_checksum(self, normalized_sql):
        """生成SQL指纹的校验和"""
        # Python 2.7兼容的编码处理
        try:
            # Python 2
            if isinstance(normalized_sql, unicode):
                normalized_sql = normalized_sql.encode('utf-8')
        except NameError:
            # Python 3
            if isinstance(normalized_sql, str):
                normalized_sql = normalized_sql.encode('utf-8')
        return hashlib.md5(normalized_sql).hexdigest()
    
    def parse_slow_log(self, log_file_path, days_back=None):
        """解析慢日志文件"""
        if days_back is None:
            days_back = PARSE_CONFIG.get('days_back', 7)
            
        # 计算起始时间
        start_time = datetime.now() - timedelta(days=days_back)
        print("解析最近{}天的慢查询（从 {} 开始）".format(days_back, start_time.strftime('%Y-%m-%d %H:%M:%S')))
        
        if not os.path.exists(log_file_path):
            raise IOError("慢日志文件不存在: {}".format(log_file_path))
        
        file_size = os.path.getsize(log_file_path)
        print("慢日志文件大小: {:.2f} MB".format(file_size / (1024*1024)))
        
        # 显示文件样本
        self._show_log_sample(log_file_path)
        
        if file_size > 500 * 1024 * 1024:  # 超过500MB的大文件
            print("检测到大文件，使用流式读取模式...")
            self._parse_large_file(log_file_path, start_time)
        else:
            print("使用标准读取模式...")
            self._parse_small_file(log_file_path, start_time)
        
        self.stats['unique_fingerprints'] = len(self.fingerprints)
        
        print("\n解析完成统计:")
        print("  总日志条目: {}".format(self.stats['total_entries']))
        print("  成功解析: {}".format(self.stats['parsed_entries']))
        print("  唯一SQL指纹: {}".format(self.stats['unique_fingerprints']))
        print("  详细执行记录: {}".format(len(self.details)))
    def parse_slow_log_with_time_range(self, log_file_path, start_time, end_time):
        """使用指定时间范围解析慢日志文件"""
        print("解析时间范围: {} 到 {}".format(start_time.strftime('%Y-%m-%d %H:%M:%S'), end_time.strftime('%Y-%m-%d %H:%M:%S')))
        
        if not os.path.exists(log_file_path):
            raise IOError("慢日志文件不存在: {}".format(log_file_path))
        
        file_size = os.path.getsize(log_file_path)
        print("慢日志文件大小: {:.2f} MB".format(file_size / (1024*1024)))
        
        # 显示文件样本
        self._show_log_sample(log_file_path)
        
        if file_size > 500 * 1024 * 1024:  # 超过500MB的大文件
            print("检测到大文件，使用流式读取模式...")
            self._parse_large_file_with_range(log_file_path, start_time, end_time)
        else:
            print("使用标准读取模式...")
            self._parse_small_file_with_range(log_file_path, start_time, end_time)
        
        self.stats['unique_fingerprints'] = len(self.fingerprints)
        
        print("\n解析完成统计:")
        print("  总日志条目: {}".format(self.stats['total_entries']))
        print("  成功解析: {}".format(self.stats['parsed_entries']))
        print("  唯一SQL指纹: {}".format(self.stats['unique_fingerprints']))
        print("  详细执行记录: {}".format(len(self.details)))
        if self.stats['date_range']['start'] and self.stats['date_range']['end']:
            print("  时间范围: {} 到 {}".format(self.stats['date_range']['start'], self.stats['date_range']['end']))

    def _parse_small_file_with_range(self, log_file_path, start_time, end_time):
        """使用时间范围解析小文件（一次性读取）"""
        with codecs.open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()
        
        # 分割日志条目 - MySQL慢日志以 "# Time:" 开始每个条目
        entries = re.split(r'# Time: ', log_content)
        self.stats['total_entries'] = len(entries) - 1  # 排除第一个空条目
        
        print("找到 {} 个日志条目，开始解析...".format(self.stats['total_entries']))
        
        processed = 0
        for i, entry in enumerate(entries[1:], 1):  # 排除第一个空条目
            if i % 1000 == 0:
                print("已处理 {}/{} 个条目...".format(i, self.stats['total_entries']))
            
            try:
                if self._parse_entry_with_range(entry, start_time, end_time):
                    processed += 1
            except Exception as e:
                if self.debug_mode:
                    print("解析第{}个条目时出错: {}".format(i, e))
                continue
        
        self.stats['parsed_entries'] = processed

    def _parse_large_file_with_range(self, log_file_path, start_time, end_time):
        """使用时间范围解析大文件（流式读取）"""
        buffer = ""
        entry_count = 0
        processed = 0
        
        print("开始流式解析大文件...")
        
        with codecs.open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            while True:
                chunk = f.read(1024 * 1024)  # 每次读取1MB
                if not chunk:
                    break
                    
                buffer += chunk
                
                # 查找完整的日志条目
                while '# Time: ' in buffer:
                    if entry_count == 0:
                        # 第一个条目可能不完整，跳过到第一个完整条目
                        first_time_pos = buffer.find('# Time: ')
                        if first_time_pos > 0:
                            buffer = buffer[first_time_pos:]
                    
                    # 查找下一个条目的开始位置
                    next_time_pos = buffer.find('# Time: ', 8)  # 跳过当前的"# Time: "
                    
                    if next_time_pos == -1:
                        # 没有找到下一个条目，需要读取更多数据
                        break
                    
                    # 提取当前条目
                    entry = buffer[8:next_time_pos]  # 跳过"# Time: "
                    buffer = buffer[next_time_pos:]
                    
                    entry_count += 1
                    
                    if entry_count % 1000 == 0:
                        print("已处理 {} 个条目...".format(entry_count))
                    
                    try:
                        if self._parse_entry_with_range(entry, start_time, end_time):
                            processed += 1
                    except Exception as e:
                        if self.debug_mode:
                            print("解析第{}个条目时出错: {}".format(entry_count, e))
                        continue
            
            # 处理最后一个条目
            if buffer and buffer.strip():
                if buffer.startswith('# Time: '):
                    entry = buffer[8:]
                else:
                    entry = buffer
                    
                entry_count += 1
                try:
                    if self._parse_entry_with_range(entry, start_time, end_time):
                        processed += 1
                except Exception as e:
                    if self.debug_mode:
                        print("解析最后一个条目时出错: {}".format(e))
                    pass
        
        self.stats['total_entries'] = entry_count
        self.stats['parsed_entries'] = processed
        print("大文件解析完成，共处理 {} 个条目".format(entry_count))

    def _parse_entry_with_range(self, entry, start_time, end_time):
        """使用时间范围解析单个日志条目"""
        lines = entry.strip().split('\n')
        if len(lines) < 3:
            return False
            
        # 解析时间戳
        timestamp_line = lines[0].strip()
        timestamp = None
        
        # 调试信息：显示前几个时间戳的格式
        if (self.debug_mode or len(self.details) < 5):
            print("调试: 时间戳行 = '{}'".format(timestamp_line))
        
        # 尝试多种时间格式
        time_formats = [
            '%Y-%m-%dT%H:%M:%S.%f',     # 2025-03-11T14:47:34.158940 (处理后的格式)
            '%Y-%m-%dT%H:%M:%S',        # 2025-03-11T14:47:34 (ISO格式)
            '%y%m%d %H:%M:%S',          # 241201 14:30:25
            '%Y-%m-%d %H:%M:%S',        # 2024-12-01 14:30:25
            '%Y%m%d %H:%M:%S',          # 20241201 14:30:25
            '%Y-%m-%d %H:%M:%S.%f',     # 2024-12-01 14:30:25.123456 (带微秒)
        ]
        
        # 预处理时间戳：移除时区信息
        processed_timestamp_line = timestamp_line
        if '+08:00' in processed_timestamp_line:
            processed_timestamp_line = processed_timestamp_line.replace('+08:00', '')
        elif '+0800' in processed_timestamp_line:
            processed_timestamp_line = processed_timestamp_line.replace('+0800', '')
        
        for fmt in time_formats:
            try:
                timestamp = datetime.strptime(processed_timestamp_line, fmt)
                # 如果年份是两位数，调整为完整年份
                if timestamp.year < 2024:
                    timestamp = timestamp.replace(year=timestamp.year + 2000)
                if (self.debug_mode or len(self.details) < 5):
                    print("调试: 解析成功，时间戳 = {}".format(timestamp))
                break
            except ValueError:
                continue
        
        if not timestamp:
            if (self.debug_mode or len(self.details) < 5):
                print("调试: 时间戳解析失败")
            return False
        
        # 检查时间是否在指定范围内
        if timestamp < start_time or timestamp > end_time:
            if (self.debug_mode or len(self.details) < 5):
                print("调试: 时间戳 {} 不在范围内 ({} - {})，跳过".format(timestamp, start_time, end_time))
            return False
        
        # 更新时间范围统计
        if not self.stats['date_range']['start'] or timestamp < self.stats['date_range']['start']:
            self.stats['date_range']['start'] = timestamp
        if not self.stats['date_range']['end'] or timestamp > self.stats['date_range']['end']:
            self.stats['date_range']['end'] = timestamp
        
        # 继续使用原来的解析逻辑...
        return self._parse_entry_content(lines, timestamp)
    
    def _show_log_sample(self, log_file_path):
        """显示日志文件样本"""
        print("\n=== 日志文件样本 ===")
        try:
            with codecs.open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 读取前2000个字符作为样本
                sample = f.read(2000)
                print(sample)
                print("=== 样本结束 ===\n")
        except Exception as e:
            print("读取样本失败: {}".format(e))
    
    
    def _parse_small_file(self, log_file_path, start_time):
        """解析小文件（一次性读取）"""
        with codecs.open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()
        
        # 分割日志条目 - MySQL慢日志以 "# Time:" 开始每个条目
        entries = re.split(r'# Time: ', log_content)
        self.stats['total_entries'] = len(entries) - 1  # 排除第一个空条目
        
        print("找到 {} 个日志条目，开始解析...".format(self.stats['total_entries']))
        
        processed = 0
        for i, entry in enumerate(entries[1:], 1):  # 排除第一个空条目
            if i % 1000 == 0:
                print("已处理 {}/{} 个条目...".format(i, self.stats['total_entries']))
            
            try:
                if self._parse_entry(entry, start_time):
                    processed += 1
            except Exception as e:
                print("解析第{}个条目时出错: {}".format(i, e))
                continue
        
        self.stats['parsed_entries'] = processed
    
    def _parse_large_file(self, log_file_path, start_time):
        """解析大文件（流式读取）"""
        buffer = ""
        entry_count = 0
        processed = 0
        
        print("开始流式解析大文件...")
        
        with codecs.open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            while True:
                chunk = f.read(1024 * 1024)  # 每次读取1MB
                if not chunk:
                    break
                    
                buffer += chunk
                
                # 查找完整的日志条目
                while '# Time: ' in buffer:
                    if entry_count == 0:
                        # 第一个条目可能不完整，跳过到第一个完整条目
                        first_time_pos = buffer.find('# Time: ')
                        if first_time_pos > 0:
                            buffer = buffer[first_time_pos:]
                    
                    # 查找下一个条目的开始位置
                    next_time_pos = buffer.find('# Time: ', 8)  # 跳过当前的"# Time: "
                    
                    if next_time_pos == -1:
                        # 没有找到下一个条目，需要读取更多数据
                        break
                    
                    # 提取当前条目
                    entry = buffer[8:next_time_pos]  # 跳过"# Time: "
                    buffer = buffer[next_time_pos:]
                    
                    entry_count += 1
                    
                    if entry_count % 1000 == 0:
                        print("已处理 {} 个条目...".format(entry_count))
                    
                    try:
                        if self._parse_entry(entry, start_time):
                            processed += 1
                    except Exception as e:
                        continue
            
            # 处理最后一个条目
            if buffer and buffer.strip():
                if buffer.startswith('# Time: '):
                    entry = buffer[8:]
                else:
                    entry = buffer
                    
                entry_count += 1
                try:
                    if self._parse_entry(entry, start_time):
                        processed += 1
                except Exception as e:
                    pass
        
        self.stats['total_entries'] = entry_count
        self.stats['parsed_entries'] = processed
        print("大文件解析完成，共处理 {} 个条目".format(entry_count))
    
    def _parse_entry(self, entry, start_time):
        """解析单个日志条目"""
        lines = entry.strip().split('\n')
        if len(lines) < 3:
            return False
            
        # 解析时间戳
        timestamp_line = lines[0].strip()
        timestamp = None
        
        # 调试信息：显示前几个时间戳的格式
        if len(self.details) < 5:
            print("调试: 时间戳行 = '{}'".format(timestamp_line))
        
        # 尝试多种时间格式
        time_formats = [
            '%Y-%m-%dT%H:%M:%S.%f',     # 2025-03-11T14:47:34.158940 (处理后的格式)
            '%Y-%m-%dT%H:%M:%S',        # 2025-03-11T14:47:34 (ISO格式)
            '%y%m%d %H:%M:%S',          # 241201 14:30:25
            '%Y-%m-%d %H:%M:%S',        # 2024-12-01 14:30:25
            '%Y%m%d %H:%M:%S',          # 20241201 14:30:25
            '%Y-%m-%d %H:%M:%S.%f',     # 2024-12-01 14:30:25.123456 (带微秒)
        ]
        
        # 预处理时间戳：移除时区信息
        processed_timestamp_line = timestamp_line
        if '+08:00' in processed_timestamp_line:
            processed_timestamp_line = processed_timestamp_line.replace('+08:00', '')
        elif '+0800' in processed_timestamp_line:
            processed_timestamp_line = processed_timestamp_line.replace('+0800', '')
        
        for fmt in time_formats:
            try:
                timestamp = datetime.strptime(processed_timestamp_line, fmt)
                # 如果年份是两位数，调整为完整年份
                if timestamp.year < 2024:
                    timestamp = timestamp.replace(year=timestamp.year + 2000)
                if len(self.details) < 5:
                    print("调试: 解析成功，时间戳 = {}".format(timestamp))
                break
            except ValueError:
                continue
        
        if not timestamp:
            if len(self.details) < 5:
                print("调试: 时间戳解析失败")
            return False
        
        # 只处理最近N天的日志
        if timestamp < start_time:
            if len(self.details) < 5:
                print("调试: 时间戳 {} 早于起始时间 {}，跳过".format(timestamp, start_time))
            return False
        
        # 更新时间范围统计
        if not self.stats['date_range']['start'] or timestamp < self.stats['date_range']['start']:
            self.stats['date_range']['start'] = timestamp
        if not self.stats['date_range']['end'] or timestamp > self.stats['date_range']['end']:
            self.stats['date_range']['end'] = timestamp
        
        # 解析用户和数据库信息
        user_host_line = None
        query_time = 0
        lock_time = 0
        rows_sent = 0
        rows_examined = 0
        
        sql_start_idx = -1
        for i, line in enumerate(lines[1:], 1):
            if line.startswith('# User@Host:'):
                user_host_line = line
                if len(self.details) < 5:
                    print("调试: 用户主机行 = '{}'".format(user_host_line))
            elif line.startswith('# Query_time:'):
                # 解析性能指标
                match = re.search(r'Query_time:\s*([\d.]+)\s*Lock_time:\s*([\d.]+)\s*Rows_sent:\s*(\d+)\s*Rows_examined:\s*(\d+)', line)
                if match:
                    query_time = float(match.group(1))
                    lock_time = float(match.group(2))
                    rows_sent = int(match.group(3))
                    rows_examined = int(match.group(4))
                if len(self.details) < 5:
                    print("调试: 查询时间行 = '{}'".format(line))
            elif not line.startswith('#') and line.strip():
                sql_start_idx = i
                if len(self.details) < 5:
                    print("调试: SQL开始索引 = {}, 行 = '{}...'".format(sql_start_idx, line[:100]))
                break
        
        if sql_start_idx == -1 or not user_host_line:
            if len(self.details) < 5:
                print("调试: SQL开始索引({}) 或用户主机行({}) 缺失".format(sql_start_idx, user_host_line))
            return False
        
        # 提取用户名和数据库 - 尝试更宽松的匹配
        username = 'unknown'
        dbname = 'unknown'
        
        # 尝试多种用户主机行格式
        user_patterns = [
            r'# User@Host:\s*(\w+)\[.*?\]\s*@.*?db:\s*(\w+)',      # 带数据库名的格式
            r'# User@Host:\s*(\w+)\[.*?\]\s*@.*?Id:\s*\d+',       # 不带数据库名，只有用户名的格式
            r'# User@Host:\s*(\w+)\[.*?\].*?db:\s*(\w+)',         # 更宽松的格式
            r'# User@Host:\s*(\w+).*?db:\s*(\w+)',                # 最宽松的格式
            r'# User@Host:\s*(\w+)',                              # 只匹配用户名
        ]
        
        for i, pattern in enumerate(user_patterns):
            user_match = re.search(pattern, user_host_line)
            if user_match:
                username = user_match.group(1)
                # 对于第二个模式（只有用户名，没有数据库），从SQL中提取数据库名
                if i == 1:  # 这是没有db字段的格式
                    # 尝试从SQL语句中提取数据库名
                    sql_preview = '\n'.join(lines[sql_start_idx:sql_start_idx+5])
                    db_match = re.search(r'use\s+(\w+)\s*;', sql_preview, re.IGNORECASE)
                    if db_match:
                        dbname = db_match.group(1)
                    else:
                        dbname = 'unknown'
                elif len(user_match.groups()) >= 2:
                    dbname = user_match.group(2)
                if len(self.details) < 5:
                    print("调试: 匹配成功，用户={}, 数据库={}".format(username, dbname))
                break
        else:
            if len(self.details) < 5:
                print("调试: 用户主机行匹配失败: {}".format(user_host_line))
            # 即使用户行解析失败，也不要返回False，使用默认值
            username = 'unknown'
            dbname = 'unknown'
        
        # 提取SQL语句
        sql_lines = lines[sql_start_idx:]
        raw_sql = '\n'.join(sql_lines).strip()
        
        # 移除结尾的分号和SET timestamp语句
        raw_sql = re.sub(r'SET timestamp=\d+;?\s*$', '', raw_sql, flags=re.IGNORECASE)
        raw_sql = raw_sql.rstrip(';').strip()
        
        # 从SQL语句中提取数据库名称 - 总是从USE语句获取
        dbname = 'unknown'
        
        # 检查整个SQL内容，包括前面可能的USE语句  
        full_sql_content = '\n'.join(lines[sql_start_idx:])
        
        # 查找USE语句 - 使用更宽松的匹配，按优先级排序
        use_patterns = [
            r'USE\s+`?([^`\s;]+)`?\s*;?',           # 标准USE语句
            r'use\s+`?([^`\s;]+)`?\s*;?',           # 小写use
            r'Use\s+`?([^`\s;]+)`?\s*;?',           # 首字母大写Use
            r'USE\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;?', # 不带引号的USE
        ]
        
        for pattern in use_patterns:
            use_match = re.search(pattern, full_sql_content, re.MULTILINE | re.IGNORECASE)
            if use_match:
                potential_dbname = use_match.group(1).strip()
                # 过滤掉明显不是数据库名的内容
                if potential_dbname and not potential_dbname.upper() in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'FROM', 'WHERE', 'SET', 'VALUES']:
                    dbname = potential_dbname
                    if len(self.details) < 5:
                        print("调试: 从USE语句中提取数据库名: {}".format(dbname))
                    break
        
        # 如果没有找到USE语句，记录调试信息但仍继续处理
        if dbname == 'unknown' and len(self.details) < 5:
            print("调试: 未找到USE语句，数据库名保持为unknown")
        
        # 清理SQL语句：移除USE语句，因为它不是实际的查询
        cleaned_sql = re.sub(r'USE\s+`?\w+`?\s*;\s*', '', raw_sql, flags=re.IGNORECASE).strip()
        
        # 如果清理后的SQL为空或太短，使用原SQL
        if not cleaned_sql or len(cleaned_sql) < 10:
            cleaned_sql = raw_sql
            
        if not cleaned_sql or len(cleaned_sql) < 10:  # 忽略过短的SQL
            if len(self.details) < 5:
                print("调试: SQL太短或为空: '{}'".format(cleaned_sql))
            return False
        
        # 使用清理后的SQL作为实际查询
        raw_sql = cleaned_sql
        
        # 过滤掉包含 "index not used" 关键字的语句
        if re.search(r'index\s+not\s+used', raw_sql, re.IGNORECASE):
            if len(self.details) < 5:
                print("调试: 跳过包含'index not used'关键字的语句")
            return False
        
        # 只记录执行时间超过阈值的慢查询
        if query_time < self.min_query_time:
            if len(self.details) < 5:
                print("调试: 跳过执行时间{}s小于{}秒的查询".format(query_time, self.min_query_time))
            return False
        
        if len(self.details) < 5:
            print("调试: 成功解析条目，SQL长度={}，执行时间={}s".format(len(raw_sql), query_time))
        
        # 规范化SQL
        normalized_sql = self.normalize_sql(raw_sql)
        checksum = self.generate_checksum(normalized_sql)
        
        # 存储指纹信息
        if checksum not in self.fingerprints:
            self.fingerprints[checksum] = {
                'checksum': checksum,
                'normalized_sql': normalized_sql,
                'raw_sql': raw_sql[:PARSE_CONFIG.get('max_sql_length', 5000)],  # 限制长度避免过大
                'username': username,
                'dbname': dbname,
                'first_seen': timestamp,
                'last_seen': timestamp,
                'reviewed_status': '待优化',
                'comments': None,
                'count': 1
            }
        else:
            # 更新时间范围和计数
            fp = self.fingerprints[checksum]
            if timestamp > fp['last_seen']:
                fp['last_seen'] = timestamp
            if timestamp < fp['first_seen']:
                fp['first_seen'] = timestamp
            fp['count'] += 1
        
        # 存储详细信息
        self.details.append({
            'checksum': checksum,
            'sql_text': raw_sql[:PARSE_CONFIG.get('max_sql_length', 5000)],  # 添加sql_text字段
            'timestamp': timestamp,
            'query_time': query_time,
            'lock_time': lock_time,
            'rows_sent': rows_sent,
            'rows_examined': rows_examined,
            'username': username,
            'dbname': dbname
        })
        
    def _parse_entry_content(self, lines, timestamp):
        """解析日志条目的内容部分（不包括时间戳解析）"""
        # 解析用户和数据库信息
        user_host_line = None
        query_time = 0
        lock_time = 0
        rows_sent = 0
        rows_examined = 0
        
        sql_start_idx = -1
        for i, line in enumerate(lines[1:], 1):
            if line.startswith('# User@Host:'):
                user_host_line = line
                if (self.debug_mode or len(self.details) < 5):
                    print("调试: 用户主机行 = '{}'".format(user_host_line))
            elif line.startswith('# Query_time:'):
                # 解析性能指标
                match = re.search(r'Query_time:\s*([\d.]+)\s*Lock_time:\s*([\d.]+)\s*Rows_sent:\s*(\d+)\s*Rows_examined:\s*(\d+)', line)
                if match:
                    query_time = float(match.group(1))
                    lock_time = float(match.group(2))
                    rows_sent = int(match.group(3))
                    rows_examined = int(match.group(4))
                if (self.debug_mode or len(self.details) < 5):
                    print("调试: 查询时间行 = '{}'".format(line))
            elif not line.startswith('#') and line.strip():
                sql_start_idx = i
                if (self.debug_mode or len(self.details) < 5):
                    print("调试: SQL开始索引 = {}, 行 = '{}...'".format(sql_start_idx, line[:100]))
                break
        
        if sql_start_idx == -1 or not user_host_line:
            if (self.debug_mode or len(self.details) < 5):
                print("调试: SQL开始索引({}) 或用户主机行({}) 缺失".format(sql_start_idx, user_host_line))
            return False
        
        # 提取用户名和数据库 - 尝试更宽松的匹配
        username = 'unknown'
        dbname = 'unknown'
        
        # 尝试多种用户主机行格式
        user_patterns = [
            r'# User@Host:\s*(\w+)\[.*?\]\s*@.*?db:\s*(\w+)',      # 带数据库名的格式
            r'# User@Host:\s*(\w+)\[.*?\]\s*@.*?Id:\s*\d+',       # 不带数据库名，只有用户名的格式
            r'# User@Host:\s*(\w+)\[.*?\].*?db:\s*(\w+)',         # 更宽松的格式
            r'# User@Host:\s*(\w+).*?db:\s*(\w+)',                # 最宽松的格式
            r'# User@Host:\s*(\w+)',                              # 只匹配用户名
        ]
        
        for i, pattern in enumerate(user_patterns):
            user_match = re.search(pattern, user_host_line)
            if user_match:
                username = user_match.group(1)
                # 对于第二个模式（只有用户名，没有数据库），从SQL中提取数据库名
                if i == 1:  # 这是没有db字段的格式
                    # 尝试从SQL语句中提取数据库名
                    sql_preview = '\n'.join(lines[sql_start_idx:sql_start_idx+5])
                    db_match = re.search(r'use\s+(\w+)\s*;', sql_preview, re.IGNORECASE)
                    if db_match:
                        dbname = db_match.group(1)
                    else:
                        dbname = 'unknown'
                elif len(user_match.groups()) >= 2:
                    dbname = user_match.group(2)
                if (self.debug_mode or len(self.details) < 5):
                    print("调试: 匹配成功，用户={}, 数据库={}".format(username, dbname))
                break
        else:
            if (self.debug_mode or len(self.details) < 5):
                print("调试: 用户主机行匹配失败: {}".format(user_host_line))
            # 即使用户行解析失败，也不要返回False，使用默认值
            username = 'unknown'
            dbname = 'unknown'
        
        # 提取SQL语句
        sql_lines = lines[sql_start_idx:]
        raw_sql = '\n'.join(sql_lines).strip()
        
        # 移除结尾的分号和SET timestamp语句
        raw_sql = re.sub(r'SET timestamp=\d+;?\s*$', '', raw_sql, flags=re.IGNORECASE)
        raw_sql = raw_sql.rstrip(';').strip()
        
        # 从SQL语句中提取数据库名称 - 总是从USE语句获取
        dbname = 'unknown'
        
        # 检查整个SQL内容，包括前面可能的USE语句
        full_sql_content = '\n'.join(lines[sql_start_idx:])
        
        # 查找USE语句 - 使用更宽松的匹配，按优先级排序
        use_patterns = [
            r'USE\s+`?([^`\s;]+)`?\s*;?',           # 标准USE语句
            r'use\s+`?([^`\s;]+)`?\s*;?',           # 小写use
            r'Use\s+`?([^`\s;]+)`?\s*;?',           # 首字母大写Use
            r'USE\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;?', # 不带引号的USE
        ]
        
        for pattern in use_patterns:
            use_match = re.search(pattern, full_sql_content, re.MULTILINE | re.IGNORECASE)
            if use_match:
                potential_dbname = use_match.group(1).strip()
                # 过滤掉明显不是数据库名的内容
                if potential_dbname and not potential_dbname.upper() in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'FROM', 'WHERE', 'SET', 'VALUES']:
                    dbname = potential_dbname
                    if (self.debug_mode or len(self.details) < 5):
                        print("调试: 从USE语句中提取数据库名: {}".format(dbname))
                    break
        
        # 如果没有找到USE语句，记录调试信息但仍继续处理
        if dbname == 'unknown' and (self.debug_mode or len(self.details) < 5):
            print("调试: 未找到USE语句，数据库名保持为unknown")
        
        # 清理SQL语句：移除USE语句，因为它不是实际的查询
        cleaned_sql = re.sub(r'USE\s+`?\w+`?\s*;\s*', '', raw_sql, flags=re.IGNORECASE).strip()
        
        # 如果清理后的SQL为空或太短，使用原SQL
        if not cleaned_sql or len(cleaned_sql) < 10:
            cleaned_sql = raw_sql
            
        if not cleaned_sql or len(cleaned_sql) < 10:  # 忽略过短的SQL
            if (self.debug_mode or len(self.details) < 5):
                print("调试: SQL太短或为空: '{}'".format(cleaned_sql))
            return False
        
        # 使用清理后的SQL作为实际查询
        raw_sql = cleaned_sql
        
        # 过滤掉包含 "index not used" 关键字的语句
        if re.search(r'index\s+not\s+used', raw_sql, re.IGNORECASE):
            if (self.debug_mode or len(self.details) < 5):
                print("调试: 跳过包含'index not used'关键字的语句")
            return False
        
        # 只记录执行时间超过阈值的慢查询
        if query_time < self.min_query_time:
            if (self.debug_mode or len(self.details) < 5):
                print("调试: 跳过执行时间{}s小于{}秒的查询".format(query_time, self.min_query_time))
            return False
        
        if (self.debug_mode or len(self.details) < 5):
            print("调试: 成功解析条目，SQL长度={}，执行时间={}s".format(len(raw_sql), query_time))
        
        # 规范化SQL
        normalized_sql = self.normalize_sql(raw_sql)
        checksum = self.generate_checksum(normalized_sql)
        
        # 存储指纹信息
        if checksum not in self.fingerprints:
            self.fingerprints[checksum] = {
                'checksum': checksum,
                'normalized_sql': normalized_sql,
                'raw_sql': raw_sql[:PARSE_CONFIG.get('max_sql_length', 5000)],  # 限制长度避免过大
                'username': username,
                'dbname': dbname,
                'first_seen': timestamp,
                'last_seen': timestamp,
                'reviewed_status': '待优化',
                'comments': None,
                'count': 1
            }
        else:
            # 更新时间范围和计数
            fp = self.fingerprints[checksum]
            if timestamp > fp['last_seen']:
                fp['last_seen'] = timestamp
            if timestamp < fp['first_seen']:
                fp['first_seen'] = timestamp
            fp['count'] += 1
        
        # 存储详细信息
        self.details.append({
            'checksum': checksum,
            'sql_text': raw_sql[:PARSE_CONFIG.get('max_sql_length', 5000)],  # 添加sql_text字段
            'timestamp': timestamp,
            'query_time': query_time,
            'lock_time': lock_time,
            'rows_sent': rows_sent,
            'rows_examined': rows_examined,
            'username': username,
            'dbname': dbname
        })
        
        return True
    
    def save_to_database(self):
        """保存解析结果到数据库"""
        if not self.fingerprints:
            print("没有数据需要保存")
            return
        
        print("\n开始保存数据到数据库...")
        print("  指纹记录: {}".format(len(self.fingerprints)))
        print("  详细记录: {}".format(len(self.details)))
        
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # 保存指纹信息
            fingerprint_sql = """
                INSERT INTO slow_query_fingerprint 
                (checksum, normalized_sql, raw_sql, username, dbname, 
                 first_seen, last_seen, reviewed_status, comments)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                last_seen = GREATEST(last_seen, VALUES(last_seen)),
                first_seen = LEAST(first_seen, VALUES(first_seen))
            """
            
            fingerprint_data = []
            for fp in self.fingerprints.values():
                fingerprint_data.append((
                    fp['checksum'],
                    fp['normalized_sql'],
                    fp['raw_sql'],
                    fp['username'],
                    fp['dbname'],
                    fp['first_seen'],
                    fp['last_seen'],
                    fp['reviewed_status'],
                    fp['comments']
                ))
            
            cursor.executemany(fingerprint_sql, fingerprint_data)
            print("  已保存 {} 条指纹记录".format(cursor.rowcount))
            
            # 保存详细信息
            detail_sql = """
                INSERT IGNORE INTO slow_query_detail 
                (checksum, sql_text, timestamp, query_time, lock_time, rows_sent, rows_examined)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            detail_data = []
            for detail in self.details:
                detail_data.append((
                    detail['checksum'],
                    detail.get('sql_text', ''),  # 添加 sql_text 字段
                    detail['timestamp'],
                    detail['query_time'],
                    detail['lock_time'],
                    detail['rows_sent'],
                    detail['rows_examined']
                ))
            
            cursor.executemany(detail_sql, detail_data)
            print("  已保存 {} 条详细记录".format(cursor.rowcount))
            
            conn.commit()
            print("数据保存成功！")
            
            # 显示保存统计
            self._show_save_statistics(cursor)
            
        except Exception as e:
            conn.rollback()
            print("保存数据失败: {}".format(e))
            raise
        finally:
            cursor.close()
            conn.close()
    
    def _show_save_statistics(self, cursor):
        """显示保存统计信息"""
        try:
            # 查询总的指纹数量
            cursor.execute("SELECT COUNT(*) FROM slow_query_fingerprint")
            total_fingerprints = cursor.fetchone()[0]
            
            # 查询总的详细记录数量
            cursor.execute("SELECT COUNT(*) FROM slow_query_detail")
            total_details = cursor.fetchone()[0]
            
            # 查询最近的记录
            cursor.execute("""
                SELECT COUNT(*), MIN(timestamp), MAX(timestamp) 
                FROM slow_query_detail 
                WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
            recent_stats = cursor.fetchone()
            
            print("\n数据库当前统计:")
            print("  总指纹数量: {}".format(total_fingerprints))
            print("  总详细记录: {}".format(total_details))
            if recent_stats[0]:
                print("  最近7天记录: {} 条".format(recent_stats[0]))
                print("  时间范围: {} 到 {}".format(recent_stats[1], recent_stats[2]))
                
        except Exception as e:
            print("获取统计信息失败: {}".format(e))

def main():
    """主函数"""
    import argparse
    
    # 创建参数解析器
    parser = argparse.ArgumentParser(
        description='MySQL 慢查询日志解析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python %(prog)s                                    # 使用默认配置解析最近7天
  python %(prog)s /path/to/slow.log                  # 指定日志文件路径
  python %(prog)s --days 3                           # 解析最近3天的日志
  python %(prog)s --min-time 10                      # 只记录超过10秒的慢查询
  python %(prog)s --start "2025-01-01" --end "2025-01-07"  # 指定时间范围
  python %(prog)s /path/to/slow.log --days 1 --auto-save --min-time 3  # 自动保存超过3秒的查询
        """
    )
    
    parser.add_argument('log_path', nargs='?', default=SLOW_LOG_PATH,
                      help='慢日志文件路径 (默认: {})'.format(SLOW_LOG_PATH))
    
    parser.add_argument('--days', '-d', type=int, default=PARSE_CONFIG.get('days_back', 7),
                      help='解析最近N天的日志 (默认: %(default)s天)')
    
    parser.add_argument('--start', '--start-time', type=str,
                      help='开始时间 (格式: YYYY-MM-DD 或 "YYYY-MM-DD HH:MM:SS")')
    
    parser.add_argument('--end', '--end-time', type=str,
                      help='结束时间 (格式: YYYY-MM-DD 或 "YYYY-MM-DD HH:MM:SS")')
    
    parser.add_argument('--auto-save', action='store_true',
                      help='自动保存到数据库，不询问用户')
    
    parser.add_argument('--debug', action='store_true',
                      help='启用调试模式，显示更多解析信息')
    
    parser.add_argument('--min-time', '-t', type=float, default=PARSE_CONFIG.get('min_query_time', 5.0),
                      help='最小查询时间阈值（秒），只记录超过此时间的慢查询 (默认: %(default)s秒)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MySQL 慢查询日志解析工具")
    print("=" * 60)
    print("日志文件路径: {}".format(args.log_path))
    print("最小查询时间阈值: {} 秒".format(args.min_time))
    
    # 计算时间范围
    start_time = None
    end_time = None
    
    if args.start and args.end:
        # 使用指定的时间范围
        try:
            # 尝试解析时间格式
            time_formats = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S']
            
            for fmt in time_formats:
                try:
                    start_time = datetime.strptime(args.start, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError("无法解析开始时间格式: {}".format(args.start))
                
            for fmt in time_formats:
                try:
                    end_time = datetime.strptime(args.end, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError("无法解析结束时间格式: {}".format(args.end))
            
            if start_time >= end_time:
                raise ValueError("开始时间必须早于结束时间")
                
            print("解析时间范围: {} 到 {}".format(start_time.strftime('%Y-%m-%d %H:%M:%S'), end_time.strftime('%Y-%m-%d %H:%M:%S')))
            
        except ValueError as e:
            print("时间参数错误: {}".format(e))
            print("时间格式示例: 2025-01-01 或 '2025-01-01 10:30:00'")
            sys.exit(1)
            
    else:
        # 使用天数回溯
        days_back = args.days
        start_time = datetime.now() - timedelta(days=days_back)
        end_time = datetime.now()
        print("解析最近{}天的慢查询（从 {} 开始）".format(days_back, start_time.strftime('%Y-%m-%d %H:%M:%S')))
    
    # 检查文件是否存在
    if not os.path.exists(args.log_path):
        print("错误: 慢日志文件不存在: {}".format(args.log_path))
        print("请确认路径是否正确，或通过参数指定:")
        print("python {} /path/to/slow.log".format(sys.argv[0]))
        sys.exit(1)
    
    try:
        # 创建解析器
        log_parser = SlowLogParser(min_query_time=args.min_time)
        log_parser.debug_mode = args.debug
        
        # 解析慢日志
        log_parser.parse_slow_log_with_time_range(args.log_path, start_time, end_time)
        
        if log_parser.stats['parsed_entries'] == 0:
            print("未找到符合条件的慢查询记录")
            return
        
        # 决定是否保存到数据库
        save_to_db = args.auto_save
        
        if not save_to_db:
            print("\n" + "="*50)
            response = input("是否将解析结果保存到数据库? (y/N): ")
            save_to_db = response.lower() in ['y', 'yes']
        
        if save_to_db:
            # 提醒检查数据库配置
            if not args.auto_save:
                print("\n请确认数据库连接配置正确:")
                print("  主机: {}".format(DB_CONFIG['host']))
                print("  用户: {}".format(DB_CONFIG['user']))
                print("  数据库: {}".format(DB_CONFIG['database']))
                
                confirm = input("配置正确吗? (y/N): ")
                if not confirm.lower() in ['y', 'yes']:
                    print("请修改脚本中的DB_CONFIG配置后重新运行")
                    return
            
            log_parser.save_to_database()
        else:
            print("解析完成，未保存到数据库")
            
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print("程序执行出错: {}".format(e))
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
