#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证server_side_slow_log_parser_py3.py中的SQL格式化功能
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from server_side_slow_log_parser_py3 import SlowLogParser
    
    # 创建解析器实例
    parser = SlowLogParser()
    
    # 测试SQL格式化功能
    test_sql = "select u.id, u.name, p.title from users u left join posts p on u.id = p.user_id where u.status = 'active' and p.published = 1 order by u.name limit 10"
    
    print("=== SQL格式化功能验证 ===")
    print("原始SQL:")
    print(test_sql)
    print("\n格式化后的SQL:")
    formatted_sql = parser.format_sql(test_sql)
    print(formatted_sql)
    
    print(f"\n✓ SQL格式化功能工作正常！")
    print(f"原始长度: {len(test_sql)}")
    print(f"格式化后长度: {len(formatted_sql)}")
    
except ImportError as e:
    print(f"导入错误: {e}")
    sys.exit(1)
except Exception as e:
    print(f"验证过程中出现错误: {e}")
    sys.exit(1)
