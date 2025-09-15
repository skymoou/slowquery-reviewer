#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
慢日志解析和导入脚本
用于解析MySQL慢查询日志并导入到数据库中
"""

import re
import hashlib
import mysql.connector
from datetime import datetime, timedelta
import sys
import os
from config import DB_CONFIG

class SlowLogParser:
    def __init__(self):
        self.fingerprints = {}
        self.details = []
    
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
        
        # 移除ORDER BY后的具体字段（保留关键字）
        sql = re.sub(r'ORDER\s+BY\s+[^;]+', 'ORDER BY ?', sql, flags=re.IGNORECASE)
        
        return sql.upper()
    
    def generate_checksum(self, normalized_sql):
        """生成SQL指纹的校验和"""
        return hashlib.md5(normalized_sql.encode('utf-8')).hexdigest()
    
    def parse_slow_log(self, log_content, days_back=7):
        """解析慢日志内容"""
        # 计算起始时间
        start_time = datetime.now() - timedelta(days=days_back)
        
        # 分割日志条目
        entries = re.split(r'# Time: ', log_content)[1:]  # 排除第一个空条目
        
        for entry in entries:
            try:
                self._parse_entry(entry, start_time)
            except Exception as e:
                print(f"解析条目时出错: {e}")
                continue
    
    def _parse_entry(self, entry, start_time):
        """解析单个日志条目"""
        lines = entry.strip().split('\n')
        if len(lines) < 3:
            return
            
        # 解析时间戳
        timestamp_line = lines[0]
        try:
            timestamp = datetime.strptime(timestamp_line.strip(), '%y%m%d %H:%M:%S')
            # 调整年份（假设是2024年之后的日志）
            if timestamp.year < 2024:
                timestamp = timestamp.replace(year=timestamp.year + 2000)
        except ValueError:
            try:
                # 尝试其他时间格式
                timestamp = datetime.strptime(timestamp_line.strip(), '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return
        
        # 只处理最近N天的日志
        if timestamp < start_time:
            return
        
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
            elif line.startswith('# Query_time:'):
                # 解析性能指标
                match = re.search(r'Query_time:\s*([\d.]+)\s*Lock_time:\s*([\d.]+)\s*Rows_sent:\s*(\d+)\s*Rows_examined:\s*(\d+)', line)
                if match:
                    query_time = float(match.group(1))
                    lock_time = float(match.group(2))
                    rows_sent = int(match.group(3))
                    rows_examined = int(match.group(4))
            elif not line.startswith('#') and line.strip():
                sql_start_idx = i
                break
        
        if sql_start_idx == -1 or not user_host_line:
            return
        
        # 提取用户名和数据库
        user_match = re.search(r'# User@Host:\s*(\w+)\[(\w*)\]\s*@\s*\[(.*?)\].*?db:\s*(\w+)', user_host_line)
        if not user_match:
            return
        
        username = user_match.group(1)
        dbname = user_match.group(4)
        
        # 提取SQL语句
        sql_lines = lines[sql_start_idx:]
        raw_sql = '\n'.join(sql_lines).strip()
        
        # 移除结尾的分号
        raw_sql = raw_sql.rstrip(';')
        
        if not raw_sql:
            return
        
        # 规范化SQL
        normalized_sql = self.normalize_sql(raw_sql)
        checksum = self.generate_checksum(normalized_sql)
        
        # 存储指纹信息
        if checksum not in self.fingerprints:
            self.fingerprints[checksum] = {
                'checksum': checksum,
                'normalized_sql': normalized_sql,
                'raw_sql': raw_sql[:5000],  # 限制长度
                'username': username,
                'dbname': dbname,
                'first_seen': timestamp,
                'last_seen': timestamp,
                'reviewed_status': '待优化',
                'comments': None
            }
        else:
            # 更新最后见到时间
            if timestamp > self.fingerprints[checksum]['last_seen']:
                self.fingerprints[checksum]['last_seen'] = timestamp
            if timestamp < self.fingerprints[checksum]['first_seen']:
                self.fingerprints[checksum]['first_seen'] = timestamp
        
        # 存储详细信息
        self.details.append({
            'checksum': checksum,
            'timestamp': timestamp,
            'query_time': query_time,
            'lock_time': lock_time,
            'rows_sent': rows_sent,
            'rows_examined': rows_examined,
            'username': username,
            'dbname': dbname
        })
    
    def save_to_database(self):
        """保存解析结果到数据库"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            print(f"开始保存 {len(self.fingerprints)} 个指纹和 {len(self.details)} 条详细记录")
            
            # 保存指纹信息
            for fingerprint in self.fingerprints.values():
                cursor.execute("""
                    INSERT INTO slow_query_fingerprint 
                    (checksum, normalized_sql, raw_sql, username, dbname, 
                     first_seen, last_seen, reviewed_status, comments)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    last_seen = GREATEST(last_seen, VALUES(last_seen)),
                    first_seen = LEAST(first_seen, VALUES(first_seen))
                """, (
                    fingerprint['checksum'],
                    fingerprint['normalized_sql'],
                    fingerprint['raw_sql'],
                    fingerprint['username'],
                    fingerprint['dbname'],
                    fingerprint['first_seen'],
                    fingerprint['last_seen'],
                    fingerprint['reviewed_status'],
                    fingerprint['comments']
                ))
            
            # 保存详细信息
            for detail in self.details:
                cursor.execute("""
                    INSERT IGNORE INTO slow_query_detail 
                    (checksum, timestamp, query_time, lock_time, rows_sent, rows_examined, username, dbname)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    detail['checksum'],
                    detail['timestamp'],
                    detail['query_time'],
                    detail['lock_time'],
                    detail['rows_sent'],
                    detail['rows_examined'],
                    detail['username'],
                    detail['dbname']
                ))
            
            conn.commit()
            print("数据保存成功！")
            
        except Exception as e:
            conn.rollback()
            print(f"保存数据失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

def main():
    if len(sys.argv) != 2:
        print("使用方法: python parse_slow_log.py <慢日志文件路径>")
        print("示例: python parse_slow_log.py /path/to/slow.log")
        sys.exit(1)
    
    log_file = sys.argv[1]
    
    if not os.path.exists(log_file):
        print(f"文件不存在: {log_file}")
        sys.exit(1)
    
    print(f"开始解析慢日志文件: {log_file}")
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()
    except Exception as e:
        print(f"读取文件失败: {e}")
        sys.exit(1)
    
    parser = SlowLogParser()
    parser.parse_slow_log(log_content, days_back=7)
    
    print(f"解析完成，共找到 {len(parser.fingerprints)} 个不同的SQL指纹")
    print(f"总共 {len(parser.details)} 条执行记录")
    
    if len(parser.fingerprints) > 0:
        parser.save_to_database()
    else:
        print("没有找到符合条件的慢查询记录")

if __name__ == '__main__':
    main()
