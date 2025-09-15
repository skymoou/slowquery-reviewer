#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
系统状态诊断脚本
===============

检查整个系统的运行状态
"""

import requests
import json
import subprocess
import os

def check_backend():
    """检查后端状态"""
    print("🔧 检查后端服务...")
    try:
        response = requests.get('http://localhost:5172/api/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 后端服务正常 - {data.get('message', 'OK')}")
            return True
        else:
            print(f"❌ 后端服务异常 - 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 后端服务连接失败: {e}")
        return False

def check_frontend_dev():
    """检查前端开发服务器"""
    print("\n🌐 检查前端开发服务器...")
    try:
        response = requests.get('http://localhost:3000', timeout=5)
        if response.status_code == 200:
            print("✅ 前端开发服务器正常")
            return True
        else:
            print(f"❌ 前端开发服务器异常 - 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 前端开发服务器连接失败: {e}")
        return False

def check_frontend_built():
    """检查构建后的前端"""
    print("\n📦 检查构建后的前端...")
    try:
        response = requests.get('http://localhost:5172', timeout=5)
        if response.status_code == 200:
            content = response.text
            if 'html' in content.lower() and ('react' in content or 'vite' in content or 'script' in content):
                print("✅ 构建后的前端正常")
                return True
            else:
                print("⚠️  前端页面加载但可能不完整")
                return False
        else:
            print(f"❌ 构建后的前端异常 - 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 构建后的前端连接失败: {e}")
        return False

def test_login_api():
    """测试登录API"""
    print("\n🔐 测试登录API...")
    try:
        response = requests.post(
            'http://localhost:5172/api/login',
            json={'username': 'admin', 'password': 'Admin@123'},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 登录API正常")
                return True
            else:
                print(f"❌ 登录API失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 登录API异常 - 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 登录API连接失败: {e}")
        return False

def check_files():
    """检查关键文件"""
    print("\n📁 检查关键文件...")
    
    files_to_check = [
        'e:/yunkai/slowquery-reviewer/frontend/dist/index.html',
        'e:/yunkai/slowquery-reviewer/frontend/dist/assets',
        'e:/yunkai/slowquery-reviewer/backend/app.py',
        'e:/yunkai/slowquery-reviewer/backend/config.py'
    ]
    
    all_exist = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 不存在")
            all_exist = False
    
    return all_exist

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 慢查询系统状态诊断")
    print("=" * 60)
    
    # 检查各个组件
    backend_ok = check_backend()
    frontend_dev_ok = check_frontend_dev()
    frontend_built_ok = check_frontend_built()
    login_ok = test_login_api()
    files_ok = check_files()
    
    print("\n" + "=" * 60)
    print("📊 诊断结果总结")
    print("=" * 60)
    
    results = [
        ("后端服务", backend_ok),
        ("前端开发服务器", frontend_dev_ok),
        ("构建后前端", frontend_built_ok),
        ("登录API", login_ok),
        ("关键文件", files_ok)
    ]
    
    for name, status in results:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {name}")
    
    print("\n🎯 建议的访问方式:")
    if frontend_dev_ok:
        print("👉 开发环境: http://localhost:3000")
    if frontend_built_ok:
        print("👉 生产环境: http://localhost:5172")
    if not frontend_dev_ok and not frontend_built_ok:
        print("❌ 前端服务均不可用")
    
    print("\n📋 默认登录账户:")
    print("   admin / Admin@123")
    print("   dba / Dba@123")
    print("   dev / Dev@123")

if __name__ == '__main__':
    main()
