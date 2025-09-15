#!/bin/bash

# ============================================
# 慢查询分析系统 - 生产环境快速部署脚本
# ============================================
# 使用方法：sudo bash quick_deploy.sh
# 适用于：Ubuntu 20.04 LTS / CentOS 7+

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查root权限
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限，请使用 sudo 运行"
        exit 1
    fi
}

# 检测操作系统
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        OS_VERSION=$VERSION_ID
    else
        log_error "无法检测操作系统版本"
        exit 1
    fi
    
    log_info "检测到操作系统: $OS $OS_VERSION"
}

# 安装系统依赖
install_dependencies() {
    log_info "安装系统依赖包..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt update
        apt install -y python3 python3-venv python3-pip mysql-server nginx supervisor curl wget
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        yum update -y
        yum install -y python3 python3-pip mysql-server nginx supervisor curl wget
        yum groupinstall -y "Development Tools"
    else
        log_error "不支持的操作系统: $OS"
        exit 1
    fi
    
    log_success "系统依赖安装完成"
}

# 创建系统用户和目录
setup_user_and_dirs() {
    log_info "创建系统用户和目录..."
    
    # 创建用户
    if ! id "slowquery" &>/dev/null; then
        useradd -r -s /bin/false -m -d /opt/slowquery-reviewer slowquery
        log_success "用户 slowquery 创建成功"
    else
        log_info "用户 slowquery 已存在"
    fi
    
    # 创建目录
    mkdir -p /opt/slowquery-reviewer
    mkdir -p /var/log/slowquery
    mkdir -p /var/run/slowquery
    mkdir -p /opt/backups/slowquery
    
    # 设置权限
    chown -R slowquery:slowquery /opt/slowquery-reviewer
    chown -R slowquery:slowquery /var/log/slowquery
    chown -R slowquery:slowquery /var/run/slowquery
    
    log_success "目录创建完成"
}

# 配置数据库
setup_database() {
    log_info "配置MySQL数据库..."
    
    # 启动MySQL服务
    systemctl start mysql
    systemctl enable mysql
    
    # 读取数据库配置
    read -p "请输入MySQL root密码: " -s MYSQL_ROOT_PASS
    echo
    read -p "请输入slowquery数据库用户密码: " -s DB_PASSWORD
    echo
    
    # 创建数据库和用户
    mysql -u root -p"$MYSQL_ROOT_PASS" <<EOF
CREATE DATABASE IF NOT EXISTS slow_query_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'slowquery'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
CREATE USER IF NOT EXISTS 'slowquery'@'%' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON slow_query_analysis.* TO 'slowquery'@'localhost';
GRANT ALL PRIVILEGES ON slow_query_analysis.* TO 'slowquery'@'%';
FLUSH PRIVILEGES;
EOF
    
    log_success "数据库配置完成"
}

# 部署应用代码
deploy_application() {
    log_info "部署应用代码..."
    
    # 注意：这里需要手动上传代码到服务器
    if [[ ! -f "/opt/slowquery-reviewer/backend/app.py" ]]; then
        log_warning "请先将项目代码上传到 /opt/slowquery-reviewer/ 目录"
        log_warning "然后重新运行此脚本"
        exit 1
    fi
    
    # 设置权限
    chown -R slowquery:slowquery /opt/slowquery-reviewer
    
    # 创建虚拟环境
    cd /opt/slowquery-reviewer
    sudo -u slowquery python3 -m venv venv
    
    # 安装Python依赖
    sudo -u slowquery bash -c "source venv/bin/activate && pip install -r backend/requirements.txt"
    
    log_success "应用代码部署完成"
}

