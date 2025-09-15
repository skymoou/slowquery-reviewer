#!/bin/bash

# ============================================
# 慢查询分析系统 - Gunicorn + Supervisor 启动脚本
# ============================================

set -e  # 遇到错误立即退出

# 颜色定义
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

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 配置文件路径
GUNICORN_CONFIG="$PROJECT_ROOT/backend/gunicorn.conf.py"
SUPERVISOR_CONFIG="/etc/supervisor/conf.d/slowquery.conf"
VENV_PATH="$PROJECT_ROOT/backend/venv"

# 显示使用说明
show_usage() {
    echo "慢查询分析系统 - Gunicorn + Supervisor 管理脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start         启动所有服务"
    echo "  stop          停止所有服务"
    echo "  restart       重启所有服务"
    echo "  status        查看服务状态"
    echo "  logs          查看服务日志"
    echo "  health        健康检查"
    echo "  install       安装和配置服务"
    echo "  update        更新代码并重启服务"
    echo ""
    echo "示例:"
    echo "  $0 start      # 启动服务"
    echo "  $0 status     # 查看状态"
    echo "  $0 logs       # 查看日志"
    echo ""
}

# 检查supervisor是否运行
check_supervisor() {
    if ! systemctl is-active --quiet supervisord 2>/dev/null && ! systemctl is-active --quiet supervisor 2>/dev/null; then
        log_error "Supervisor服务未运行，请先启动Supervisor"
        echo "启动命令: sudo systemctl start supervisord"
        exit 1
    fi
}

# 检查配置文件
check_configs() {
    if [[ ! -f "$GUNICORN_CONFIG" ]]; then
        log_error "Gunicorn配置文件不存在: $GUNICORN_CONFIG"
        exit 1
    fi
    
    if [[ ! -f "$SUPERVISOR_CONFIG" ]]; then
        log_error "Supervisor配置文件不存在: $SUPERVISOR_CONFIG"
        echo "请运行: $0 install 来安装配置"
        exit 1
    fi
}

# 检查虚拟环境
check_venv() {
    if [[ ! -d "$VENV_PATH" ]]; then
        log_error "Python虚拟环境不存在: $VENV_PATH"
        echo "请先创建虚拟环境: python3 -m venv $VENV_PATH"
        exit 1
    fi
    
    if [[ ! -f "$VENV_PATH/bin/gunicorn" ]]; then
        log_error "Gunicorn未安装在虚拟环境中"
        echo "请运行: $VENV_PATH/bin/pip install gunicorn"
        exit 1
    fi
}

# 启动服务
start_services() {
    log_info "启动慢查询分析系统服务..."
    
    check_supervisor
    check_configs
    check_venv
    
    # 重载配置
    log_info "重载Supervisor配置..."
    sudo supervisorctl reread
    sudo supervisorctl update
    
    # 启动服务
    log_info "启动后端服务 (Gunicorn)..."
    sudo supervisorctl start slowquery-backend
    
    log_info "启动前端服务 (Vite Preview)..."
    sudo supervisorctl start slowquery-frontend
    
    # 等待服务启动
    sleep 3
    
    # 检查状态
    check_service_status
    
    log_success "所有服务启动完成！"
    echo ""
    echo "访问地址:"
    echo "  前端界面: http://localhost:4173"
    echo "  后端API:  http://localhost:5172"
    echo "  健康检查: http://localhost:5172/api/health"
}

# 停止服务
stop_services() {
    log_info "停止慢查询分析系统服务..."
    
    check_supervisor
    
    sudo supervisorctl stop slowquery:*
    
    log_success "所有服务已停止"
}

# 重启服务
restart_services() {
    log_info "重启慢查询分析系统服务..."
    
    stop_services
    sleep 2
    start_services
}

# 查看服务状态
show_status() {
    log_info "慢查询分析系统服务状态:"
    echo ""
    
    check_supervisor
    
    # 显示Supervisor状态
    echo "=== Supervisor进程状态 ==="
    sudo supervisorctl status slowquery:*
    echo ""
    
    # 显示端口监听状态
    echo "=== 端口监听状态 ==="
    if command -v ss &> /dev/null; then
        ss -tlnp | grep -E "(5172|4173)" || echo "未发现监听端口"
    else
        netstat -tlnp | grep -E "(5172|4173)" || echo "未发现监听端口"
    fi
    echo ""
    
    # 显示进程信息
    echo "=== 进程信息 ==="
    ps aux | grep -E "(gunicorn|npm.*preview)" | grep -v grep || echo "未发现相关进程"
}

