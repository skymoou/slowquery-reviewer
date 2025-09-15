#!/bin/bash

# ============================================
# 慢查询分析系统 Linux 启动脚本
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检查是否以root权限运行某些命令
check_sudo() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本，脚本会在需要时自动使用sudo"
        exit 1
    fi
}

# 检查虚拟环境
check_venv() {
    if [[ -d "venv" ]]; then
        log_success "找到虚拟环境"
        source venv/bin/activate
    else
        log_error "未找到虚拟环境，请先运行: python3 -m venv venv"
        exit 1
    fi
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖包..."
    
    if ! python -c "import gunicorn" 2>/dev/null; then
        log_warning "gunicorn未安装，正在安装..."
        pip install gunicorn
    fi
    
    log_success "依赖检查完成"
}

# 启动服务
start_server() {
    log_info "启动后端服务..."
    log_info "使用gunicorn服务器"
    
    if [[ -f "gunicorn.conf.py" ]]; then
        gunicorn -c gunicorn.conf.py app:app
    else
        gunicorn -w 2 -b 0.0.0.0:5172 --timeout 300 app:app
    fi
}

# 后台启动服务
start_server_background() {
    log_info "后台启动后端服务..."
    
    if [[ -f "gunicorn.conf.py" ]]; then
        nohup gunicorn -c gunicorn.conf.py app:app > app.log 2>&1 &
    else
        nohup gunicorn -w 2 -b 0.0.0.0:5172 --timeout 300 app:app > app.log 2>&1 &
    fi
    
    log_success "服务已在后台启动，PID: $!"
}

# 停止服务
stop_server() {
    log_info "停止后端服务..."
    pkill -f "gunicorn.*app:app" || true
    log_success "服务已停止"
}

# 检查服务状态
check_status() {
    log_info "检查服务状态..."
    
    # 检查端口5172是否被占用
    if command -v ss >/dev/null 2>&1; then
        if ss -tlnp | grep -q ":5172"; then
            log_success "后端服务正在运行 (端口5172)"
        else
            log_warning "后端服务未运行"
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -an | grep -q ":5172"; then
            log_success "后端服务正在运行 (端口5172)"
        else
            log_warning "后端服务未运行"
        fi
    else
        log_warning "无法检查端口状态 (ss和netstat命令都不可用)"
    fi
    
    # 测试API接口
    if command -v curl >/dev/null 2>&1; then
        if curl -s http://localhost:5172/api/health >/dev/null; then
            log_success "API接口响应正常"
        else
            log_warning "API接口无响应"
        fi
    else
        log_info "无法测试API接口 (curl命令不可用)"
    fi
    
    # 显示进程信息
    local processes=$(ps aux | grep -E "gunicorn.*app:app" | grep -v grep)
    if [[ -n "$processes" ]]; then
        log_info "运行中的服务进程:"
        echo "$processes"
    fi
}

# 显示帮助信息
show_help() {
    echo "慢查询分析系统后端启动脚本 (Linux)"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  start      启动服务 (前台运行)"
    echo "  background 启动服务 (后台运行)"
    echo "  stop       停止服务"
    echo "  restart    重启服务"
    echo "  status     检查服务状态"
    echo "  help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start      # 前台启动服务"
    echo "  $0 background # 后台启动服务"
    echo "  $0 stop       # 停止服务"
    echo "  $0 status     # 检查状态"
    echo ""
    echo "环境要求:"
    echo "  - Python 3.9+ (Rocky Linux 9默认)"
    echo "  - 已创建虚拟环境 (python3 -m venv venv)"
    echo "  - 已安装依赖包 (pip install -r requirements.txt)"
}

# 主函数
main() {
    # 切换到脚本所在目录
    cd "$(dirname "$0")"
    
    log_info "慢查询分析系统 Linux 启动脚本"
    
    # 检查用户权限
    check_sudo
    
    # 检查虚拟环境
    check_venv
    
    # 处理命令行参数
    case "${1:-start}" in
        "start")
            check_dependencies
            start_server
            ;;
        "background"|"bg")
            check_dependencies
            start_server_background
            ;;
        "stop")
            stop_server
            ;;
        "restart")
            stop_server
            sleep 2
            check_dependencies
            start_server_background
            ;;
        "status")
            check_status
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "无效的选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
