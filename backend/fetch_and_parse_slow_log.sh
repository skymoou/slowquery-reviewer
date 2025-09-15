#!/bin/bash
# 从远程服务器获取慢日志并解析

SERVER_IP="10.41.0.91"
SERVER_USER="root"
SERVER_PASSWORD="Wp.com#2023"
SLOW_LOG_PATH="/data/mysql/log/slow.log"
LOCAL_LOG_FILE="./slow_log_$(date +%Y%m%d_%H%M%S).log"

echo "正在从服务器 $SERVER_IP 获取慢日志..."

# 使用sshpass和scp从远程服务器复制慢日志文件
# 注意：需要先安装sshpass
# Ubuntu/Debian: sudo apt-get install sshpass
# CentOS/RHEL: sudo yum install sshpass

if command -v sshpass >/dev/null 2>&1; then
    echo "使用sshpass获取慢日志文件..."
    sshpass -p "$SERVER_PASSWORD" scp -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP:$SLOW_LOG_PATH" "$LOCAL_LOG_FILE"
else
    echo "未找到sshpass命令，请手动复制慢日志文件或安装sshpass"
    echo "手动命令："
    echo "scp root@$SERVER_IP:$SLOW_LOG_PATH $LOCAL_LOG_FILE"
    exit 1
fi

if [ $? -eq 0 ]; then
    echo "慢日志文件已下载到: $LOCAL_LOG_FILE"
    echo "文件大小: $(ls -lh $LOCAL_LOG_FILE | awk '{print $5}')"
    
    echo "开始解析慢日志..."
    python parse_slow_log.py "$LOCAL_LOG_FILE"
    
    echo "清理临时文件..."
    rm "$LOCAL_LOG_FILE"
    echo "完成！"
else
    echo "下载慢日志文件失败"
    exit 1
fi
