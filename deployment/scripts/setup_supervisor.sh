#!/bin/bash

# =================================================
# 慢查询分析系统 Supervisor 自动配置脚本
# =================================================

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

# 检查是否以root权限运行某些命令
check_sudo() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本，脚本会在需要时自动使用sudo"
        exit 1
    fi
}

# 检查系统环境
check_environment() {
    log_info "检查系统环境..."
    
    # 检查操作系统
    if [[ -f /etc/rocky-release ]]; then
        log_success "检测到Rocky Linux系统，推荐使用！"
        OS_TYPE="rocky"
    elif [[ -f /etc/redhat-release ]]; then
        log_info "检测到RHEL兼容系统"
        OS_TYPE="rhel"
    elif [[ -f /etc/debian_version ]]; then
        log_info "检测到Debian/Ubuntu系统"
        OS_TYPE="debian"
    else
        log_warning "未知操作系统，建议使用Rocky Linux 9.x系统以获得最佳体验"
        OS_TYPE="unknown"
    fi
    
    # 检查权限
    if [[ $EUID -eq 0 ]]; then
        log_warning "建议不要以root用户运行此脚本"
    fi
    
    # 检查必要命令
    for cmd in systemctl python3 pip3 npm; do
        if ! command -v $cmd &> /dev/null; then
            if [[ "$cmd" == "npm" ]]; then
                log_warning "命令 $cmd 未找到，请先安装Node.js"
                log_info "Rocky Linux安装命令: sudo dnf install -y nodejs npm"
            else
                log_error "命令 $cmd 未找到，请先安装必要依赖"
                exit 1
            fi
        fi
    done
    
    log_success "环境检查通过"
}

# 检查Supervisor是否已安装
check_supervisor() {
    log_info "检查Supervisor安装状态..."
    
    if ! command -v supervisorctl &> /dev/null; then
        log_warning "Supervisor未安装，正在安装..."
        
        # 检测操作系统
        if [[ -f /etc/rocky-release ]]; then
            # Rocky Linux
            sudo dnf install -y epel-release
            sudo dnf install -y supervisor
        elif [[ -f /etc/redhat-release ]]; then
            # RHEL/CentOS
            sudo dnf install -y epel-release
            sudo dnf install -y supervisor
        elif [[ -f /etc/debian_version ]]; then
            # Debian/Ubuntu
            sudo apt update
            sudo apt install -y supervisor
        else
            log_error "不支持的操作系统，请手动安装Supervisor"
            exit 1
        fi
        
        # 启动服务
        sudo systemctl start supervisord 2>/dev/null || sudo systemctl start supervisor
        sudo systemctl enable supervisord 2>/dev/null || sudo systemctl enable supervisor
        
        log_success "Supervisor安装完成"
    else
        log_success "Supervisor已安装"
    fi
}

# 获取项目路径
get_project_path() {
    # 获取脚本所在目录的上级目录作为项目根目录
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_PATH="$(dirname "$SCRIPT_DIR")"
    
    log_info "项目路径: $PROJECT_PATH"
    
    # 验证项目结构
    if [[ ! -f "$PROJECT_PATH/backend/app.py" ]]; then
        log_error "项目结构不正确，未找到 backend/app.py"
        exit 1
    fi
    
    if [[ ! -f "$PROJECT_PATH/frontend/package.json" ]]; then
        log_error "项目结构不正确，未找到 frontend/package.json"
        exit 1
    fi
}

# 检查虚拟环境
check_venv() {
    log_info "检查Python虚拟环境..."
    
    VENV_PATH="$PROJECT_PATH/backend/venv"
    
    if [[ ! -d "$VENV_PATH" ]]; then
        log_warning "虚拟环境不存在，正在创建..."
        cd "$PROJECT_PATH/backend"
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        log_success "虚拟环境创建完成"
    else
        log_success "虚拟环境已存在"
    fi
    
    # 检查gunicorn是否安装
    if [[ ! -f "$VENV_PATH/bin/gunicorn" ]]; then
        log_warning "gunicorn未安装，正在安装..."
        source "$VENV_PATH/bin/activate"
        pip install gunicorn
        log_success "gunicorn安装完成"
    fi
}

# 检查Node.js依赖
check_nodejs() {
    log_info "检查Node.js依赖..."
    
    cd "$PROJECT_PATH/frontend"
    
    if [[ ! -d "node_modules" ]]; then
        log_warning "Node.js依赖未安装，正在安装..."
        npm install
        log_success "Node.js依赖安装完成"
    else
        log_success "Node.js依赖已安装"
    fi
    
    # 构建前端
    if [[ ! -d "dist" ]]; then
        log_info "构建前端应用..."
        npm run build
        log_success "前端构建完成"
    fi
}