# 配置环境变量
setup_environment() {
    log_info "配置环境变量..."
    
    # 生成JWT密钥
    JWT_SECRET=$(openssl rand -hex 32)
    
    # 创建.env文件
    cat > /opt/slowquery-reviewer/backend/.env <<EOF
# 数据库配置
DB_HOST=localhost
DB_USER=slowquery
DB_PASSWORD=$DB_PASSWORD
DB_NAME=slow_query_analysis
DB_POOL_SIZE=15

# JWT配置
JWT_SECRET_KEY=$JWT_SECRET
JWT_ACCESS_TOKEN_EXPIRES=86400

# 应用配置
FLASK_ENV=production
FLASK_DEBUG=false
EOF
    
    # 设置权限
    chmod 600 /opt/slowquery-reviewer/backend/.env
    chown slowquery:slowquery /opt/slowquery-reviewer/backend/.env
    
    log_success "环境变量配置完成"
}

# 初始化数据库表
init_database_tables() {
    log_info "初始化数据库表..."
    
    cd /opt/slowquery-reviewer/backend
    
    # 初始化数据库
    sudo -u slowquery bash -c "source ../venv/bin/activate && python init_database.py"
    
    # 创建表结构
    sudo -u slowquery bash -c "source ../venv/bin/activate && python init_tables.py"
    
    # 创建管理员用户
    sudo -u slowquery bash -c "source ../venv/bin/activate && python init_admin.py"
    
    log_success "数据库表初始化完成"
    log_info "默认管理员账号: admin / admin (请登录后立即修改密码)"
}

# 配置Nginx
setup_nginx() {
    log_info "配置Nginx..."
    
    # 读取域名配置
    read -p "请输入域名或IP地址 (默认: localhost): " DOMAIN
    DOMAIN=${DOMAIN:-localhost}
    
    # 创建Nginx配置
    cat > /etc/nginx/sites-available/slowquery-reviewer <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    access_log /var/log/nginx/slowquery_access.log;
    error_log /var/log/nginx/slowquery_error.log;
    
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    client_max_body_size 100M;
    
    location / {
        root /opt/slowquery-reviewer/frontend/dist;
        try_files \$uri \$uri/ /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)\$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    location /api/ {
        proxy_pass http://127.0.0.1:5172;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:5172/api/status;
        access_log off;
    }
}
EOF
    
    # 启用配置
    ln -sf /etc/nginx/sites-available/slowquery-reviewer /etc/nginx/sites-enabled/
    
    # 删除默认配置
    rm -f /etc/nginx/sites-enabled/default
    
    # 测试配置
    nginx -t
    
    # 启动Nginx
    systemctl restart nginx
    systemctl enable nginx
    
    log_success "Nginx配置完成"
}

# 配置Supervisor
setup_supervisor() {
    log_info "配置Supervisor..."
    
    # 创建Supervisor配置
    cat > /etc/supervisor/conf.d/slowquery.conf <<EOF
[group:slowquery]
programs=slowquery-backend

[program:slowquery-backend]
command=/opt/slowquery-reviewer/venv/bin/gunicorn -c gunicorn.conf.py app:app
directory=/opt/slowquery-reviewer/backend
user=slowquery
group=slowquery
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/slowquery/backend.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
environment=PYTHONPATH="/opt/slowquery-reviewer/backend"
EOF
    
    # 启动Supervisor服务
    systemctl restart supervisor
    systemctl enable supervisor
    
    # 重新加载配置
    supervisorctl reread
    supervisorctl update
    
    # 启动应用
    supervisorctl start slowquery-backend
    
    log_success "Supervisor配置完成"
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    
    if command -v ufw &> /dev/null; then
        # Ubuntu UFW
        ufw allow ssh
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw --force enable
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS firewalld
        systemctl start firewalld
        systemctl enable firewalld
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --reload
    fi
    
    log_success "防火墙配置完成"
}

