#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器端慢日志解析脚本
直接在MySQL服务器上解析慢日志并导入到数据库
"""

import re
import hashlib
import pymysql
from datetime import datetime, timedelta
import sys
import os

# 尝试导入配置文件，如果不存在则使用默认配置
try:
    from server_config import DB_CONFIG, SLOW_LOG_PATH, PARSE_CONFIG
except ImportError:
    print("警告: 未找到server_config.py配置文件，使用默认配置")
    DB_CONFIG = {
        'host': '172.16.176.70',
        'user': 'root',
        'password': 'SlowQ#123',  # 需要修改
        'database': 'slow_query_analysis',
        'charset': 'utf8mb4',
        'autocommit': False

    }
    SLOW_LOG_PATH = "/data/mysql/log/slow.log"
    PARSE_CONFIG = {
        'days_back': 7,
        'max_sql_length': 500000,  # 增加到500KB，支持更长的SQL语句
        'batch_size': 1000,
        'min_query_time': 5.0  # 最小查询时间（秒）
    }

# 用户名到数据库名的映射字典
# 当慢查询日志中无法获取数据库名时，根据用户名推断数据库名
try:
    from username_mapping_config import USER_TO_DATABASE_MAPPING
    print("已加载用户名映射配置文件")
except ImportError:
    # 如果没有配置文件，使用默认映射
    USER_TO_DATABASE_MAPPING = {
        # 可以根据需要添加更多映射关系
        # 'username': 'database_name',
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
        return hashlib.md5(normalized_sql.encode('utf-8')).hexdigest()
    
    def infer_database_from_username(self, username):
        """根据用户名推断数据库名"""
        if not username or username == 'unknown':
            return 'unknown'
        
        # 首先查找完全匹配的用户名
        if username in USER_TO_DATABASE_MAPPING:
            inferred_db = USER_TO_DATABASE_MAPPING[username]
            if self.debug_mode:
                print(f"调试: 根据用户名 '{username}' 推断数据库名为 '{inferred_db}'")
            return inferred_db
        
        # 如果没有完全匹配，尝试部分匹配（用户名可能包含额外字符）
        for mapped_user, mapped_db in USER_TO_DATABASE_MAPPING.items():
            if mapped_user in username or username in mapped_user:
                if self.debug_mode:
                    print(f"调试: 根据用户名 '{username}' 部分匹配 '{mapped_user}'，推断数据库名为 '{mapped_db}'")
                return mapped_db
        
        # 如果都没有匹配，返回unknown
        if self.debug_mode:
            print(f"调试: 用户名 '{username}' 未找到对应的数据库映射，保持为 'unknown'")
        return 'unknown'
    
    def format_sql(self, sql):
        """格式化SQL语句，提高可读性"""
        if not sql or len(sql.strip()) == 0:
            return sql
        
        # 第一步：清理各种空白符
        # 移除行首行尾空白
        sql = sql.strip()
        
        # 将所有类型的空白符（空格、制表符、换行符等）统一为单个空格
        sql = re.sub(r'\s+', ' ', sql)
        
        # 移除SQL注释
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)  # 多行注释
        sql = re.sub(r'--.*?(?=\n|$)', '', sql)  # 单行注释
        
        # 移除多余的空格（在特殊字符前后）
        sql = re.sub(r'\s*([(),;])\s*', r'\1', sql)  # 括号、逗号、分号前后的空格
        sql = re.sub(r'\s*([=<>!]+)\s*', r' \1 ', sql)  # 操作符前后保持单个空格
        
        # 处理复合操作符（>=, <=, !=, <>等）
        sql = re.sub(r'\s*([<>!]=?)\s*', r' \1 ', sql)  # 复合比较操作符
        
        # 确保关键字之间有适当的空格 - 更精确的匹配
        sql = re.sub(r'(\w)(and)(\w)', r'\1 \2 \3', sql, flags=re.IGNORECASE)
        sql = re.sub(r'(\w)(or)(\w)', r'\1 \2 \3', sql, flags=re.IGNORECASE)
        sql = re.sub(r'(\w)(like)', r'\1 \2', sql, flags=re.IGNORECASE)
        sql = re.sub(r'(like)(\w)', r'\1 \2', sql, flags=re.IGNORECASE)
        
        # 确保数字和关键字之间有空格
        sql = re.sub(r'(\d)(and|or)(\w)', r'\1 \2 \3', sql, flags=re.IGNORECASE)
        sql = re.sub(r'(\w)(and|or)(\d)', r'\1 \2 \3', sql, flags=re.IGNORECASE)
        
        # 清理引号内容周围的空格（但保持引号内的内容不变）
        sql = re.sub(r"\s*'\s*([^']*?)\s*'\s*", r" '\1' ", sql)  # 单引号
        sql = re.sub(r'\s*"\s*([^"]*?)\s*"\s*', r' "\1" ', sql)  # 双引号
        
        # 第二步：为主要关键字添加换行
        major_keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT']
        for keyword in major_keywords:
            # 在关键字前添加换行（除了语句开头）
            pattern = r'(?<!^)\s*' + re.escape(keyword) + r'\s+'
            replacement = r'\n' + keyword + ' '
            sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
        
        # 第三步：为JOIN添加换行
        join_keywords = ['JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'OUTER JOIN', 'FULL JOIN', 'CROSS JOIN']
        for join in join_keywords:
            pattern = r'\s+' + re.escape(join) + r'\s+'
            replacement = r'\n' + join + ' '
            sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
        
        # 第四步：为UPDATE、INSERT、DELETE的关键子句添加换行
        sql = re.sub(r'\s+(SET|VALUES|INTO)\s+', r'\n\1 ', sql, flags=re.IGNORECASE)
        
        # 第五步：在AND/OR前添加适当的缩进和换行
        sql = re.sub(r'\s+(AND|OR)\s+', r'\n  \1 ', sql, flags=re.IGNORECASE)
        
        # 第六步：处理子查询的缩进和括号格式化
        lines = sql.split('\n')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 处理右括号 - 在添加缩进前减少层级
            if ')' in line:
                # 计算括号平衡
                open_count = line.count('(')
                close_count = line.count(')')
                if close_count > open_count:
                    indent_level = max(0, indent_level - (close_count - open_count))
            
            # 添加当前行的缩进
            if indent_level > 0:
                line = '  ' * indent_level + line
            
            # 处理括号周围的空格
            line = re.sub(r'\s*\(\s*', '(', line)  # 左括号后无空格
            line = re.sub(r'\s*\)\s*', ') ', line)  # 右括号前无空格，后有空格
            line = line.rstrip()  # 移除行尾空格
            
            formatted_lines.append(line)
            
            # 处理左括号 - 在添加缩进后增加层级
            if '(' in line:
                open_count = line.count('(')
                close_count = line.count(')')
                if open_count > close_count:
                    indent_level += (open_count - close_count)
        
        # 第七步：重新组合SQL并进行最终清理
        formatted_sql = '\n'.join(formatted_lines)
        
        # 清理多余的空行
        formatted_sql = re.sub(r'\n\s*\n+', '\n', formatted_sql)
        
        # 清理逗号前后的空格
        formatted_sql = re.sub(r'\s*,\s*', ', ', formatted_sql)
        
        # 第八步：确保关键字大写（提高可读性）
        major_keywords_upper = [
            'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT', 
            'INSERT', 'UPDATE', 'DELETE', 'SET', 'VALUES', 'INTO',
            'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'OUTER JOIN', 'FULL JOIN', 'CROSS JOIN',
            'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'AS', 'ON',
            'UNION', 'UNION ALL', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'IF'
        ]
        
        for keyword in major_keywords_upper:
            # 使用单词边界确保完整匹配
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            formatted_sql = re.sub(pattern, keyword, formatted_sql, flags=re.IGNORECASE)
        
        # 第九步：最终清理和修复
        formatted_sql = formatted_sql.strip()
        
        # 修复缺失的空格问题
        formatted_sql = re.sub(r'(\d)(and|or)', r'\1 \2', formatted_sql, flags=re.IGNORECASE)
        formatted_sql = re.sub(r'(and|or)(\d)', r'\1 \2', formatted_sql, flags=re.IGNORECASE)
        formatted_sql = re.sub(r'(\w)(and|or)(?=\s*\w)', r'\1 \2', formatted_sql, flags=re.IGNORECASE)
        
        # 确保语句结尾有适当的标点
        if formatted_sql and not formatted_sql.endswith(';'):
            # 如果原始SQL有分号，保留分号
            if sql.rstrip().endswith(';'):
                formatted_sql += ';'
        
        return formatted_sql
    
    def parse_slow_log(self, log_file_path, days_back=None):
        """解析慢日志文件"""
        if days_back is None:
            days_back = PARSE_CONFIG.get('days_back', 7)
            
        # 计算起始时间
        start_time = datetime.now() - timedelta(days=days_back)
        print(f"解析最近{days_back}天的慢查询（从 {start_time.strftime('%Y-%m-%d %H:%M:%S')} 开始）")
        
        if not os.path.exists(log_file_path):
            raise FileNotFoundError(f"慢日志文件不存在: {log_file_path}")
        
        file_size = os.path.getsize(log_file_path)
        print(f"慢日志文件大小: {file_size / (1024*1024):.2f} MB")
        
        # 显示文件样本
        self._show_log_sample(log_file_path)
        
        if file_size > 500 * 1024 * 1024:  # 超过500MB的大文件
            print("检测到大文件，使用流式读取模式...")
            self._parse_large_file(log_file_path, start_time)
        else:
            print("使用标准读取模式...")
            self._parse_small_file(log_file_path, start_time)
        
        self.stats['unique_fingerprints'] = len(self.fingerprints)
        
        print(f"\n解析完成统计:")
        print(f"  总日志条目: {self.stats['total_entries']}")
        print(f"  成功解析: {self.stats['parsed_entries']}")
        print(f"  唯一SQL指纹: {self.stats['unique_fingerprints']}")
        print(f"  详细执行记录: {len(self.details)}")
    def parse_slow_log_with_time_range(self, log_file_path, start_time, end_time, use_optimization=True, optimization_threshold=100):
        """使用指定时间范围解析慢日志文件"""
        print(f"解析时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 到 {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 清空之前的解析结果
        self.details = []
        self.fingerprints = {}
        self.stats = {
            'total_entries': 0,
            'parsed_entries': 0,
            'unique_fingerprints': 0,
            'date_range': {'start': None, 'end': None}
        }
        
        if not os.path.exists(log_file_path):
            raise FileNotFoundError(f"慢日志文件不存在: {log_file_path}")
        
        file_size = os.path.getsize(log_file_path)
        print(f"慢日志文件大小: {file_size / (1024*1024):.2f} MB")
        
        # 显示文件样本
        self._show_log_sample(log_file_path)
        
        # 尝试使用时间范围优化
        threshold_bytes = optimization_threshold * 1024 * 1024
        should_optimize = use_optimization and file_size > threshold_bytes
        
        if should_optimize:
            print(f"检测到大文件（>{optimization_threshold}MB），使用时间范围优化模式...")
            self._parse_with_time_optimization(log_file_path, start_time, end_time)
        elif file_size > 500 * 1024 * 1024:  # 超过500MB的超大文件
            print("检测到超大文件，使用流式读取模式...")
            self._parse_large_file_with_range(log_file_path, start_time, end_time)
        else:
            print("使用标准读取模式...")
            self._parse_small_file_with_range(log_file_path, start_time, end_time)
        
        self.stats['unique_fingerprints'] = len(self.fingerprints)
        
        print(f"\n解析完成统计:")
        print(f"  总日志条目: {self.stats['total_entries']}")
        print(f"  成功解析: {self.stats['parsed_entries']}")
        print(f"  唯一SQL指纹: {self.stats['unique_fingerprints']}")
        print(f"  详细执行记录: {len(self.details)}")
        if self.stats['date_range']['start'] and self.stats['date_range']['end']:
            print(f"  时间范围: {self.stats['date_range']['start']} 到 {self.stats['date_range']['end']}")
        
        # 返回解析结果
        return self.details

    def _parse_with_time_optimization(self, log_file_path, start_time, end_time):
        """使用时间范围优化的解析方法"""
        import time
        optimization_start = time.time()
        
        # 检查文件大小，如果超过安全限制，直接使用流式解析
        file_size = os.path.getsize(log_file_path)
        file_size_gb = file_size / (1024 * 1024 * 1024)
        
        # 如果文件超过2GB，不使用时间优化，直接流式解析
        if file_size_gb > 2.0:
            print(f"文件过大 ({file_size_gb:.1f}GB)，直接使用流式标准模式解析以避免内存问题...")
            self._parse_standard_mode_with_range(log_file_path, start_time, end_time)
            return
        
        print("正在定位目标时间范围...")
        
        # 第一步：快速定位开始位置
        locate_start = time.time()
        start_offset = self._find_time_offset(log_file_path, start_time, search_start=True)
        end_offset = self._find_time_offset(log_file_path, end_time, search_start=False)
        locate_time = time.time() - locate_start
        
        if start_offset is None or end_offset is None:
            print("警告: 无法定位时间范围，使用流式标准模式解析")
            self._parse_standard_mode_with_range(log_file_path, start_time, end_time)
            return
        
        # 确保end_offset大于start_offset
        if end_offset <= start_offset:
            print("警告: 时间范围定位异常，使用流式标准模式解析")
            self._parse_standard_mode_with_range(log_file_path, start_time, end_time)
            return
        
        target_size = end_offset - start_offset
        total_size = os.path.getsize(log_file_path)
        optimization_ratio = (target_size / total_size) * 100
        
        print(f"时间定位耗时: {locate_time:.2f} 秒")
        print(f"目标时间范围数据大小: {target_size / (1024*1024):.2f} MB")
        print(f"优化比例: {optimization_ratio:.1f}% (跳过了 {100-optimization_ratio:.1f}% 的数据)")
        
        # 第二步：只读取目标范围的数据
        parse_start = time.time()
        self._parse_range_data(log_file_path, start_offset, end_offset, start_time, end_time)
        parse_time = time.time() - parse_start
        
        total_time = time.time() - optimization_start
        estimated_full_time = total_time / (optimization_ratio / 100)
        
        print(f"\n性能统计:")
        print(f"  实际解析时间: {total_time:.2f} 秒")
        print(f"  预估全文件时间: {estimated_full_time:.2f} 秒")
        print(f"  时间节省: {estimated_full_time - total_time:.2f} 秒 ({((estimated_full_time - total_time) / estimated_full_time * 100):.1f}%)")

    def _find_time_offset(self, log_file_path, target_time, search_start=True):
        """使用二分查找定位目标时间在文件中的偏移量"""
        file_size = os.path.getsize(log_file_path)
        
        # 如果文件过大，降低采样点数量以减少内存使用
        if file_size > 5 * 1024 * 1024 * 1024:  # 5GB以上
            print("警告: 文件过大，时间定位可能不准确")
            sample_count = 20  # 减少采样点
        elif file_size > 1024 * 1024 * 1024:  # 1GB以上
            sample_count = 50  # 减少采样点
        elif file_size > 100 * 1024 * 1024:  # 100MB以上
            sample_count = 50
        else:
            sample_count = 20
        
        print(f"使用 {sample_count} 个采样点进行时间定位...")
        
        # 创建采样点
        sample_points = []
        chunk_size = file_size // sample_count
        max_read_lines = 1000  # 每个采样点最多读取1000行，避免无限循环
        
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i in range(sample_count):
                    offset = i * chunk_size
                    if offset >= file_size:
                        break
                        
                    f.seek(offset)
                    line = ""  # 初始化line变量
                    lines_read = 0
                    
                    # 跳到下一个完整的日志条目开始
                    if offset > 0:
                        # 读取到下一个"# Time:"，但限制读取行数
                        while lines_read < max_read_lines:
                            line = f.readline()
                            lines_read += 1
                            if not line or line.startswith('# Time:'):
                                break
                        
                        if not line or lines_read >= max_read_lines:
                            continue
                    else:
                        # 如果是文件开头，直接读取第一行
                        line = f.readline()
                        if not line.startswith('# Time:'):
                            # 查找第一个Time行
                            while lines_read < max_read_lines:
                                line = f.readline()
                                lines_read += 1
                                if not line or line.startswith('# Time:'):
                                    break
                            if not line or lines_read >= max_read_lines:
                                continue
                    
                    # 读取时间戳
                    current_offset = f.tell() - len(line.encode('utf-8')) if offset > 0 else 0
                    timestamp = self._extract_timestamp_from_line(line.strip())
                    
                    if timestamp:
                        sample_points.append((current_offset, timestamp))
                        if self.debug_mode and len(sample_points) <= 5:
                            print(f"采样点 {len(sample_points)}: 偏移量={current_offset}, 时间={timestamp}")
                            
        except Exception as e:
            print(f"采样过程出错: {e}")
            return None
        
        if len(sample_points) < 2:
            print("警告: 采样点数量不足，无法进行时间定位")
            return None
        
        # 对采样点按时间排序
        sample_points.sort(key=lambda x: x[1])
        
        # 使用二分查找定位目标时间
        left, right = 0, len(sample_points) - 1
        best_offset = None
        
        while left <= right:
            mid = (left + right) // 2
            mid_time = sample_points[mid][1]
            
            if search_start:
                # 查找开始位置：找到第一个大于等于target_time的位置
                if mid_time >= target_time:
                    best_offset = sample_points[mid][0]
                    right = mid - 1
                else:
                    left = mid + 1
            else:
                # 查找结束位置：找到最后一个小于等于target_time的位置
                if mid_time <= target_time:
                    best_offset = sample_points[mid][0]
                    left = mid + 1
                else:
                    right = mid - 1
        
        # 如果是查找结束位置，需要向前扩展一些以确保包含所有相关数据
        if not search_start and best_offset is not None:
            # 向后扩展10MB或到文件末尾
            best_offset = min(best_offset + 10 * 1024 * 1024, file_size)
        
        # 如果是查找开始位置，向前扩展一些以确保不遗漏数据
        if search_start and best_offset is not None:
            # 向前扩展5MB或到文件开头
            best_offset = max(best_offset - 5 * 1024 * 1024, 0)
        
        if best_offset is not None:
            action = "开始" if search_start else "结束"
            print(f"定位{action}位置: 偏移量={best_offset}, 文件位置={best_offset/(1024*1024):.1f}MB")
        
        return best_offset

    def _extract_timestamp_from_line(self, line):
        """从日志行中提取时间戳"""
        if not line.startswith('# Time:'):
            return None
        
        # 移除"# Time:"前缀
        timestamp_str = line[7:].strip()
        
        # 尝试多种时间格式
        time_formats = [
            '%Y-%m-%dT%H:%M:%S.%f',     # 2025-03-11T14:47:34.158940
            '%Y-%m-%dT%H:%M:%S',        # 2025-03-11T14:47:34
            '%y%m%d %H:%M:%S',          # 241201 14:30:25
            '%Y-%m-%d %H:%M:%S',        # 2024-12-01 14:30:25
            '%Y%m%d %H:%M:%S',          # 20241201 14:30:25
            '%Y-%m-%d %H:%M:%S.%f',     # 2024-12-01 14:30:25.123456
        ]
        
        # 预处理时间戳：移除时区信息
        if '+08:00' in timestamp_str:
            timestamp_str = timestamp_str.replace('+08:00', '')
        elif '+0800' in timestamp_str:
            timestamp_str = timestamp_str.replace('+0800', '')
        
        for fmt in time_formats:
            try:
                timestamp = datetime.strptime(timestamp_str, fmt)
                # 如果年份是两位数，调整为完整年份
                if timestamp.year < 2024:
                    timestamp = timestamp.replace(year=timestamp.year + 2000)
                return timestamp
            except ValueError:
                continue
        
        return None

    def _parse_iso_timestamp(self, timestamp_str):
        """解析ISO格式的时间戳"""
        if not timestamp_str:
            return None
        
        # 尝试多种ISO时间格式
        iso_formats = [
            '%Y-%m-%dT%H:%M:%S.%f+08:00',    # 2025-09-11T09:51:22.214931+08:00
            '%Y-%m-%dT%H:%M:%S+08:00',       # 2025-09-11T09:51:22+08:00
            '%Y-%m-%dT%H:%M:%S.%f%z',        # 通用带时区的微秒格式
            '%Y-%m-%dT%H:%M:%S%z',           # 通用带时区格式
            '%Y-%m-%dT%H:%M:%S.%f',          # 无时区的微秒格式
            '%Y-%m-%dT%H:%M:%S',             # 无时区格式
        ]
        
        # 预处理时间戳：移除或转换时区信息
        processed_timestamp = timestamp_str
        if '+08:00' in processed_timestamp:
            processed_timestamp = processed_timestamp.replace('+08:00', '')
        elif '+0800' in processed_timestamp:
            processed_timestamp = processed_timestamp.replace('+0800', '')
        
        for fmt in iso_formats:
            try:
                if '%z' in fmt:
                    # 对于包含时区的格式，使用原始字符串
                    timestamp = datetime.strptime(timestamp_str, fmt)
                else:
                    # 对于不包含时区的格式，使用处理后的字符串
                    timestamp = datetime.strptime(processed_timestamp, fmt)
                
                # 如果解析的时间戳带有时区信息，转换为本地时间
                if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
                    # 转换为UTC然后再转换为本地时间
                    timestamp = timestamp.replace(tzinfo=None)
                
                return timestamp
            except ValueError:
                continue
        
        return None

    def _parse_traditional_timestamp(self, timestamp_str):
        """解析传统格式的时间戳"""
        if not timestamp_str:
            return None
        
        # 尝试多种传统时间格式
        time_formats = [
            '%Y-%m-%dT%H:%M:%S.%f',     # 2025-03-11T14:47:34.158940 (处理后的格式)
            '%Y-%m-%dT%H:%M:%S',        # 2025-03-11T14:47:34 (ISO格式)
            '%y%m%d %H:%M:%S',          # 241201 14:30:25
            '%Y-%m-%d %H:%M:%S',        # 2024-12-01 14:30:25
            '%Y%m%d %H:%M:%S',          # 20241201 14:30:25
            '%Y-%m-%d %H:%M:%S.%f',     # 2024-12-01 14:30:25.123456 (带微秒)
        ]
        
        # 预处理时间戳：移除时区信息
        processed_timestamp = timestamp_str
        if '+08:00' in processed_timestamp:
            processed_timestamp = processed_timestamp.replace('+08:00', '')
        elif '+0800' in processed_timestamp:
            processed_timestamp = processed_timestamp.replace('+0800', '')
        
        for fmt in time_formats:
            try:
                timestamp = datetime.strptime(processed_timestamp, fmt)
                # 如果年份是两位数，调整为完整年份
                if timestamp.year < 2024:
                    timestamp = timestamp.replace(year=timestamp.year + 2000)
                return timestamp
            except ValueError:
                continue
        
        return None

    def _looks_like_iso_timestamp(self, line):
        """检查行是否看起来像ISO时间戳"""
        if not line:
            return False
        
        # 简单的ISO时间戳模式检查
        import re
        iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        return bool(re.match(iso_pattern, line))

    def _parse_range_data(self, log_file_path, start_offset, end_offset, start_time, end_time):
        """解析指定范围内的数据"""
        range_size = end_offset - start_offset
        
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(start_offset)
            
            # 读取指定范围的数据
            data = f.read(range_size)
        
        print(f"读取范围数据: {len(data) / (1024*1024):.2f} MB")
        
        # 分割日志条目
        entries = re.split(r'# Time: ', data)
        self.stats['total_entries'] = len(entries) - 1 if len(entries) > 1 else 0
        
        print(f"找到 {self.stats['total_entries']} 个日志条目，开始解析...")
        
        processed = 0
        for i, entry in enumerate(entries[1:], 1):  # 排除第一个可能不完整的条目
            if i % 1000 == 0:
                print(f"已处理 {i}/{self.stats['total_entries']} 个条目...")
            
            try:
                if self._parse_entry_with_range(entry, start_time, end_time):
                    processed += 1
            except Exception as e:
                if self.debug_mode:
                    print(f"解析第{i}个条目时出错: {e}")
                continue
        
        self.stats['parsed_entries'] = processed
        print(f"范围解析完成，有效处理 {processed} 个条目")

    def _parse_small_file_with_range(self, log_file_path, start_time, end_time):
        """使用时间范围解析文件（流式读取，避免内存问题）"""
        print("回退到标准模式，使用流式解析避免内存问题...")
        
        # 使用流式解析，避免一次性读取整个文件
        return self._parse_standard_mode_with_range(log_file_path, start_time, end_time)
    
    def _parse_standard_mode_with_range(self, log_file_path, start_time, end_time):
        """标准模式的时间范围解析，使用流式读取"""
        entry_buffer = ""
        entry_count = 0
        processed = 0
        
        print("使用标准流式解析模式...")
        
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # 检查是否是新条目的开始 - 支持传统和ISO格式
                is_new_entry = (line.startswith('# Time: ') or 
                               self._looks_like_iso_timestamp(line.strip()))
                
                if is_new_entry:
                    # 处理前一个条目
                    if entry_buffer:
                        try:
                            if self._parse_single_entry_with_time_check(entry_buffer, start_time, end_time):
                                processed += 1
                        except Exception as e:
                            if self.debug_mode:
                                print(f"解析条目时出错: {e}")
                    
                    # 开始新条目
                    entry_buffer = line
                    entry_count += 1
                    
                    # 每处理1000个条目显示进度
                    if entry_count % 1000 == 0:
                        print(f"已处理 {entry_count} 个条目，有效解析 {processed} 个...")
                else:
                    # 继续当前条目
                    entry_buffer += line
            
            # 处理最后一个条目
            if entry_buffer:
                try:
                    if self._parse_single_entry_with_time_check(entry_buffer, start_time, end_time):
                        processed += 1
                except Exception as e:
                    if self.debug_mode:
                        print(f"解析最后条目时出错: {e}")
        
        self.stats['total_entries'] = entry_count
        self.stats['parsed_entries'] = processed
        print(f"标准模式解析完成，总条目: {entry_count}，有效处理: {processed} 个")
        
    def _parse_single_entry_with_time_check(self, entry_text, start_time, end_time):
        """解析单个条目并检查时间范围"""
        # 获取第一行来检查时间戳
        lines = entry_text.strip().split('\n')
        if not lines:
            return False
        
        first_line = lines[0].strip()
        timestamp = None
        
        # 尝试解析时间戳
        if first_line.startswith('# Time:'):
            # 传统MySQL慢日志格式
            timestamp_match = re.search(r'^# Time: (.+)$', first_line)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1).strip()
                if self.debug_mode:
                    print(f"调试: 提取的传统时间戳字符串: '{timestamp_str}'")
                timestamp = self._extract_timestamp_from_line(f"# Time: {timestamp_str}")
        else:
            # ISO时间戳格式
            if self.debug_mode:
                print(f"调试: 尝试解析ISO时间戳: '{first_line}'")
            timestamp = self._parse_iso_timestamp(first_line)
        
        if not timestamp:
            if self.debug_mode:
                print(f"调试: 时间戳解析失败")
            return False
            
        if self.debug_mode:
            print(f"调试: 解析出的时间戳: {timestamp}")
            
        # 检查时间范围
        if timestamp < start_time or timestamp > end_time:
            if self.debug_mode:
                print(f"调试: 时间戳 {timestamp} 不在范围内 ({start_time} - {end_time})")
            return False
        
        if self.debug_mode:
            print(f"调试: 时间戳检查通过，调用 _parse_entry_with_range")
        
        # 解析条目内容
        try:
            # 直接调用_parse_entry_with_range，它会处理数据添加到结果集
            result = self._parse_entry_with_range(entry_text, start_time, end_time)
            if self.debug_mode:
                print(f"调试: _parse_entry_with_range 返回结果: {result}")
            return result
        except Exception as e:
            if self.debug_mode:
                print(f"条目解析失败: {e}")
        
        return False

    def _parse_large_file_with_range(self, log_file_path, start_time, end_time):
        """使用时间范围解析大文件（流式读取）"""
        buffer = ""
        entry_count = 0
        processed = 0
        
        print("开始流式解析大文件...")
        
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
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
                        print(f"已处理 {entry_count} 个条目...")
                    
                    try:
                        if self._parse_entry_with_range(entry, start_time, end_time):
                            processed += 1
                    except Exception as e:
                        if self.debug_mode:
                            print(f"解析第{entry_count}个条目时出错: {e}")
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
                        print(f"解析最后一个条目时出错: {e}")
                    pass
        
        self.stats['total_entries'] = entry_count
        self.stats['parsed_entries'] = processed
        print(f"大文件解析完成，共处理 {entry_count} 个条目")

    def _parse_entry_with_range(self, entry, start_time, end_time):
        """使用时间范围解析单个日志条目"""
        lines = entry.strip().split('\n')
        if len(lines) < 3:
            return False
            
        # 解析时间戳 - 第一行可能是"# Time: ..."格式或纯ISO格式
        timestamp_line = lines[0].strip()
        
        # 调试信息：显示前几个时间戳的格式
        if (self.debug_mode or len(self.details) < 5):
            print(f"调试: 时间戳行 = '{timestamp_line}'")
        
        # 使用专门的时间戳提取函数
        if timestamp_line.startswith('# Time:'):
            timestamp = self._extract_timestamp_from_line(timestamp_line)
        else:
            # 处理纯ISO时间戳格式
            timestamp = self._parse_iso_timestamp(timestamp_line)
        
        if not timestamp:
            if (self.debug_mode or len(self.details) < 5):
                print(f"调试: 时间戳解析失败")
            return False
        
        if (self.debug_mode or len(self.details) < 5):
            print(f"调试: 解析成功，时间戳 = {timestamp}")
        
        # 检查时间是否在指定范围内
        if timestamp < start_time or timestamp > end_time:
            if (self.debug_mode or len(self.details) < 5):
                print(f"调试: 时间戳 {timestamp} 不在范围内 ({start_time} - {end_time})，跳过")
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
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 读取前2000个字符作为样本
                sample = f.read(2000)
                print(sample)
                print("=== 样本结束 ===\n")
        except Exception as e:
            print(f"读取样本失败: {e}")
    
    
    def _parse_small_file(self, log_file_path, start_time):
        """解析小文件（一次性读取）"""
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()
        
        # 分割日志条目 - MySQL慢日志以 "# Time:" 开始每个条目
        entries = re.split(r'# Time: ', log_content)
        self.stats['total_entries'] = len(entries) - 1  # 排除第一个空条目
        
        print(f"找到 {self.stats['total_entries']} 个日志条目，开始解析...")
        
        processed = 0
        for i, entry in enumerate(entries[1:], 1):  # 排除第一个空条目
            if i % 1000 == 0:
                print(f"已处理 {i}/{self.stats['total_entries']} 个条目...")
            
            try:
                if self._parse_entry(entry, start_time):
                    processed += 1
            except Exception as e:
                print(f"解析第{i}个条目时出错: {e}")
                continue
        
        self.stats['parsed_entries'] = processed
    
    def _parse_large_file(self, log_file_path, start_time):
        """解析大文件（流式读取）"""
        buffer = ""
        entry_count = 0
        processed = 0
        
        print("开始流式解析大文件...")
        
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
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
                        print(f"已处理 {entry_count} 个条目...")
                    
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
        print(f"大文件解析完成，共处理 {entry_count} 个条目")
    
    def _parse_entry(self, entry, start_time):
        """解析单个日志条目"""
        lines = entry.strip().split('\n')
        if len(lines) < 3:
            return False
            
        # 解析时间戳
        timestamp_line = lines[0].strip()
        
        # 调试信息：显示前几个时间戳的格式
        if len(self.details) < 5:
            print(f"调试: 时间戳行 = '{timestamp_line}'")
        
        # 首先尝试ISO格式解析
        timestamp = self._parse_iso_timestamp(timestamp_line)
        
        if not timestamp:
            # 如果ISO格式失败，尝试传统格式
            timestamp = self._parse_traditional_timestamp(timestamp_line)
        
        if not timestamp:
            if len(self.details) < 5:
                print(f"调试: 时间戳解析失败")
            return False
        
        if len(self.details) < 5:
            print(f"调试: 解析成功，时间戳 = {timestamp}")
        
        # 只处理最近N天的日志
        if timestamp < start_time:
            if len(self.details) < 5:
                print(f"调试: 时间戳 {timestamp} 早于起始时间 {start_time}，跳过")
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
                    print(f"调试: 用户主机行 = '{user_host_line}'")
            elif line.startswith('# Query_time:'):
                # 解析性能指标
                match = re.search(r'Query_time:\s*([\d.]+)\s*Lock_time:\s*([\d.]+)\s*Rows_sent:\s*(\d+)\s*Rows_examined:\s*(\d+)', line)
                if match:
                    query_time = float(match.group(1))
                    lock_time = float(match.group(2))
                    rows_sent = int(match.group(3))
                    rows_examined = int(match.group(4))
                if len(self.details) < 5:
                    print(f"调试: 查询时间行 = '{line}'")
            elif not line.startswith('#') and line.strip():
                sql_start_idx = i
                if len(self.details) < 5:
                    print(f"调试: SQL开始索引 = {sql_start_idx}, 行 = '{line[:100]}...'")
                break
        
        if sql_start_idx == -1 or not user_host_line:
            if len(self.details) < 5:
                print(f"调试: SQL开始索引({sql_start_idx}) 或用户主机行({user_host_line}) 缺失")
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
                    print(f"调试: 匹配成功，用户={username}, 数据库={dbname}")
                break
        else:
            if len(self.details) < 5:
                print(f"调试: 用户主机行匹配失败: {user_host_line}")
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
                        print(f"调试: 从USE语句中提取数据库名: {dbname}")
                    break
        
        # 如果没有找到USE语句，尝试根据用户名推断数据库名
        if dbname == 'unknown' and username != 'unknown':
            dbname = self.infer_database_from_username(username)
            if len(self.details) < 5:
                if dbname != 'unknown':
                    print(f"调试: 根据用户名 '{username}' 推断数据库名为 '{dbname}'")
                else:
                    print(f"调试: 未找到USE语句且用户名 '{username}' 无匹配映射，数据库名保持为unknown")
        elif dbname == 'unknown' and len(self.details) < 5:
            print(f"调试: 未找到USE语句且用户名为unknown，数据库名保持为unknown")
        
        # 清理SQL语句：移除USE语句，因为它不是实际的查询
        cleaned_sql = re.sub(r'USE\s+`?\w+`?\s*;\s*', '', raw_sql, flags=re.IGNORECASE).strip()
        
        # 如果清理后的SQL为空或太短，使用原SQL
        if not cleaned_sql or len(cleaned_sql) < 10:
            cleaned_sql = raw_sql
            
        if not cleaned_sql or len(cleaned_sql) < 10:  # 忽略过短的SQL
            if len(self.details) < 5:
                print(f"调试: SQL太短或为空: '{cleaned_sql}'")
            return False
        
        # 使用清理后的SQL作为实际查询
        raw_sql = cleaned_sql
        
        # 过滤掉包含 "index not used" 关键字的语句
        if re.search(r'index\s+not\s+used', raw_sql, re.IGNORECASE):
            if len(self.details) < 5:
                print(f"调试: 跳过包含'index not used'关键字的语句")
            return False
        
        # 只记录执行时间超过阈值的慢查询
        if query_time < self.min_query_time:
            if len(self.details) < 5:
                print(f"调试: 跳过执行时间{query_time}s小于{self.min_query_time}秒的查询")
            return False
        
        if len(self.details) < 5:
            print(f"调试: 成功解析条目，SQL长度={len(raw_sql)}，执行时间={query_time}s")
        
        # 检查SQL长度并给出警告（但不截断）
        if len(raw_sql) > 100000:  # 100KB
            print(f"警告: 发现超长SQL语句（{len(raw_sql)}字符），可能影响性能")
        
        # 规范化SQL
        normalized_sql = self.normalize_sql(raw_sql)
        checksum = self.generate_checksum(normalized_sql)
        
        # 存储指纹信息
        if checksum not in self.fingerprints:
            self.fingerprints[checksum] = {
                'checksum': checksum,
                'normalized_sql': normalized_sql,
                'raw_sql': raw_sql,  # 存储完整的原始SQL，不截断
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
            'sql_text': raw_sql,  # 存储完整的SQL文本，不截断
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
                    print(f"调试: 用户主机行 = '{user_host_line}'")
            elif line.startswith('# Query_time:'):
                # 解析性能指标
                match = re.search(r'Query_time:\s*([\d.]+)\s*Lock_time:\s*([\d.]+)\s*Rows_sent:\s*(\d+)\s*Rows_examined:\s*(\d+)', line)
                if match:
                    query_time = float(match.group(1))
                    lock_time = float(match.group(2))
                    rows_sent = int(match.group(3))
                    rows_examined = int(match.group(4))
                if (self.debug_mode or len(self.details) < 5):
                    print(f"调试: 查询时间行 = '{line}'")
            elif not line.startswith('#') and line.strip():
                sql_start_idx = i
                if (self.debug_mode or len(self.details) < 5):
                    print(f"调试: SQL开始索引 = {sql_start_idx}, 行 = '{line[:100]}...'")
                break
        
        if sql_start_idx == -1 or not user_host_line:
            if (self.debug_mode or len(self.details) < 5):
                print(f"调试: SQL开始索引({sql_start_idx}) 或用户主机行({user_host_line}) 缺失")
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
                    print(f"调试: 匹配成功，用户={username}, 数据库={dbname}")
                break
        else:
            if (self.debug_mode or len(self.details) < 5):
                print(f"调试: 用户主机行匹配失败: {user_host_line}")
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
                        print(f"调试: 从USE语句中提取数据库名: {dbname}")
                    break
        
        # 如果没有找到USE语句，尝试根据用户名推断数据库名
        if dbname == 'unknown' and username != 'unknown':
            dbname = self.infer_database_from_username(username)
            if (self.debug_mode or len(self.details) < 5):
                if dbname != 'unknown':
                    print(f"调试: 根据用户名 '{username}' 推断数据库名为 '{dbname}'")
                else:
                    print(f"调试: 未找到USE语句且用户名 '{username}' 无匹配映射，数据库名保持为unknown")
        elif dbname == 'unknown' and (self.debug_mode or len(self.details) < 5):
            print(f"调试: 未找到USE语句且用户名为unknown，数据库名保持为unknown")
        
        # 清理SQL语句：移除USE语句，因为它不是实际的查询
        cleaned_sql = re.sub(r'USE\s+`?\w+`?\s*;\s*', '', raw_sql, flags=re.IGNORECASE).strip()
        
        # 如果清理后的SQL为空或太短，使用原SQL
        if not cleaned_sql or len(cleaned_sql) < 10:
            cleaned_sql = raw_sql
            
        if not cleaned_sql or len(cleaned_sql) < 10:  # 忽略过短的SQL
            if (self.debug_mode or len(self.details) < 5):
                print(f"调试: SQL太短或为空: '{cleaned_sql}'")
            return False
        
        # 使用清理后的SQL作为实际查询
        raw_sql = cleaned_sql
        
        # 过滤掉包含 "index not used" 关键字的语句
        if re.search(r'index\s+not\s+used', raw_sql, re.IGNORECASE):
            if (self.debug_mode or len(self.details) < 5):
                print(f"调试: 跳过包含'index not used'关键字的语句")
            return False
        
        # 只记录执行时间超过阈值的慢查询
        if query_time < self.min_query_time:
            if (self.debug_mode or len(self.details) < 5):
                print(f"调试: 跳过执行时间{query_time}s小于{self.min_query_time}秒的查询")
            return False
        
        if (self.debug_mode or len(self.details) < 5):
            print(f"调试: 成功解析条目，SQL长度={len(raw_sql)}，执行时间={query_time}s")
        
        # 检查SQL长度并给出警告（但不截断）
        if len(raw_sql) > 100000:  # 100KB
            print(f"警告: 发现超长SQL语句（{len(raw_sql)}字符），可能影响性能")
        
        # 规范化SQL
        normalized_sql = self.normalize_sql(raw_sql)
        checksum = self.generate_checksum(normalized_sql)
        
        # 存储指纹信息
        if checksum not in self.fingerprints:
            self.fingerprints[checksum] = {
                'checksum': checksum,
                'normalized_sql': normalized_sql,
                'raw_sql': raw_sql,  # 存储完整的原始SQL，不截断
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
            'sql_text': raw_sql,  # 存储完整的原始SQL，不截断
            'formatted_sql': self.format_sql(raw_sql),  # 格式化完整的SQL
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
        
        print(f"\n开始保存数据到数据库...")
        print(f"  指纹记录: {len(self.fingerprints)}")
        print(f"  详细记录: {len(self.details)}")
        
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # 检查并报告超长SQL
            self._check_sql_lengths()
            
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
            print(f"  已保存 {cursor.rowcount} 条指纹记录")
            
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
                    detail.get('formatted_sql', detail.get('sql_text', '')),  # 优先使用格式化SQL，回退到原始SQL
                    detail['timestamp'],
                    detail['query_time'],
                    detail['lock_time'],
                    detail['rows_sent'],
                    detail['rows_examined']
                ))
            
            cursor.executemany(detail_sql, detail_data)
            print(f"  已保存 {cursor.rowcount} 条详细记录")
            
            conn.commit()
            print("数据保存成功！")
            
            # 显示保存统计
            self._show_save_statistics(cursor)
            
        except pymysql.err.DataError as e:
            conn.rollback()
            if "Data too long for column" in str(e):
                print(f"\n数据库字段长度不足: {e}")
                print("\n解决方案:")
                print("1. 运行数据库升级脚本: python upgrade_database.py")
                print("2. 或手动执行SQL: ALTER TABLE slow_query_fingerprint MODIFY COLUMN raw_sql LONGTEXT;")
                print("3. 或手动执行SQL: ALTER TABLE slow_query_detail MODIFY COLUMN sql_text LONGTEXT;")
                print("\n当前数据库字段类型可能是TEXT（最大64KB），需要升级为LONGTEXT（最大4GB）")
            else:
                print(f"数据保存失败: {e}")
            raise
        except Exception as e:
            conn.rollback()
            print(f"保存数据失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def _check_sql_lengths(self):
        """检查SQL长度统计"""
        max_raw_sql_len = 0
        max_formatted_sql_len = 0
        long_sql_count = 0
        
        # 检查指纹表的SQL长度
        for fp in self.fingerprints.values():
            if fp['raw_sql']:
                sql_len = len(fp['raw_sql'])
                max_raw_sql_len = max(max_raw_sql_len, sql_len)
                if sql_len > 65535:  # TEXT类型的限制
                    long_sql_count += 1
        
        # 检查详细表的SQL长度
        for detail in self.details:
            formatted_sql = detail.get('formatted_sql', detail.get('sql_text', ''))
            if formatted_sql:
                sql_len = len(formatted_sql)
                max_formatted_sql_len = max(max_formatted_sql_len, sql_len)
                if sql_len > 65535:  # TEXT类型的限制
                    long_sql_count += 1
        
        print(f"\nSQL长度统计:")
        print(f"  最大原始SQL长度: {max_raw_sql_len:,} 字符")
        print(f"  最大格式化SQL长度: {max_formatted_sql_len:,} 字符")
        
        if long_sql_count > 0:
            print(f"  超过64KB的SQL数量: {long_sql_count}")
            print(f"  警告: 检测到超长SQL，如果数据库字段是TEXT类型将无法保存！")
            print(f"  建议运行: python upgrade_database.py 升级字段类型")
        else:
            print(f"  所有SQL长度都在64KB以内，可以正常保存")
    
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
            
            print(f"\n数据库当前统计:")
            print(f"  总指纹数量: {total_fingerprints}")
            print(f"  总详细记录: {total_details}")
            if recent_stats[0]:
                print(f"  最近7天记录: {recent_stats[0]} 条")
                print(f"  时间范围: {recent_stats[1]} 到 {recent_stats[2]}")
                
        except Exception as e:
            print(f"获取统计信息失败: {e}")

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
                      help=f'慢日志文件路径 (默认: {SLOW_LOG_PATH})')
    
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
    
    parser.add_argument('--no-time-optimization', action='store_true',
                      help='禁用时间范围优化，强制遍历整个文件（用于调试）')
    
    parser.add_argument('--optimization-threshold', type=int, default=100,
                      help='启用时间优化的文件大小阈值（MB），默认100MB以上的文件使用优化')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MySQL 慢查询日志解析工具")
    print("=" * 60)
    print(f"日志文件路径: {args.log_path}")
    print(f"最小查询时间阈值: {args.min_time} 秒")
    
    # 显示用户名到数据库名的映射配置
    if USER_TO_DATABASE_MAPPING:
        print(f"用户名到数据库名映射配置:")
        for username, dbname in USER_TO_DATABASE_MAPPING.items():
            print(f"  {username} -> {dbname}")
    else:
        print("未配置用户名到数据库名的映射")
    
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
                raise ValueError(f"无法解析开始时间格式: {args.start}")
                
            for fmt in time_formats:
                try:
                    end_time = datetime.strptime(args.end, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"无法解析结束时间格式: {args.end}")
            
            if start_time >= end_time:
                raise ValueError("开始时间必须早于结束时间")
                
            print(f"解析时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 到 {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except ValueError as e:
            print(f"时间参数错误: {e}")
            print("时间格式示例: 2025-01-01 或 '2025-01-01 10:30:00'")
            sys.exit(1)
            
    else:
        # 使用天数回溯
        days_back = args.days
        start_time = datetime.now() - timedelta(days=days_back)
        end_time = datetime.now()
        print(f"解析最近{days_back}天的慢查询（从 {start_time.strftime('%Y-%m-%d %H:%M:%S')} 开始）")
    
    # 检查文件是否存在
    if not os.path.exists(args.log_path):
        print(f"错误: 慢日志文件不存在: {args.log_path}")
        print("请确认路径是否正确，或通过参数指定:")
        print(f"python {sys.argv[0]} /path/to/slow.log")
        sys.exit(1)
    
    try:
        # 创建解析器
        log_parser = SlowLogParser(min_query_time=args.min_time)
        log_parser.debug_mode = args.debug
        
        # 解析慢日志
        use_optimization = not args.no_time_optimization
        log_parser.parse_slow_log_with_time_range(
            args.log_path, 
            start_time, 
            end_time,
            use_optimization=use_optimization,
            optimization_threshold=args.optimization_threshold
        )
        
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
                print(f"  主机: {DB_CONFIG['host']}")
                print(f"  用户: {DB_CONFIG['user']}")
                print(f"  数据库: {DB_CONFIG['database']}")
                
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
        print(f"程序执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
