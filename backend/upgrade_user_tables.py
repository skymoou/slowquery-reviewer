#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库表结构升级脚本
==================

此脚本用于升级用户表结构，添加缺失的字段以支持完整的用户管理功能。

升级内容：
1. 为users表添加is_active字段
2. 为users表添加email、full_name字段  
3. 为users表添加last_login字段
4. 更新表引擎和字符集

使用方法：
python upgrade_user_tables.py
"""

import sys
import os
import mysql.connector

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import DB_CONFIG
except ImportError:
    print("❌ 错误: 无法导入数据库配置，请确保 config.py 文件存在")
    sys.exit(1)

def check_column_exists(cursor, table_name, column_name):
    """检查列是否存在"""
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = '{table_name}' 
        AND COLUMN_NAME = '{column_name}'
    """)
    return cursor.fetchone()[0] > 0

def upgrade_users_table():
    """升级用户表结构"""
    print("🔧 开始升级用户表结构...")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 检查并添加is_active字段
        if not check_column_exists(cursor, 'users', 'is_active'):
            print("   📝 添加 is_active 字段...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN is_active BOOLEAN DEFAULT TRUE 
                AFTER role_id
            """)
        else:
            print("   ✅ is_active 字段已存在")
        
        # 检查并添加email字段
        if not check_column_exists(cursor, 'users', 'email'):
            print("   📝 添加 email 字段...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN email VARCHAR(100) 
                AFTER is_active
            """)
        else:
            print("   ✅ email 字段已存在")
            
        # 检查并添加full_name字段
        if not check_column_exists(cursor, 'users', 'full_name'):
            print("   📝 添加 full_name 字段...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN full_name VARCHAR(100) 
                AFTER email
            """)
        else:
            print("   ✅ full_name 字段已存在")
            
        # 检查并添加last_login字段
        if not check_column_exists(cursor, 'users', 'last_login'):
            print("   📝 添加 last_login 字段...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN last_login TIMESTAMP NULL 
                AFTER full_name
            """)
        else:
            print("   ✅ last_login 字段已存在")
            
        # 检查并添加updated_at字段
        if not check_column_exists(cursor, 'users', 'updated_at'):
            print("   📝 添加 updated_at 字段...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP 
                AFTER created_at
            """)
        else:
            print("   ✅ updated_at 字段已存在")
        
        # 更新现有用户的is_active状态
        cursor.execute("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")
        
        # 添加索引（如果不存在）
        try:
            cursor.execute("CREATE INDEX idx_username ON users(username)")
            print("   📝 添加 username 索引...")
        except mysql.connector.Error:
            print("   ✅ username 索引已存在")
            
        try:
            cursor.execute("CREATE INDEX idx_is_active ON users(is_active)")
            print("   📝 添加 is_active 索引...")
        except mysql.connector.Error:
            print("   ✅ is_active 索引已存在")
        
        conn.commit()
        print("✅ 用户表结构升级完成")
        
        # 显示升级后的表结构
        cursor.execute("DESCRIBE users")
        columns = cursor.fetchall()
        
        print("\n📋 升级后的用户表结构:")
        print("-" * 60)
        print(f"{'字段名':<15} {'类型':<20} {'可空':<5} {'默认值':<10}")
        print("-" * 60)
        for column in columns:
            field, type_info, null, key, default, extra = column
            null_str = "YES" if null == "YES" else "NO"
            default_str = str(default) if default is not None else "NULL"
            print(f"{field:<15} {type_info:<20} {null_str:<5} {default_str:<10}")
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ 升级失败: {e}")
        conn.rollback()
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def upgrade_other_tables():
    """升级其他表结构"""
    print("\n🔧 检查其他表结构...")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 更新表引擎和字符集
        tables_to_update = ['roles', 'permissions', 'role_permissions', 'users']
        
        for table in tables_to_update:
            print(f"   🔄 更新表 {table} 的引擎和字符集...")
            try:
                cursor.execute(f"""
                    ALTER TABLE {table} 
                    ENGINE=InnoDB 
                    DEFAULT CHARSET=utf8mb4 
                    COLLATE=utf8mb4_unicode_ci
                """)
            except mysql.connector.Error as e:
                if "doesn't exist" not in str(e):
                    print(f"   ⚠️  表 {table} 更新警告: {e}")
        
        conn.commit()
        print("✅ 表结构更新完成")
        
    except Exception as e:
        print(f"❌ 表结构更新失败: {e}")
        conn.rollback()
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 数据库表结构升级工具")
    print("=" * 60)
    
    try:
        # 测试数据库连接
        print("🔗 测试数据库连接...")
        conn = mysql.connector.connect(**DB_CONFIG)
        conn.close()
        print("✅ 数据库连接成功")
        
        # 升级用户表
        upgrade_users_table()
        
        # 升级其他表
        upgrade_other_tables()
        
        print("\n🎉 数据库升级完成！")
        print("\n现在可以使用完整功能的用户初始化脚本了。")
        
    except Exception as e:
        print(f"\n❌ 升级过程中发生错误: {e}")
        print("\n🔧 故障排除建议:")
        print("1. 检查数据库服务是否正常运行")
        print("2. 检查数据库连接配置")
        print("3. 检查数据库用户权限")
        sys.exit(1)

if __name__ == '__main__':
    main()