# 创建管理脚本
create_management_scripts() {
    log_info "创建管理脚本..."
    
    # 创建启动脚本
    cat > /opt/slowquery-reviewer/start.sh <<EOF
#!/bin/bash
supervisorctl start slowquery-backend
systemctl start nginx
echo "慢查询分析系统已启动"
EOF
    
    # 创建停止脚本
    cat > /opt/slowquery-reviewer/stop.sh <<EOF
#!/bin/bash
supervisorctl stop slowquery-backend
echo "慢查询分析系统已停止"
EOF
    
    # 创建重启脚本
    cat > /opt/slowquery-reviewer/restart.sh <<EOF
#!/bin/bash
supervisorctl restart slowquery-backend
systemctl reload nginx
echo "慢查询分析系统已重启"
EOF
    
    # 创建状态检查脚本
    cat > /opt/slowquery-reviewer/status.sh <<EOF
#!/bin/bash
echo "=== 服务状态 ==="
supervisorctl status slowquery-backend
systemctl status nginx --no-pager -l
echo
echo "=== 端口监听 ==="
netstat -tlnp | grep -E "(80|5172)"
echo
echo "=== 健康检查 ==="
curl -s http://localhost:5172/api/status || echo "API服务异常"
EOF
    
    # 设置执行权限
    chmod +x /opt/slowquery-reviewer/*.sh
    
    log_success "管理脚本创建完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署结果..."
    
    # 等待服务启动
    sleep 5
    
    # 检查服务状态
    if supervisorctl status slowquery-backend | grep -q RUNNING; then
        log_success "后端服务运行正常"
    else
        log_error "后端服务启动失败"
        return 1
    fi
    
    # 检查API可用性
    if curl -s http://localhost:5172/api/status > /dev/null; then
        log_success "API服务可访问"
    else
        log_error "API服务不可访问"
        return 1
    fi
    
    # 检查Nginx状态
    if systemctl is-active nginx >/dev/null; then
        log_success "Nginx服务运行正常"
    else
        log_error "Nginx服务异常"
        return 1
    fi
    
    log_success "部署验证完成！"
}

# 显示部署结果
show_deployment_result() {
    echo
    echo "============================================"
    echo -e "${GREEN}慢查询分析系统部署完成！${NC}"
    echo "============================================"
    echo
    echo "访问地址: http://$DOMAIN"
    echo "默认账号: admin"
    echo "默认密码: admin"
    echo
    echo "重要提醒:"
    echo "1. 请立即登录系统修改默认密码"
    echo "2. 建议配置SSL证书启用HTTPS"
    echo "3. 定期备份数据库数据"
    echo
    echo "管理命令:"
    echo "启动服务: /opt/slowquery-reviewer/start.sh"
    echo "停止服务: /opt/slowquery-reviewer/stop.sh"
    echo "重启服务: /opt/slowquery-reviewer/restart.sh"
    echo "查看状态: /opt/slowquery-reviewer/status.sh"
    echo
    echo "日志位置:"
    echo "应用日志: /var/log/slowquery/backend.log"
    echo "Nginx日志: /var/log/nginx/slowquery_*.log"
    echo
    echo "配置文件:"
    echo "环境变量: /opt/slowquery-reviewer/backend/.env"
    echo "Nginx配置: /etc/nginx/sites-available/slowquery-reviewer"
    echo "Supervisor配置: /etc/supervisor/conf.d/slowquery.conf"
    echo
    echo "============================================"
}

# 主函数
main() {
    echo
    echo "============================================"
    echo "慢查询分析系统 - 生产环境部署脚本"
    echo "============================================"
    echo
    
    check_root
    detect_os
    
    log_warning "部署前请确保:"
    log_warning "1. 已将项目代码上传到服务器"
    log_warning "2. 服务器可以访问互联网"
    log_warning "3. 已准备好MySQL root密码"
    echo
    
    read -p "确认开始部署? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 0
    fi
    
    install_dependencies
    setup_user_and_dirs
    setup_database
    deploy_application
    setup_environment
    init_database_tables
    setup_nginx
    setup_supervisor
    setup_firewall
    create_management_scripts
    
    if verify_deployment; then
        show_deployment_result
    else
        log_error "部署验证失败，请检查日志"
        exit 1
    fi
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 执行主函数
main "$@"