# 查看日志
show_logs() {
    echo "慢查询分析系统服务日志:"
    echo ""
    echo "选择要查看的日志:"
    echo "1) 后端服务日志"
    echo "2) 前端服务日志"
    echo "3) 后端错误日志"
    echo "4) 前端错误日志"
    echo "5) Gunicorn访问日志"
    echo "6) Gunicorn错误日志"
    echo "7) 实时监控所有日志"
    echo ""
    read -p "请输入选择 (1-7): " choice
    
    case $choice in
        1)
            log_info "显示后端服务日志..."
            sudo supervisorctl tail -f slowquery-backend
            ;;
        2)
            log_info "显示前端服务日志..."
            sudo supervisorctl tail -f slowquery-frontend
            ;;
        3)
            log_info "显示后端错误日志..."
            sudo tail -f /var/log/supervisor/slowquery-backend-error.log
            ;;
        4)
            log_info "显示前端错误日志..."
            sudo tail -f /var/log/supervisor/slowquery-frontend-error.log
            ;;
        5)
            log_info "显示Gunicorn访问日志..."
            sudo tail -f /var/log/gunicorn-access.log
            ;;
        6)
            log_info "显示Gunicorn错误日志..."
            sudo tail -f /var/log/gunicorn-error.log
            ;;
        7)
            log_info "实时监控所有日志..."
            sudo tail -f /var/log/supervisor/slowquery-*.log /var/log/gunicorn-*.log
            ;;
        *)
            log_error "无效选择"
            ;;
    esac
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    echo ""
    
    # 检查Supervisor状态
    echo "=== 1. Supervisor服务状态 ==="
    if systemctl is-active --quiet supervisord 2>/dev/null || systemctl is-active --quiet supervisor 2>/dev/null; then
        log_success "Supervisor服务正常运行"
    else
        log_error "Supervisor服务未运行"
        return 1
    fi
    echo ""
    
    # 检查应用进程状态
    echo "=== 2. 应用进程状态 ==="
    backend_status=$(sudo supervisorctl status slowquery-backend 2>/dev/null | awk '{print $2}')
    frontend_status=$(sudo supervisorctl status slowquery-frontend 2>/dev/null | awk '{print $2}')
    
    if [[ "$backend_status" == "RUNNING" ]]; then
        log_success "后端服务正常运行"
    else
        log_error "后端服务状态异常: $backend_status"
    fi
    
    if [[ "$frontend_status" == "RUNNING" ]]; then
        log_success "前端服务正常运行"
    else
        log_error "前端服务状态异常: $frontend_status"
    fi
    echo ""
    
    # 检查端口监听
    echo "=== 3. 端口监听检查 ==="
    if ss -tln | grep -q ":5172"; then
        log_success "后端端口 5172 正常监听"
    else
        log_error "后端端口 5172 未监听"
    fi
    
    if ss -tln | grep -q ":4173"; then
        log_success "前端端口 4173 正常监听"
    else
        log_error "前端端口 4173 未监听"
    fi
    echo ""
    
    # 检查API响应
    echo "=== 4. API响应检查 ==="
    if curl -s -f http://localhost:5172/api/health >/dev/null 2>&1; then
        log_success "后端API响应正常"
        echo "API响应: $(curl -s http://localhost:5172/api/health)"
    else
        log_error "后端API无响应"
    fi
    echo ""
    
    # 检查前端页面
    echo "=== 5. 前端页面检查 ==="
    if curl -s -f http://localhost:4173/ >/dev/null 2>&1; then
        log_success "前端页面响应正常"
    else
        log_error "前端页面无响应"
    fi
    echo ""
    
    log_info "健康检查完成"
}

# 检查服务状态
check_service_status() {
    backend_status=$(sudo supervisorctl status slowquery-backend 2>/dev/null | awk '{print $2}')
    frontend_status=$(sudo supervisorctl status slowquery-frontend 2>/dev/null | awk '{print $2}')
    
    if [[ "$backend_status" == "RUNNING" ]]; then
        log_success "后端服务运行正常"
    else
        log_error "后端服务状态异常: $backend_status"
    fi
    
    if [[ "$frontend_status" == "RUNNING" ]]; then
        log_success "前端服务运行正常"
    else
        log_error "前端服务状态异常: $frontend_status"
    fi
}

# 安装和配置服务
install_services() {
    log_info "安装和配置慢查询分析系统服务..."
    
    # 运行自动化安装脚本
    if [[ -f "$PROJECT_ROOT/deployment/scripts/setup_supervisor.sh" ]]; then
        bash "$PROJECT_ROOT/deployment/scripts/setup_supervisor.sh"
    else
        log_error "自动化安装脚本不存在"
        exit 1
    fi
}

# 更新代码并重启
update_services() {
    log_info "更新代码并重启服务..."
    
    # 停止服务
    stop_services
    
    # 更新代码
    log_info "拉取最新代码..."
    git pull origin main
    
    # 更新Python依赖
    log_info "更新Python依赖..."
    source "$VENV_PATH/bin/activate"
    pip install -r "$PROJECT_ROOT/backend/requirements.txt"
    
    # 更新前端依赖并重新构建
    log_info "更新前端依赖..."
    cd "$PROJECT_ROOT/frontend"
    npm install
    npm run build
    
    # 启动服务
    start_services
    
    log_success "代码更新和服务重启完成"
}

# 主函数
main() {
    case "${1:-}" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        health)
            health_check
            ;;
        install)
            install_services
            ;;
        update)
            update_services
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
