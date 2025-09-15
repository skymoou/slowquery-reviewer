#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL慢查询日志解析器 - 精简版
功能包括：SQL格式化、完整存储、用户名映射、时间优化、ISO时间戳支持
"""

import os
import re
import hashlib
import pymysql
from datetime import datetime, timedelta
import argparse

class SlowLogParser:
    def __init__(self, min_query_time=5.0):
        """初始化解析器"""
        self.min_query_time = min_query_time
        self.details = []
        self.fingerprints = {}
        self.stats = {'total_entries': 0, 'parsed_entries': 0, 'unique_fingerprints': 0, 'date_range': {'start': None, 'end': None}}
        self.debug_mode = False
        
        # 用户名映射配置（直接写在脚本中）
        self.username_mapping = self._get_username_mapping()
        if self.username_mapping:
            print("已加载用户名映射配置")
        
        # 用户黑名单配置（这些用户的慢查询将被忽略）
        self.username_blacklist = self._get_username_blacklist()
        if self.username_blacklist:
            print(f"已加载用户黑名单配置: {', '.join(self.username_blacklist)}")

    def _get_username_mapping(self):
        """获取用户名映射配置"""
        return {
            # 在这里直接配置用户名到数据库的映射关系
            # 格式: 'username': 'database_name'
            'act_user':'posx_act',
            'act_user_prd':'posx_act',
            'aegean_user':'posx_aegean',
            'prd_user':'posx_prd',
            'tras_user':'posx_prd',
            'agentuser':'posx_agent',
            'bss_user':'posx_bss',
            'pms_user':'posx_pms',
            'pps_user':'posx_pps',
            'risk_user':'posx_risk',
            'stock_user':'posx_stock',
            'dc_user':'posx_dc',
            'dls_user':'posx_dlc',
            'dms_user':'posx_dms',
            'drs_user':'posx_drs',
            'ifs_user':'ifs_gateway',
            'ifsedu_user':'ifs_education',
            'k8snacos_user':'wpk8s_nacos',
            'mer_user':'posx_mer',
            'mer_user_prd':'posx_mer',
            'nacos_user':'wpk8s_nacos',
            'rhk_user':'reassure_housekeeper',
            'sas_user':'posx_sas',
            'tcs_user':'posx_tcs',
            'wop_user':'posx_wop',
            'wos_user':'posx_wos',
            'xxl_user':'xxl_job',
            'yeepay_user':'posx_yeepay',
            'dls_o':'posx_dls',
        }

    def _get_username_blacklist(self):
        """获取用户黑名单配置"""
        return {
            # 在这里配置需要忽略的用户名
            # 这些用户的慢查询记录将不会被解析和存储
            'pmm_user',      # PMM监控用户
            'root',          # 系统管理员
            'mysql',         # MySQL系统用户
            'monitor',       # 监控用户
            'backup',        # 备份用户
            'replication',   # 复制用户
            'mysql.sys',     # MySQL系统账户
            'mysql.session', # MySQL会话账户
            'admin',         # 通用管理员（如果不需要记录）
            'pt_user',       # 归档用户
            'archery_user',  # archeryuser
            # 可以根据需要添加更多用户名
        }

    def normalize_sql(self, sql):
        """规范化SQL语句"""
        if not sql or not sql.strip():
            return ""
        
        # 基础清理
        normalized = re.sub(r'\s+', ' ', sql.strip())
        
        # 参数化处理
        patterns = [
            (r"'[^']*'", "'?'"),  # 字符串参数
            (r'"[^"]*"', "'?'"),  # 双引号字符串
            (r'\b\d+\b', '?'),    # 数字参数
            (r'IN\s*\([^)]+\)', 'IN (?)'),  # IN子句
            (r'VALUES\s*\([^)]+\)', 'VALUES (?)'),  # VALUES子句
        ]
        
        for pattern, replacement in patterns:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        return normalized.upper()

    def generate_checksum(self, normalized_sql):
        """生成SQL指纹"""
        return hashlib.md5(normalized_sql.encode('utf-8')).hexdigest()

    def infer_database_from_username(self, username):
        """根据用户名推断数据库名"""
        if username in self.username_mapping:
            return self.username_mapping[username]
        return 'unknown'

    def format_sql(self, sql):
        """格式化SQL语句 - 9步优化流程"""
        if not sql or len(sql.strip()) < 5:
            return sql
            
        try:
            # 1. 基础清理
            formatted = sql.strip()
            
            # 2. 移除多余空白
            formatted = re.sub(r'\s+', ' ', formatted)
            
            # 3. 关键字换行
            keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT', 
                       'INSERT INTO', 'UPDATE', 'DELETE FROM', 'UNION', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN']
            
            for keyword in keywords:
                formatted = re.sub(f'\\b{keyword}\\b', f'\n{keyword}', formatted, flags=re.IGNORECASE)
            
            # 4. AND/OR换行
            formatted = re.sub(r'\b(AND|OR)\b', r'\n\1', formatted, flags=re.IGNORECASE)
            
            # 5. 逗号后换行（在SELECT子句中）
            formatted = re.sub(r',(\s*[a-zA-Z_])', r',\n\1', formatted)
            
            # 6. 清理多余换行
            formatted = re.sub(r'\n\s*\n', '\n', formatted)
            formatted = re.sub(r'^\s*\n', '', formatted)
            
            # 7. 关键字大写
            for keyword in keywords + ['AND', 'OR', 'SET', 'VALUES', 'ON', 'AS', 'IS', 'NULL', 'NOT', 'IN', 'EXISTS']:
                formatted = re.sub(f'\\b{keyword.lower()}\\b', keyword, formatted, flags=re.IGNORECASE)
                formatted = re.sub(f'\\b{keyword.upper()}\\b', keyword, formatted)
            
            # 8. 缩进处理
            lines = formatted.split('\n')
            indented_lines = []
            for line in lines:
                line = line.strip()
                if line:
                    if any(line.startswith(kw) for kw in ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT', 'INSERT', 'UPDATE', 'DELETE']):
                        indented_lines.append(line)
                    else:
                        indented_lines.append('  ' + line)
            
            # 9. 最终整理
            formatted = '\n'.join(indented_lines)
            return formatted.strip()
            
        except Exception as e:
            return sql  # 格式化失败时返回原SQL

    def parse_slow_log_with_time_range(self, log_file_path, start_time, end_time, use_optimization=True, optimization_threshold=100):
        """主解析方法 - 支持时间范围和优化"""
        print(f"解析时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 到 {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 清空之前的解析结果
        self.details = []
        self.fingerprints = {}
        self.stats = {'total_entries': 0, 'parsed_entries': 0, 'unique_fingerprints': 0, 'date_range': {'start': None, 'end': None}}
        
        if not os.path.exists(log_file_path):
            raise FileNotFoundError(f"慢日志文件不存在: {log_file_path}")
        
        file_size = os.path.getsize(log_file_path)
        print(f"慢日志文件大小: {file_size / (1024*1024):.2f} MB")
        
        self._show_log_sample(log_file_path)
        
        # 根据文件大小选择解析策略
        if file_size < 50 * 1024 * 1024:  # 50MB以下
            print("使用标准读取模式...")
        else:
            print("回退到标准模式，使用流式解析避免内存问题...")
        
        # 使用统一的流式解析方法
        self._parse_with_streaming(log_file_path, start_time, end_time)
        
        self.stats['unique_fingerprints'] = len(self.fingerprints)
        print(f"\n解析完成统计:")
        print(f"  总日志条目: {self.stats['total_entries']}")
        print(f"  成功解析: {self.stats['parsed_entries']}")
        print(f"  唯一SQL指纹: {self.stats['unique_fingerprints']}")
        print(f"  详细执行记录: {len(self.details)}")
        if self.stats['date_range']['start']:
            print(f"  时间范围: {self.stats['date_range']['start']} 到 {self.stats['date_range']['end']}")
        
        return self.details

    def _parse_with_streaming(self, log_file_path, start_time, end_time):
        """统一的流式解析方法"""
        entry_buffer = ""
        entry_count = 0
        processed = 0
        
        print("使用标准流式解析模式...")
        
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # 检查是否是新条目的开始
                if self._is_entry_start(line):
                    # 处理前一个条目
                    if entry_buffer:
                        if self._parse_single_entry(entry_buffer, start_time, end_time):
                            processed += 1
                    
                    # 开始新条目
                    entry_buffer = line
                    entry_count += 1
                    
                    if entry_count % 1000 == 0:
                        print(f"已处理 {entry_count} 个条目，有效解析 {processed} 个...")
                else:
                    entry_buffer += line
            
            # 处理最后一个条目
            if entry_buffer:
                if self._parse_single_entry(entry_buffer, start_time, end_time):
                    processed += 1
        
        self.stats['total_entries'] = entry_count
        self.stats['parsed_entries'] = processed
        print(f"标准模式解析完成，总条目: {entry_count}，有效处理: {processed} 个")

    def _is_entry_start(self, line):
        """检查是否是条目开始"""
        return (line.startswith('# Time: ') or 
                bool(re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', line.strip())))

    def _parse_single_entry(self, entry_text, start_time, end_time):
        """解析单个条目"""
        lines = entry_text.strip().split('\n')
        if not lines:
            return False
        
        # 解析时间戳
        timestamp = self._parse_timestamp(lines[0].strip())
        if not timestamp:
            return False
        
        # 检查时间范围
        if timestamp < start_time or timestamp > end_time:
            return False
        
        # 更新时间范围统计
        if not self.stats['date_range']['start'] or timestamp < self.stats['date_range']['start']:
            self.stats['date_range']['start'] = timestamp
        if not self.stats['date_range']['end'] or timestamp > self.stats['date_range']['end']:
            self.stats['date_range']['end'] = timestamp
        
        return self._parse_entry_content(lines, timestamp)

    def _parse_timestamp(self, timestamp_line):
        """统一时间戳解析"""
        # ISO格式
        if re.match(r'^\d{4}-\d{2}-\d{2}T', timestamp_line):
            return self._parse_iso_timestamp(timestamp_line)
        
        # 传统MySQL格式
        if timestamp_line.startswith('# Time:'):
            return self._extract_timestamp_from_line(timestamp_line)
        
        return None

    def _parse_iso_timestamp(self, timestamp_str):
        """解析ISO时间戳"""
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f+08:00', '%Y-%m-%dT%H:%M:%S+08:00',
            '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'
        ]
        
        # 移除时区信息
        cleaned = timestamp_str.replace('+08:00', '').replace('+0800', '')
        
        for fmt in formats:
            try:
                if '+08:00' in fmt and '+08:00' in timestamp_str:
                    return datetime.strptime(timestamp_str, fmt).replace(tzinfo=None)
                else:
                    return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
        return None

    def _extract_timestamp_from_line(self, line):
        """解析传统MySQL时间戳"""
        if not line.startswith('# Time:'):
            return None
        
        timestamp_str = line[7:].strip()
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%y%m%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S', '%Y%m%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f'
        ]
        
        # 移除时区
        timestamp_str = timestamp_str.replace('+08:00', '').replace('+0800', '')
        
        for fmt in formats:
            try:
                timestamp = datetime.strptime(timestamp_str, fmt)
                if timestamp.year < 2024:
                    timestamp = timestamp.replace(year=timestamp.year + 2000)
                return timestamp
            except ValueError:
                continue
        return None

    def _parse_entry_content(self, lines, timestamp):
        """解析条目内容"""
        # 解析用户和性能指标
        username, dbname = 'unknown', 'unknown'
        query_time = lock_time = rows_sent = rows_examined = 0
        sql_start_idx = -1
        
        for i, line in enumerate(lines[1:], 1):
            if line.startswith('# User@Host:'):
                # 提取用户名
                user_match = re.search(r'# User@Host:\s*(\w+)', line)
                if user_match:
                    username = user_match.group(1)
                    
            elif line.startswith('# Query_time:'):
                # 解析性能指标
                match = re.search(r'Query_time:\s*([\d.]+)\s*Lock_time:\s*([\d.]+)\s*Rows_sent:\s*(\d+)\s*Rows_examined:\s*(\d+)', line)
                if match:
                    query_time, lock_time = float(match.group(1)), float(match.group(2))
                    rows_sent, rows_examined = int(match.group(3)), int(match.group(4))
                    
            elif not line.startswith('#') and line.strip():
                sql_start_idx = i
                break
        
        if sql_start_idx == -1:
            return False
        
        # 提取SQL
        sql_lines = lines[sql_start_idx:]
        raw_sql = '\n'.join(sql_lines).strip()
        raw_sql = re.sub(r'SET timestamp=\d+;?\s*$', '', raw_sql, flags=re.IGNORECASE).rstrip(';').strip()
        
        # 提取数据库名
        use_match = re.search(r'USE\s+`?([^`\s;]+)`?\s*;?', raw_sql, re.IGNORECASE)
        if use_match:
            dbname = use_match.group(1)
            raw_sql = re.sub(r'USE\s+`?\w+`?\s*;\s*', '', raw_sql, flags=re.IGNORECASE).strip()
        elif username != 'unknown':
            dbname = self.infer_database_from_username(username)
        
        # 过滤条件
        if (not raw_sql or len(raw_sql) < 10 or 
            query_time < self.min_query_time or 
            'index not used' in raw_sql.lower() or
            username in self.username_blacklist):  # 用户黑名单过滤
            
            # 记录被过滤的原因（调试模式）
            if self.debug_mode and username in self.username_blacklist:
                print(f"过滤黑名单用户: {username}")
            
            return False
        
        # 生成指纹
        normalized_sql = self.normalize_sql(raw_sql)
        checksum = self.generate_checksum(normalized_sql)
        
        # 存储指纹
        if checksum not in self.fingerprints:
            self.fingerprints[checksum] = {
                'checksum': checksum, 'normalized_sql': normalized_sql,
                'raw_sql': raw_sql, 'username': username, 'dbname': dbname,
                'first_seen': timestamp, 'last_seen': timestamp,
                'reviewed_status': '待优化', 'comments': None
            }
        else:
            fp = self.fingerprints[checksum]
            fp['last_seen'] = max(fp['last_seen'], timestamp)
            fp['first_seen'] = min(fp['first_seen'], timestamp)
        
        # 存储详细记录
        self.details.append({
            'checksum': checksum, 'sql_text': raw_sql,
            'formatted_sql': self.format_sql(raw_sql), 'timestamp': timestamp,
            'query_time': query_time, 'lock_time': lock_time,
            'rows_sent': rows_sent, 'rows_examined': rows_examined,
            'username': username, 'dbname': dbname
        })
        
        return True

    def _show_log_sample(self, log_file_path):
        """显示日志样本"""
        print("\n=== 日志文件样本 ===")
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                print(f.read(2000))
            print("=== 样本结束 ===\n")
        except Exception as e:
            print(f"读取样本失败: {e}")

    def save_to_database(self):
        """保存到数据库"""
        if not self.fingerprints:
            print("没有数据需要保存")
            return
        
        try:
            # 连接数据库
            connection = pymysql.connect(
                host='172.16.176.70', user='root', password='SlowQ#123',
                database='slow_query_analysis', charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                # 保存指纹数据（使用原来的表名和结构）
                for fp in self.fingerprints.values():
                    cursor.execute("""
                        INSERT INTO slow_query_fingerprint (checksum, normalized_sql, raw_sql, username, dbname, 
                                                           first_seen, last_seen, reviewed_status, comments)
                        VALUES (%(checksum)s, %(normalized_sql)s, %(raw_sql)s, %(username)s, %(dbname)s,
                               %(first_seen)s, %(last_seen)s, %(reviewed_status)s, %(comments)s)
                        ON DUPLICATE KEY UPDATE
                        first_seen = LEAST(first_seen, VALUES(first_seen)),
                        last_seen = GREATEST(last_seen, VALUES(last_seen)),
                        raw_sql = VALUES(raw_sql)
                    """, fp)
                
                # 保存详细记录（使用原来的表名和结构）
                for detail in self.details:
                    cursor.execute("""
                        INSERT IGNORE INTO slow_query_detail (checksum, sql_text, timestamp, 
                                                             query_time, lock_time, rows_sent, rows_examined)
                        VALUES (%(checksum)s, %(formatted_sql)s, %(timestamp)s,
                               %(query_time)s, %(lock_time)s, %(rows_sent)s, %(rows_examined)s)
                    """, detail)
                
                connection.commit()
                print(f"\n数据保存成功:")
                print(f"  SQL指纹记录: {len(self.fingerprints)} 条")
                print(f"  详细执行记录: {len(self.details)} 条")
                
        except Exception as e:
            print(f"数据库保存失败: {e}")
        finally:
            if 'connection' in locals():
                connection.close()

def _parse_time_range(args):
    """解析时间范围参数"""
    try:
        # 优先使用精确的时间范围
        if args.start_time and args.end_time:
            start_time = datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S')
            end_time = datetime.strptime(args.end_time, '%Y-%m-%d %H:%M:%S')
            print(f"使用自定义时间范围: {start_time} 到 {end_time}")
            return start_time, end_time
        
        # 使用日期范围（如果只指定了日期）
        elif args.start_date or args.end_date:
            if args.start_date:
                start_time = datetime.strptime(args.start_date + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
            else:
                # 如果没有指定开始日期，默认从一周前开始
                start_time = datetime.now() - timedelta(days=7)
            
            if args.end_date:
                end_time = datetime.strptime(args.end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
            else:
                # 如果没有指定结束日期，默认到当前时间
                end_time = datetime.now()
            
            print(f"使用自定义日期范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 到 {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return start_time, end_time
        
        # 使用单独的开始时间或结束时间
        elif args.start_time:
            start_time = datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S')
            end_time = datetime.now()
            print(f"从指定时间到现在: {start_time} 到 {end_time}")
            return start_time, end_time
        
        elif args.end_time:
            end_time = datetime.strptime(args.end_time, '%Y-%m-%d %H:%M:%S')
            start_time = end_time - timedelta(days=args.days)
            print(f"从{args.days}天前到指定时间: {start_time} 到 {end_time}")
            return start_time, end_time
        
        # 默认使用days参数
        else:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=args.days)
            print(f"使用默认时间范围: 最近{args.days}天")
            return start_time, end_time
            
    except ValueError as e:
        print(f"时间格式错误: {e}")
        print("请使用格式: YYYY-MM-DD HH:MM:SS (如: 2025-09-12 10:30:00)")
        print("或使用日期格式: YYYY-MM-DD (如: 2025-09-12)")
        exit(1)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MySQL慢查询日志解析器')
    parser.add_argument('--log-file', default='/data/mysql/log/slow.log', help='慢日志文件路径')
    parser.add_argument('--days', type=int, default=7, help='解析最近N天的日志')
    parser.add_argument('--min-time', type=float, default=5.0, help='最小查询时间阈值(秒)')
    parser.add_argument('--save-db', action='store_true', help='保存到数据库')
    
    # 自定义时间范围参数
    parser.add_argument('--start-time', type=str, help='开始时间 (格式: YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end-time', type=str, help='结束时间 (格式: YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--start-date', type=str, help='开始日期 (格式: YYYY-MM-DD，时间默认00:00:00)')
    parser.add_argument('--end-date', type=str, help='结束日期 (格式: YYYY-MM-DD，时间默认23:59:59)')
    
    # 用户过滤参数
    parser.add_argument('--disable-blacklist', action='store_true', help='禁用用户黑名单过滤')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，显示过滤详情')
    
    args = parser.parse_args()
    
    # 创建解析器
    slow_parser = SlowLogParser(min_query_time=args.min_time)
    
    # 设置调试模式
    if args.debug:
        slow_parser.debug_mode = True
        print("调试模式已启用")
    
    # 处理黑名单设置
    if args.disable_blacklist:
        slow_parser.username_blacklist = set()  # 清空黑名单
        print("用户黑名单已禁用")
    
    # 解析自定义时间范围
    start_time, end_time = _parse_time_range(args)
    
    try:
        # 解析日志
        print(f"开始解析慢查询日志: {args.log_file}")
        print(f"查询时间阈值: {args.min_time}秒")
        
        results = slow_parser.parse_slow_log_with_time_range(args.log_file, start_time, end_time)
        
        # 保存到数据库
        if args.save_db:
            slow_parser.save_to_database()
        
        print("\n解析完成!")
        
    except Exception as e:
        print(f"解析失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
