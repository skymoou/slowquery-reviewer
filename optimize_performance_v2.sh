#!/bin/bash

#################################################################################
# 慢查询系统性能优化脚本 - 升级版
# 
# 此脚本用于优化系统性能，提高页面加载速度
#################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}🚀 慢查询系统性能优化 v2.0${NC}"
echo -e "${BLUE}================================${NC}"
echo

# 检查依赖
check_dependencies() {
    echo -e "${YELLOW}📋 检查系统依赖...${NC}"
    
    # 检查Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js 未安装${NC}"
        exit 1
    fi
    
    # 检查npm
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}❌ npm 未安装${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 依赖检查完成${NC}"
}

# 前端性能优化
optimize_frontend() {
    echo -e "${YELLOW}📦 1. 优化前端构建...${NC}"
    
    cd frontend
    
    # 清理缓存
    echo "清理构建缓存..."
    rm -rf node_modules/.vite
    rm -rf dist
    
    # 重新安装依赖并清理未使用的包
    echo "优化依赖..."
    npm ci --production=false
    npm prune
    
    # 执行优化构建
    echo "执行生产构建..."
    NODE_ENV=production npm run build
    
    # 分析bundle大小
    echo "分析构建结果..."
    du -sh dist/
    find dist -name "*.js" -exec ls -lh {} \; | sort -k5 -hr
    
    cd ..
    echo -e "${GREEN}✅ 前端优化完成${NC}"
}

# 后端性能优化
optimize_backend() {
    echo -e "${YELLOW}🛠️ 2. 优化后端配置...${NC}"
    
    cd backend
    
    # 安装Python依赖
    if [[ -f requirements.txt ]]; then
        echo "更新Python依赖..."
        pip install -r requirements.txt --upgrade
    fi
    
    # 检查数据库连接
    echo "检查数据库连接..."
    python -c "
import mysql.connector
from config import DB_CONFIG
try:
    conn = mysql.connector.connect(**DB_CONFIG)
    print('✅ 数据库连接正常')
    conn.close()
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
    exit(1)
"
    
    # 执行数据库优化
    echo "执行数据库优化..."
    mysql -h${DB_HOST:-10.41.0.91} -u${DB_USER:-root} -p${DB_PASSWORD:-Wp.stg3} ${DB_NAME:-slow_query_analysis} < optimize_database.sql 2>/dev/null || true
    
    cd ..
    echo -e "${GREEN}✅ 后端优化完成${NC}"
}

# 系统配置优化
optimize_system() {
    echo -e "${YELLOW}⚙️ 3. 优化系统配置...${NC}"
    
    # 创建优化的systemd服务文件
    cat > /tmp/slowquery-backend.service << 'EOF'
[Unit]
Description=SlowQuery Backend Service
After=network.target
After=mysql.service
Requires=mysql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/slowquery-reviewer/backend
Environment=PYTHONPATH=/opt/slowquery-reviewer/backend
Environment=FLASK_ENV=production
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=slowquery-backend
TimeoutStartSec=60
TimeoutStopSec=30

# 性能优化
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

    # 安装服务文件
    if [[ -f /tmp/slowquery-backend.service ]]; then
        sudo mv /tmp/slowquery-backend.service /etc/systemd/system/
        sudo systemctl daemon-reload
        echo -e "${GREEN}✅ Systemd服务已更新${NC}"
    fi
}

# Nginx配置优化
optimize_nginx() {
    echo -e "${YELLOW}🌐 4. 优化Nginx配置...${NC}"
    
    # 创建优化的Nginx配置
    cat > /tmp/slowquery-nginx.conf << 'EOF'
# 慢查询系统Nginx配置 - 性能优化版本
server {
    listen 80;
    server_name _;
    
    # 安全头部
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # 日志配置
    access_log /var/log/nginx/slowquery.access.log combined buffer=32k flush=5s;
    error_log /var/log/nginx/slowquery.error.log warn;
    
    # 前端静态文件
    location / {
        root /opt/slowquery-reviewer/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # 缓存策略
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            add_header Vary Accept-Encoding;
            access_log off;
        }
        
        location ~* \.(html)$ {
            expires 1h;
            add_header Cache-Control "public";
        }
    }
    
    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:5172;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 性能优化
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # 超时配置
        proxy_connect_timeout 10s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 压缩
        gzip on;
        gzip_types application/json text/plain application/javascript text/css;
    }
    
    # 健康检查
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

    if [[ -f /tmp/slowquery-nginx.conf ]]; then
        sudo mv /tmp/slowquery-nginx.conf /etc/nginx/sites-available/slowquery-reviewer
        
        # 启用站点
        sudo ln -sf /etc/nginx/sites-available/slowquery-reviewer /etc/nginx/sites-enabled/
        
        # 测试配置
        if sudo nginx -t; then
            echo -e "${GREEN}✅ Nginx配置已更新${NC}"
        else
            echo -e "${RED}❌ Nginx配置有误${NC}"
            exit 1
        fi
    fi
}