# 生成配置文件
generate_config() {
    log_info "生成Supervisor配置文件..."
    
    USERNAME=$(whoami)
    VENV_PYTHON="$PROJECT_PATH/backend/venv/bin/python"
    VENV_GUNICORN="$PROJECT_PATH/backend/venv/bin/gunicorn"
    GUNICORN_CONFIG="$PROJECT_PATH/backend/gunicorn.conf.py"
    
    # 检查npm路径
    NPM_PATH=$(which npm)
    if [[ -z "$NPM_PATH" ]]; then
        log_error "未找到npm命令，请确保Node.js已正确安装"
        exit 1
    fi
    
    # 检查gunicorn配置文件
    if [[ ! -f "$GUNICORN_CONFIG" ]]; then
        log_error "未找到gunicorn配置文件: $GUNICORN_CONFIG"
        exit 1
    fi
    
    # 创建配置文件
    CONFIG_FILE="/tmp/slowquery.conf"
    
    cat > "$CONFIG_FILE" << EOF
# ============================================
# 慢查询分析系统 Supervisor 配置文件
# 自动生成于: $(date)
# ============================================

[group:slowquery]
programs=slowquery-backend,slowquery-frontend

# ============================================
# 后端服务配置 (Gunicorn + Supervisor)
# ============================================
[program:slowquery-backend]
command=$VENV_GUNICORN -c $GUNICORN_CONFIG app:app
directory=$PROJECT_PATH/backend
user=$USERNAME
autostart=true
autorestart=true
autorestart=unexpected
startretries=3
startsecs=10
redirect_stderr=true
stdout_logfile=/var/log/supervisor/slowquery-backend.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
stderr_logfile=/var/log/supervisor/slowquery-backend-error.log
stderr_logfile_maxbytes=50MB
stderr_logfile_backups=10
stopsignal=TERM
stopwaitsecs=30
killasgroup=true
stopasgroup=true
priority=100
environment=PATH="$PROJECT_PATH/backend/venv/bin:/usr/bin:/usr/local/bin",PYTHONPATH="$PROJECT_PATH/backend",FLASK_ENV="production"

# ============================================
# 前端服务配置 (Vite Preview + Supervisor)
# ============================================
[program:slowquery-frontend]
command=$NPM_PATH run preview -- --host 0.0.0.0 --port 4173
directory=$PROJECT_PATH/frontend
user=$USERNAME
autostart=true
autorestart=true
autorestart=unexpected
startretries=3
startsecs=10
redirect_stderr=true
stdout_logfile=/var/log/supervisor/slowquery-frontend.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
stderr_logfile=/var/log/supervisor/slowquery-frontend-error.log
stderr_logfile_maxbytes=50MB
stderr_logfile_backups=10
stopsignal=TERM
stopwaitsecs=10
killasgroup=true
stopasgroup=true
priority=200
environment=NODE_ENV=production,PATH="/usr/bin:/usr/local/bin:$HOME/.local/bin"
EOF
    
    log_success "配置文件生成完成: $CONFIG_FILE"
}

# 安装配置文件
install_config() {
    log_info "安装Supervisor配置文件..."
    
    # 创建日志目录
    sudo mkdir -p /var/log/supervisor
    
    # 复制配置文件
    sudo cp "$CONFIG_FILE" /etc/supervisor/conf.d/slowquery.conf
    
    # 设置权限
    sudo chown root:root /etc/supervisor/conf.d/slowquery.conf
    sudo chmod 644 /etc/supervisor/conf.d/slowquery.conf
    
    log_success "配置文件安装完成"
}

# 重载Supervisor配置
reload_supervisor() {
    log_info "重载Supervisor配置..."
    
    sudo supervisorctl reread
    sudo supervisorctl update
    
    log_success "Supervisor配置重载完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    sudo supervisorctl start slowquery:*
    
    # 等待几秒让服务启动
    sleep 3
    
    # 检查服务状态
    log_info "检查服务状态..."
    sudo supervisorctl status slowquery:*
}

# 显示管理命令
show_management_commands() {
    log_success "=== 服务部署完成 ==="
    echo ""
    log_info "常用管理命令："
    echo "  查看服务状态: sudo supervisorctl status"
    echo "  启动所有服务: sudo supervisorctl start slowquery:*"
    echo "  停止所有服务: sudo supervisorctl stop slowquery:*"
    echo "  重启所有服务: sudo supervisorctl restart slowquery:*"
    echo "  查看后端日志: sudo supervisorctl tail slowquery-backend"
    echo "  查看前端日志: sudo supervisorctl tail slowquery-frontend"
    echo ""
    log_info "访问地址："
    echo "  前端界面: http://localhost:4173"
    echo "  后端API: http://localhost:5172/api/health"
    echo ""
    log_info "默认登录账户："
    echo "  管理员: admin / Admin@123"
    echo "  DBA: dba / Dba@123"
    echo "  开发者: dev / Dev@123"
    echo ""
    log_warning "请及时修改默认密码！"
}

# 主函数
main() {
    log_info "开始配置慢查询分析系统的Supervisor服务..."
    
    check_sudo
    check_environment
    check_supervisor
    get_project_path
    check_venv
    check_nodejs
    generate_config
    install_config
    reload_supervisor
    start_services
    show_management_commands
    
    log_success "配置完成！"
}

# 运行主函数
main "$@"
