#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
清理旧用户脚本
============

删除旧的测试用户，只保留标准的用户账户。
"""

import sys
import os
import mysql.connector

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import DB_CONFIG
except ImportError:
    print("❌ 错误: 无法导入数据库配置")
    sys.exit(1)

def clean_old_users():
    """清理旧用户"""
    print("🧹 清理旧用户账户...")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 删除旧的测试用户
        old_users = ['dev_user', 'dba_user', 'test_user', 'user1', 'user2']
        
        for username in old_users:
            cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            if cursor.rowcount > 0:
                print(f"   ✅ 删除用户: {username}")
        
        conn.commit()
        
        # 显示剩余用户
        cursor.execute("""
            SELECT u.username, r.name as role_name, u.created_at 
            FROM users u 
            LEFT JOIN roles r ON u.role_id = r.id 
            ORDER BY u.username
        """)
        users = cursor.fetchall()
        
        print("\n📋 当前用户列表:")
        print("-" * 50)
        print(f"{'用户名':<10} {'角色':<10} {'创建时间':<20}")
        print("-" * 50)
        for username, role, created_at in users:
            print(f"{username:<10} {role:<10} {created_at}")
        print("-" * 50)
        
        print(f"\n✅ 清理完成！当前共有 {len(users)} 个用户")
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        conn.rollback()
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    clean_old_users()
