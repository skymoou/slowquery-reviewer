#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库字段升级脚本
将SQL相关字段从TEXT升级为LONGTEXT以支持更大的SQL语句
"""

import pymysql
import sys
import os

# 尝试导入配置文件
try:
    from server_config import DB_CONFIG
except ImportError:
    # 如果没有配置文件，使用默认配置
    print("警告: 未找到server_config.py，请确认数据库配置")
    sys.exit(1)

def upgrade_sql_columns():
    """升级SQL字段为LONGTEXT类型"""
    print("=" * 60)
    print("SQL字段升级工具")
    print("将TEXT字段升级为LONGTEXT以支持更大的SQL语句")
    print("=" * 60)
    
    print(f"数据库配置:")
    print(f"  主机: {DB_CONFIG['host']}")
    print(f"  用户: {DB_CONFIG['user']}")
    print(f"  数据库: {DB_CONFIG['database']}")
    
    # 确认是否继续
    response = input("\n确认要执行数据库升级吗? (y/N): ")
    if not response.lower() in ['y', 'yes']:
        print("升级已取消")
        return
    
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("\n开始升级数据库字段...")
        
        # 检查当前字段类型
        print("\n1. 检查当前字段类型...")
        
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME IN ('slow_query_fingerprint', 'slow_query_detail')
            AND COLUMN_NAME LIKE '%sql%'
            ORDER BY TABLE_NAME, COLUMN_NAME
        """, (DB_CONFIG['database'],))
        
        current_columns = cursor.fetchall()
        print("当前SQL字段类型:")
        for col in current_columns:
            print(f"  {col[0]}: {col[1]} ({col[2]} 字符)")
        
        # 升级字段
        upgrade_sqls = [
            "ALTER TABLE slow_query_fingerprint MODIFY COLUMN raw_sql LONGTEXT",
            "ALTER TABLE slow_query_fingerprint MODIFY COLUMN normalized_sql LONGTEXT NOT NULL",
            "ALTER TABLE slow_query_detail MODIFY COLUMN sql_text LONGTEXT NOT NULL"
        ]
        
        print("\n2. 执行字段升级...")
        for i, sql in enumerate(upgrade_sqls, 1):
            print(f"  执行升级 {i}/{len(upgrade_sqls)}: {sql}")
            cursor.execute(sql)
            print(f"  ✓ 升级 {i} 完成")
        
        # 提交更改
        conn.commit()
        print("\n3. 升级成功提交到数据库")
        
        # 验证升级结果
        print("\n4. 验证升级结果...")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME IN ('slow_query_fingerprint', 'slow_query_detail')
            AND COLUMN_NAME LIKE '%sql%'
            ORDER BY TABLE_NAME, COLUMN_NAME
        """, (DB_CONFIG['database'],))
        
        upgraded_columns = cursor.fetchall()
        print("升级后的SQL字段类型:")
        for col in upgraded_columns:
            max_length = "无限制" if col[2] is None else f"{col[2]} 字符"
            print(f"  {col[0]}: {col[1]} ({max_length})")
        
        print("\n" + "=" * 60)
        print("升级完成！现在可以存储任意长度的SQL语句了。")
        print("LONGTEXT类型支持最大4GB的文本内容。")
        print("=" * 60)
        
    except Exception as e:
        conn.rollback()
        print(f"\n升级失败: {e}")
        print("数据库已回滚到升级前状态")
        
        # 显示详细错误信息
        import traceback
        print("\n详细错误信息:")
        traceback.print_exc()
        
        sys.exit(1)
        
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    upgrade_sql_columns()
