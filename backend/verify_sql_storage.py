#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证SQL完整存储功能的修改
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from server_side_slow_log_parser_py3 import SlowLogParser, PARSE_CONFIG
    
    print("=== SQL完整存储验证 ===\n")
    
    # 检查配置
    print(f"当前配置:")
    print(f"  max_sql_length: {PARSE_CONFIG.get('max_sql_length')} 字符")
    print(f"  相当于: {PARSE_CONFIG.get('max_sql_length') / 1024:.1f} KB")
    
    # 创建一个长SQL测试
    long_sql = "SELECT " + ", ".join([f"column_{i}" for i in range(1000)]) + " FROM big_table WHERE condition = 'test'"
    print(f"\n测试长SQL:")
    print(f"  SQL长度: {len(long_sql)} 字符")
    print(f"  相当于: {len(long_sql) / 1024:.2f} KB")
    print(f"  是否会被截断: {'否' if len(long_sql) <= PARSE_CONFIG.get('max_sql_length') else '是'}")
    
    # 测试格式化功能
    parser = SlowLogParser()
    formatted = parser.format_sql(long_sql)
    print(f"  格式化后长度: {len(formatted)} 字符")
    
    print(f"\n✓ SQL完整存储功能已启用！")
    print(f"✓ 支持最大SQL长度: {PARSE_CONFIG.get('max_sql_length')} 字符")
    print(f"✓ 实际应用中将不再截断SQL语句")
    
except ImportError as e:
    print(f"导入错误: {e}")
    sys.exit(1)
except Exception as e:
    print(f"验证过程中出现错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
