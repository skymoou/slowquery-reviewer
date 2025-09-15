#!/usr/bin/env python3
"""
手动获取远程慢日志的简化脚本
使用paramiko库通过SSH连接到远程服务器
"""

import paramiko
import os
from datetime import datetime

def download_slow_log():
    """下载远程慢日志文件"""
    server_ip = "10.41.0.91"
    username = "root"
    password = "Wp.com#2024"
    remote_path = "/data/mysql/log/slow.log"
    local_path = f"slow_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    try:
        print(f"正在连接到服务器 {server_ip}...")
        
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 连接到服务器
        ssh.connect(server_ip, username=username, password=password)
        
        # 创建SFTP客户端
        sftp = ssh.open_sftp()
        
        print(f"正在下载慢日志文件 {remote_path} 到 {local_path}...")
        sftp.get(remote_path, local_path)
        
        # 关闭连接
        sftp.close()
        ssh.close()
        
        print(f"下载完成！文件保存为: {local_path}")
        
        # 检查文件大小
        file_size = os.path.getsize(local_path)
        print(f"文件大小: {file_size / (1024*1024):.2f} MB")
        
        return local_path
        
    except Exception as e:
        print(f"下载失败: {str(e)}")
        return None

def main():
    """主函数"""
    print("开始下载远程慢日志文件...")
    
    # 检查是否安装了paramiko
    try:
        import paramiko
    except ImportError:
        print("请先安装paramiko库:")
        print("pip install paramiko")
        return
    
    # 下载慢日志文件
    log_file = download_slow_log()
    
    if log_file and os.path.exists(log_file):
        print("\n开始解析慢日志...")
        
        # 调用解析脚本
        os.system(f"python parse_slow_log.py {log_file}")
        
        # 询问是否删除临时文件
        response = input(f"\n是否删除临时文件 {log_file}? (y/N): ")
        if response.lower() == 'y':
            os.remove(log_file)
            print("临时文件已删除")
        else:
            print(f"临时文件保留: {log_file}")
    else:
        print("下载失败，请检查网络连接和服务器信息")

if __name__ == '__main__':
    main()
