#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JWT密钥生成工具
用于为服务器部署生成安全的JWT密钥
"""

import secrets
import string
import hashlib
import os
from datetime import datetime

def generate_secure_key(length=64):
    """生成安全的随机密钥"""
    # 使用安全的随机数生成器
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_hex_key(length=32):
    """生成十六进制密钥"""
    return secrets.token_hex(length)

def generate_urlsafe_key(length=32):
    """生成URL安全的Base64密钥"""
    return secrets.token_urlsafe(length)

def generate_hash_based_key(seed_text):
    """基于种子文本生成哈希密钥"""
    # 添加随机盐值
    salt = secrets.token_hex(16)
    combined = f"{seed_text}:{salt}:{datetime.now().isoformat()}"
    return hashlib.sha256(combined.encode()).hexdigest()

def main():
    print("JWT密钥生成工具")
    print("=" * 50)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 生成多种类型的密钥供选择
    print("🔐 推荐的JWT密钥（请选择其中一个）:")
    print()
    
    print("1. 高强度随机密钥 (推荐):")
    secure_key = generate_secure_key(64)
    print(f"   {secure_key}")
    print()
    
    print("2. 十六进制密钥:")
    hex_key = generate_hex_key(32)
    print(f"   {hex_key}")
    print()
    
    print("3. URL安全密钥:")
    urlsafe_key = generate_urlsafe_key(48)
    print(f"   {urlsafe_key}")
    print()
    
    print("4. 基于项目的唯一密钥:")
    project_key = generate_hash_based_key("slowquery-reviewer-production")
    print(f"   {project_key}")
    print()
    
    print("=" * 50)
    print("📋 部署配置说明")
    print("=" * 50)
    print()
    
    print("方法1: 环境变量设置 (推荐)")
    print("Rocky Linux生产服务器:")
    print(f'export JWT_SECRET_KEY="{secure_key}"')
    print()
    print("添加到 ~/.bashrc 以永久保存:")
    print(f'echo \'export JWT_SECRET_KEY="{secure_key}"\' >> ~/.bashrc')
    print()
    
    print("方法2: 修改config.py文件")
    print("将以下内容添加到config.py:")
    print(f"JWT_SECRET_KEY = '{secure_key}'")
    print()
    
    print("方法3: 创建.env文件")
    print("在backend目录创建.env文件，内容:")
    print(f"JWT_SECRET_KEY={secure_key}")
    print()
    
    print("⚠️  安全提醒:")
    print("- 密钥应该保密，不要提交到代码仓库")
    print("- 每个环境(开发/测试/生产)使用不同的密钥")
    print("- 定期更换生产环境密钥")
    print("- 将密钥添加到.gitignore文件中")

if __name__ == "__main__":
    main()