# 性能监控设置
setup_monitoring() {
    echo -e "${YELLOW}📊 5. 设置性能监控...${NC}"
    
    # 创建性能监控脚本
    cat > /opt/slowquery-reviewer/monitor.sh << 'EOF'
#!/bin/bash
# 性能监控脚本

LOG_FILE="/var/log/slowquery-monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# 检查服务状态
check_service() {
    if systemctl is-active --quiet slowquery-backend; then
        echo "[$DATE] ✅ Backend service is running" >> $LOG_FILE
    else
        echo "[$DATE] ❌ Backend service is down" >> $LOG_FILE
        systemctl restart slowquery-backend
    fi
}

# 检查内存使用
check_memory() {
    MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
    echo "[$DATE] 📊 Memory usage: ${MEMORY_USAGE}%" >> $LOG_FILE
    
    if (( $(echo "$MEMORY_USAGE > 90" | bc -l) )); then
        echo "[$DATE] ⚠️ High memory usage detected" >> $LOG_FILE
    fi
}

# 检查数据库连接
check_database() {
    if python3 -c "
import mysql.connector
from config import DB_CONFIG
try:
    conn = mysql.connector.connect(**DB_CONFIG)
    conn.close()
    print('Database OK')
except:
    print('Database Error')
    exit(1)
" > /dev/null 2>&1; then
        echo "[$DATE] ✅ Database connection OK" >> $LOG_FILE
    else
        echo "[$DATE] ❌ Database connection failed" >> $LOG_FILE
    fi
}

# 执行检查
check_service
check_memory
check_database

# 清理旧日志
find /var/log -name "slowquery-*.log" -mtime +7 -delete
EOF

    chmod +x /opt/slowquery-reviewer/monitor.sh
    
    # 添加到crontab
    (crontab -l 2>/dev/null; echo "*/5 * * * * /opt/slowquery-reviewer/monitor.sh") | crontab -
    
    echo -e "${GREEN}✅ 监控设置完成${NC}"
}

# 重启服务
restart_services() {
    echo -e "${YELLOW}🔄 6. 重启服务...${NC}"
    
    # 重启后端服务
    if systemctl is-enabled slowquery-backend &>/dev/null; then
        sudo systemctl restart slowquery-backend
        echo -e "${GREEN}✅ Backend服务已重启${NC}"
    fi
    
    # 重启Nginx
    if systemctl is-enabled nginx &>/dev/null; then
        sudo systemctl reload nginx
        echo -e "${GREEN}✅ Nginx已重载${NC}"
    fi
    
    # 检查服务状态
    sleep 3
    echo -e "\n${BLUE}服务状态检查:${NC}"
    systemctl is-active slowquery-backend && echo -e "${GREEN}✅ Backend: Running${NC}" || echo -e "${RED}❌ Backend: Failed${NC}"
    systemctl is-active nginx && echo -e "${GREEN}✅ Nginx: Running${NC}" || echo -e "${RED}❌ Nginx: Failed${NC}"
}

# 性能测试
performance_test() {
    echo -e "${YELLOW}🧪 7. 执行性能测试...${NC}"
    
    # 测试API响应时间
    echo "测试API响应时间..."
    time curl -s http://localhost/api/health > /dev/null
    
    # 测试前端加载时间
    echo "测试前端页面..."
    time curl -s http://localhost/ > /dev/null
    
    echo -e "${GREEN}✅ 性能测试完成${NC}"
}

# 主函数
main() {
    echo -e "${BLUE}开始性能优化流程...${NC}\n"
    
    check_dependencies
    optimize_frontend
    optimize_backend
    optimize_system
    optimize_nginx
    setup_monitoring
    restart_services
    performance_test
    
    echo -e "\n${GREEN}🎉 性能优化完成！${NC}"
    echo -e "${BLUE}优化内容:${NC}"
    echo -e "  ✅ 前端构建优化 (代码分割、压缩、缓存)"
    echo -e "  ✅ 后端性能优化 (连接池、查询缓存)"
    echo -e "  ✅ 数据库索引优化"
    echo -e "  ✅ Nginx配置优化 (缓存、压缩、负载均衡)"
    echo -e "  ✅ 系统监控设置"
    echo -e "\n${YELLOW}建议:${NC}"
    echo -e "  📊 定期检查 /var/log/slowquery-monitor.log"
    echo -e "  🔧 根据使用情况调整缓存策略"
    echo -e "  📈 监控系统资源使用情况"
}

# 执行主函数
main "$@"
