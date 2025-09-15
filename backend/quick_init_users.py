#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速用户初始化脚本
================

此脚本用于快速创建系统默认用户，适用于生产环境部署。

默认账户：
- admin / Admin@123  (管理员)
- dba / Dba@123      (数据库管理员)  
- dev / Dev@123      (开发者)

使用方法：
python quick_init_users.py
"""

import sys
import os
import mysql.connector
import bcrypt

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import DB_CONFIG
except ImportError:
    print("错误: 无法导入数据库配置，请确保 config.py 文件存在")
    sys.exit(1)

def quick_init():
    """快速初始化用户"""
    print("🚀 快速初始化用户账户...")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 检查并创建角色
        roles = [
            ('dev', '开发人员'),
            ('dba', '数据库管理员'), 
            ('admin', '系统管理员')
        ]
        
        print("创建角色...")
        for role_name, description in roles:
            cursor.execute("""
                INSERT IGNORE INTO roles (name, description) 
                VALUES (%s, %s)
            """, (role_name, description))
        
        # 获取角色ID
        cursor.execute("SELECT id, name FROM roles")
        role_ids = {row[1]: row[0] for row in cursor.fetchall()}
        
        # 创建用户
        users = [
            ('admin', 'Admin@123', 'admin'),
            ('dba', 'Dba@123', 'dba'),
            ('dev', 'Dev@123', 'dev')
        ]
        
        print("创建用户...")
        for username, password, role in users:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # 删除已存在的用户
            cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            
            # 创建新用户（不包含is_active字段，因为表中没有此字段）
            cursor.execute("""
                INSERT INTO users (username, password_hash, role_id)
                VALUES (%s, %s, %s)
            """, (username, password_hash, role_ids[role]))
            
            print(f"✅ 用户 {username} 创建成功")
        
        conn.commit()
        
        print("\n🎉 用户初始化完成！")
        print("\n默认登录账户:")
        print("管理员: admin / Admin@123")
        print("DBA:   dba / Dba@123") 
        print("开发者: dev / Dev@123")
        print("\n⚠️ 请在首次登录后立即修改密码！")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    quick_init()
