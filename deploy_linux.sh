#!/bin/bash

# 快速部署脚本 - Linux服务器增量更新
# 用途：将GitHub上的最新代码部署到生产服务器

set -e  # 遇到错误立即退出

# 配置参数
PROJECT_PATH="/opt/slowquery-reviewer"  # 项目部署路径，请根据实际情况修改
SERVICE_NAME="slowquery-reviewer"       # Supervisor服务名称
NGINX_SITE="slowquery-reviewer"         # Nginx站点名称
BACKUP_PATH="/opt/backup/slowquery"     # 备份路径

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 检查是否为root用户或有sudo权限
check_privileges() {
    if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
        log_error "此脚本需要root权限或sudo权限"
        exit 1
    fi
}

# 检查项目是否存在
check_project_exists() {
    if [ ! -d "$PROJECT_PATH" ]; then
        log_error "项目目录不存在: $PROJECT_PATH"
        log_info "请先执行初始部署或检查路径配置"
        exit 1
    fi
}

# 创建备份
create_backup() {
    log_info "创建备份..."
    
    # 创建备份目录
    sudo mkdir -p "$BACKUP_PATH"
    
    # 备份关键文件
    BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
    sudo cp -r "$PROJECT_PATH/backend/routes" "$BACKUP_PATH/routes_$BACKUP_DATE" 2>/dev/null || true
    sudo cp "$PROJECT_PATH/backend/config.py" "$BACKUP_PATH/config_$BACKUP_DATE.py" 2>/dev/null || true
    
    log_success "备份完成: $BACKUP_PATH"
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    # 停止后端服务
    if sudo supervisorctl status $SERVICE_NAME >/dev/null 2>&1; then
        sudo supervisorctl stop $SERVICE_NAME
        log_success "后端服务已停止"
    else
        log_warning "后端服务不存在或已停止"
    fi
}

# 更新代码
update_code() {
    log_info "更新代码..."
    
    cd "$PROJECT_PATH"
    
    # 获取当前提交ID
    OLD_COMMIT=$(git rev-parse HEAD)
    
    # 拉取最新代码
    sudo -u www-data git pull origin main
    
    # 获取新的提交ID
    NEW_COMMIT=$(git rev-parse HEAD)
    
    if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
        log_info "代码已是最新版本"
        return 0
    else
        log_success "代码更新完成"
        log_info "从 ${OLD_COMMIT:0:7} 更新到 ${NEW_COMMIT:0:7}"
        
        # 显示变更文件
        git diff --name-only $OLD_COMMIT $NEW_COMMIT | while read file; do
            log_info "变更文件: $file"
        done
        
        return 1  # 表示有更新
    fi
}

# 更新后端依赖
update_backend() {
    log_info "检查后端依赖..."
    
    cd "$PROJECT_PATH/backend"
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 更新依赖
    pip install -r requirements.txt --quiet
    
    log_success "后端依赖检查完成"
}

# 构建前端
build_frontend() {
    log_info "检查前端构建..."
    
    cd "$PROJECT_PATH/frontend"
    
    # 检查是否有前端变更
    if git diff --name-only HEAD~1 HEAD | grep -q "frontend/" 2>/dev/null; then
        log_info "发现前端变更，重新构建..."
        npm install --silent
        npm run build --silent
        log_success "前端构建完成"
    else
        log_info "前端无变更，跳过构建"
    fi
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 启动后端服务
    sudo supervisorctl start $SERVICE_NAME
    
    # 等待服务启动
    sleep 3
    
    # 检查服务状态
    if sudo supervisorctl status $SERVICE_NAME | grep -q "RUNNING"; then
        log_success "后端服务启动成功"
    else
        log_error "后端服务启动失败"
        sudo supervisorctl tail $SERVICE_NAME
        exit 1
    fi
    
    # 重新加载Nginx
    sudo systemctl reload nginx
    log_success "Nginx配置已重新加载"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查后端API
    if curl -f http://localhost:5172/api/health >/dev/null 2>&1; then
        log_success "后端API健康检查通过"
    else
        log_warning "后端API健康检查失败，但服务可能正在启动"
    fi
    
    # 检查前端页面
    if curl -f http://localhost/ >/dev/null 2>&1; then
        log_success "前端页面访问正常"
    else
        log_warning "前端页面访问失败"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_success "🎉 部署完成!"
    echo
    echo "📊 服务信息："
    echo "   后端服务: $(sudo supervisorctl status $SERVICE_NAME | awk '{print $2}')"
    echo "   当前版本: $(cd $PROJECT_PATH && git log -1 --format='%h - %s')"
    echo
    echo "🔗 访问地址："
    echo "   前端页面: http://your-server-ip/"
    echo "   API接口: http://your-server-ip/api/"
    echo
    echo "📝 查看日志："
    echo "   应用日志: sudo tail -f /var/log/slowquery-reviewer.log"
    echo "   服务状态: sudo supervisorctl status $SERVICE_NAME"
}

# 主执行流程
main() {
    echo "🚀 开始Linux服务器增量部署..."
    echo
    
    check_privileges
    check_project_exists
    create_backup
    stop_services
    
    # 更新代码，如果有变更则继续后续步骤
    if update_code; then
        log_info "没有代码更新，仅重启服务"
    else
        log_info "有代码更新，执行完整部署流程"
        update_backend
        build_frontend
    fi
    
    start_services
    health_check
    show_deployment_info
}

# 捕获错误并回滚
trap 'log_error "部署失败，正在回滚..."; sudo supervisorctl start $SERVICE_NAME 2>/dev/null || true' ERR

# 执行主流程
main "$@"
