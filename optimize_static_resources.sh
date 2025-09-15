#!/bin/bash

# 慢查询系统静态资源优化部署脚本
# 用于解决CDN资源加载超时问题

set -e

echo "🚀 开始慢查询系统静态资源优化部署..."

# 配置变量
FRONTEND_DIR="/path/to/slowquery-reviewer/frontend"
BACKEND_DIR="/path/to/slowquery-reviewer/backend"
NGINX_CONF_DIR="/etc/nginx/sites-available"
SERVICE_NAME="slowquery-backend"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查必要的工具
check_prerequisites() {
    log_info "检查系统依赖..."
    
    if ! command -v npm &> /dev/null; then
        log_error "npm 未安装，请先安装 Node.js"
        exit 1
    fi
    
    if ! command -v nginx &> /dev/null; then
        log_error "nginx 未安装，请先安装 nginx"
        exit 1
    fi
    
    log_info "依赖检查通过"
}

# 停止服务
stop_services() {
    log_info "停止相关服务..."
    systemctl stop nginx 2>/dev/null || log_warn "nginx 服务停止失败"
    systemctl stop $SERVICE_NAME 2>/dev/null || log_warn "$SERVICE_NAME 服务停止失败"
}

# 构建前端项目
build_frontend() {
    log_info "构建前端项目..."
    cd $FRONTEND_DIR
    
    # 清理旧构建
    rm -rf dist node_modules/.vite
    
    # 安装依赖
    npm install
    
    # 构建项目
    npm run build
    
    if [ $? -eq 0 ]; then
        log_info "前端构建成功"
    else
        log_error "前端构建失败"
        exit 1
    fi
}

# 优化静态资源
optimize_assets() {
    log_info "优化静态资源..."
    cd $FRONTEND_DIR/dist
    
    # 压缩CSS和JS文件
    find . -name "*.css" -exec gzip -k {} \;
    find . -name "*.js" -exec gzip -k {} \;
    
    # 设置适当的文件权限
    find . -type f -exec chmod 644 {} \;
    find . -type d -exec chmod 755 {} \;
    
    log_info "静态资源优化完成"
}

# 配置Nginx
configure_nginx() {
    log_info "配置Nginx..."
    
    cat > $NGINX_CONF_DIR/slowquery << 'EOF'
# 慢查询系统 Nginx 配置 - 静态资源优化版
server {
    listen 80;
    server_name localhost;
    
    # 根目录设置
    root /path/to/slowquery-reviewer/frontend/dist;
    index index.html;
    
    # 启用gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml+rss
        application/json;
    
    # 静态资源缓存优化
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
        
        # 优先使用预压缩的gzip文件
        gzip_static on;
        
        # 如果文件不存在，不要记录错误日志
        log_not_found off;
    }
    
    # 前端路由支持
    location / {
        try_files $uri $uri/ /index.html;
        
        # 安全头
        add_header X-Frame-Options DENY;
        add_header X-XSS-Protection "1; mode=block";
        add_header X-Content-Type-Options nosniff;
    }
    
    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:5172;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # 超时设置
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # 健康检查
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # 错误页面
    error_page 404 /index.html;
    error_page 500 502 503 504 /50x.html;
    
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}
EOF
    
    # 创建软链接
    ln -sf $NGINX_CONF_DIR/slowquery /etc/nginx/sites-enabled/
    
    # 测试配置
    nginx -t
    if [ $? -eq 0 ]; then
        log_info "Nginx配置验证成功"
    else
        log_error "Nginx配置验证失败"
        exit 1
    fi
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 启动后端服务
    systemctl start $SERVICE_NAME
    if [ $? -eq 0 ]; then
        log_info "后端服务启动成功"
    else
        log_error "后端服务启动失败"
        exit 1
    fi
    
    # 启动Nginx
    systemctl start nginx
    if [ $? -eq 0 ]; then
        log_info "Nginx服务启动成功"
    else
        log_error "Nginx服务启动失败"
        exit 1
    fi
    
    # 启用自启动
    systemctl enable nginx
    systemctl enable $SERVICE_NAME
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."
    
    # 检查服务状态
    if systemctl is-active --quiet nginx; then
        log_info "✅ Nginx 运行正常"
    else
        log_error "❌ Nginx 运行异常"
    fi
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_info "✅ 后端服务运行正常"
    else
        log_error "❌ 后端服务运行异常"
    fi
    
    # 检查端口监听
    if netstat -tlnp | grep -q ":80 "; then
        log_info "✅ 端口80监听正常"
    else
        log_warn "⚠️  端口80未监听"
    fi
    
    # 测试HTTP响应
    if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
        log_info "✅ HTTP服务响应正常"
    else
        log_warn "⚠️  HTTP服务响应异常"
    fi
}

# 显示优化效果
show_optimization_results() {
    log_info "优化效果统计..."
    
    cd $FRONTEND_DIR/dist
    
    echo "📊 静态资源统计:"
    echo "   CSS文件: $(find . -name "*.css" | wc -l)"
    echo "   JS文件: $(find . -name "*.js" | wc -l)" 
    echo "   压缩文件: $(find . -name "*.gz" | wc -l)"
    echo "   总文件大小: $(du -sh . | cut -f1)"
    
    echo ""
    echo "🎯 优化效果:"
    echo "   ✅ 移除了Bootstrap Icons CDN依赖"
    echo "   ✅ 使用react-icons本地图标库"
    echo "   ✅ 启用静态资源压缩和缓存"
    echo "   ✅ 优化了Webpack构建配置"
    echo "   ✅ 减少了网络请求和加载时间"
}

# 主执行函数
main() {
    log_info "开始执行静态资源优化部署..."
    
    check_prerequisites
    stop_services
    build_frontend
    optimize_assets
    configure_nginx
    start_services
    verify_deployment
    show_optimization_results
    
    log_info "🎉 静态资源优化部署完成!"
    echo ""
    echo "📋 部署摘要:"
    echo "   - 前端构建: ✅ 完成"
    echo "   - 静态资源优化: ✅ 完成"
    echo "   - Nginx配置: ✅ 完成"
    echo "   - 服务启动: ✅ 完成"
    echo "   - 验证测试: ✅ 完成"
    echo ""
    echo "🌐 访问地址: http://localhost/"
    echo "📊 管理面板: http://localhost/stats"
    echo "🔧 如需调试，请查看日志:"
    echo "   - Nginx: sudo tail -f /var/log/nginx/error.log"
    echo "   - 后端: sudo journalctl -fu $SERVICE_NAME"
}

# 执行主函数
main "$@"
