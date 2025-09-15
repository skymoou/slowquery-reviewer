#!/bin/bash

# ============================================
# 慢查询分析系统 - 运维管理脚本
# ============================================
# 使用方法：bash manage.sh [command]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置路径
PROJECT_DIR="/opt/slowquery-reviewer"
BACKEND_DIR="$PROJECT_DIR/backend"
LOG_DIR="/var/log/slowquery"
BACKUP_DIR="/opt/backups/slowquery"

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

# 显示帮助信息
show_help() {
    echo "慢查询分析系统 - 运维管理脚本"
    echo
    echo "使用方法: $0 [command]"
    echo
    echo "可用命令:"
    echo "  start           启动所有服务"
    echo "  stop            停止所有服务"
    echo "  restart         重启所有服务"
    echo "  status          查看服务状态"
    echo "  logs            查看实时日志"
    echo "  backup          备份数据库"
    echo "  restore         恢复数据库"
    echo "  update          更新应用"
    echo "  health          健康检查"
    echo "  cleanup         清理日志文件"
    echo "  config          查看配置信息"
    echo "  user            用户管理"
    echo "  help            显示此帮助信息"
    echo
}

# 启动服务
start_services() {
    log_info "启动慢查询分析系统..."
    
    # 启动后端服务
    supervisorctl start slowquery-backend
    log_success "后端服务已启动"
    
    # 启动Nginx
    systemctl start nginx
    log_success "Nginx服务已启动"
    
    # 等待服务就绪
    sleep 3
    
    # 验证服务状态
    if curl -s http://localhost:5172/api/status > /dev/null; then
        log_success "系统启动完成！"
    else
        log_warning "系统启动完成，但API服务可能需要更多时间"
    fi
}

# 停止服务
stop_services() {
    log_info "停止慢查询分析系统..."
    
    # 停止后端服务
    supervisorctl stop slowquery-backend
    log_success "后端服务已停止"
    
    log_success "系统停止完成！"
}

# 重启服务
restart_services() {
    log_info "重启慢查询分析系统..."
    
    # 重启后端服务
    supervisorctl restart slowquery-backend
    log_success "后端服务已重启"
    
    # 重载Nginx配置
    systemctl reload nginx
    log_success "Nginx配置已重载"
    
    # 等待服务就绪
    sleep 3
    
    log_success "系统重启完成！"
}

# 查看服务状态
show_status() {
    echo "============================================"
    echo "慢查询分析系统 - 服务状态"
    echo "============================================"
    echo
    
    echo "=== Supervisor服务状态 ==="
    supervisorctl status
    echo
    
    echo "=== Nginx服务状态 ==="
    systemctl status nginx --no-pager -l
    echo
    
    echo "=== 端口监听状态 ==="
    netstat -tlnp | grep -E "(80|5172)" || echo "无相关端口监听"
    echo
    
    echo "=== 进程信息 ==="
    ps aux | grep -E "(gunicorn|nginx)" | grep -v grep || echo "无相关进程"
    echo
    
    echo "=== 磁盘使用情况 ==="
    df -h $PROJECT_DIR
    echo
    
    echo "=== 内存使用情况 ==="
    free -h
    echo
}

# 查看实时日志
show_logs() {
    echo "显示实时日志 (Ctrl+C 退出)..."
    echo
    
    # 选择日志类型
    echo "请选择要查看的日志:"
    echo "1) 应用日志 (backend)"
    echo "2) Nginx访问日志"
    echo "3) Nginx错误日志"
    echo "4) 所有日志"
    
    read -p "请输入选择 (1-4): " choice
    
    case $choice in
        1)
            tail -f $LOG_DIR/backend.log
            ;;
        2)
            tail -f /var/log/nginx/slowquery_access.log
            ;;
        3)
            tail -f /var/log/nginx/slowquery_error.log
            ;;
        4)
            multitail $LOG_DIR/backend.log /var/log/nginx/slowquery_access.log /var/log/nginx/slowquery_error.log
            ;;
        *)
            log_error "无效的选择"
            ;;
    esac
}

# 备份数据库
backup_database() {
    log_info "开始数据库备份..."
    
    # 创建备份目录
    mkdir -p $BACKUP_DIR
    
    # 生成备份文件名
    DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/database_backup_$DATE.sql"
    
    # 读取数据库配置
    source $BACKEND_DIR/.env
    
    # 执行备份
    mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME > $BACKUP_FILE
    
    if [ $? -eq 0 ]; then
        # 压缩备份文件
        gzip $BACKUP_FILE
        
        log_success "数据库备份完成: ${BACKUP_FILE}.gz"
        
        # 显示备份文件大小
        ls -lh ${BACKUP_FILE}.gz
        
        # 清理旧备份 (保留最近30天)
        find $BACKUP_DIR -name "database_backup_*.sql.gz" -mtime +30 -delete
        log_info "已清理30天前的旧备份文件"
    else
        log_error "数据库备份失败"
        return 1
    fi
}

# 恢复数据库
restore_database() {
    log_warning "数据库恢复操作将覆盖现有数据！"
    read -p "确认继续? (y/N): " confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "操作已取消"
        return 0
    fi
    
    # 列出可用的备份文件
    echo "可用的备份文件:"
    ls -lt $BACKUP_DIR/database_backup_*.sql.gz | head -10
    echo
    
    read -p "请输入要恢复的备份文件名: " backup_file
    
    if [ ! -f "$BACKUP_DIR/$backup_file" ]; then
        log_error "备份文件不存在: $backup_file"
        return 1
    fi
    
    log_info "开始恢复数据库..."
    
    # 停止应用服务
    supervisorctl stop slowquery-backend
    
    # 读取数据库配置
    source $BACKEND_DIR/.env
    
    # 解压并恢复
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$BACKUP_DIR/$backup_file" | mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME
    else
        mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME < "$BACKUP_DIR/$backup_file"
    fi
    
    if [ $? -eq 0 ]; then
        log_success "数据库恢复完成"
        
        # 重启应用服务
        supervisorctl start slowquery-backend
        log_success "应用服务已重启"
    else
        log_error "数据库恢复失败"
        
        # 尝试重启应用服务
        supervisorctl start slowquery-backend
        return 1
    fi
}

# 更新应用
update_application() {
    log_info "准备更新应用..."
    
    # 备份当前版本
    BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
    cp -r $BACKEND_DIR ${BACKEND_DIR}_backup_$BACKUP_DATE
    log_info "当前版本已备份到: ${BACKEND_DIR}_backup_$BACKUP_DATE"
    
    log_warning "请手动上传新版本代码到 $PROJECT_DIR"
    read -p "代码上传完成后按回车继续..."
    
    # 安装新依赖
    cd $PROJECT_DIR
    sudo -u slowquery bash -c "source venv/bin/activate && pip install -r backend/requirements.txt"
    
    # 设置权限
    chown -R slowquery:slowquery $PROJECT_DIR
    
    # 重启服务
    supervisorctl restart slowquery-backend
    systemctl reload nginx
    
    # 验证更新
    sleep 5
    if curl -s http://localhost:5172/api/status > /dev/null; then
        log_success "应用更新完成！"
    else
        log_error "应用更新后服务异常，请检查日志"
        return 1
    fi
}

# 健康检查
health_check() {
    echo "============================================"
    echo "慢查询分析系统 - 健康检查"
    echo "============================================"
    echo
    
    # 检查服务状态
    echo "=== 服务状态检查 ==="
    if supervisorctl status slowquery-backend | grep -q RUNNING; then
        log_success "后端服务运行正常"
    else
        log_error "后端服务异常"
    fi
    
    if systemctl is-active nginx >/dev/null; then
        log_success "Nginx服务运行正常"
    else
        log_error "Nginx服务异常"
    fi
    echo
    
    # 检查API可用性
    echo "=== API可用性检查 ==="
    if curl -s http://localhost:5172/api/status > /dev/null; then
        log_success "API服务正常"
        
        # 获取API响应详情
        API_RESPONSE=$(curl -s http://localhost:5172/api/status)
        echo "API响应: $API_RESPONSE"
    else
        log_error "API服务不可访问"
    fi
    echo
    
    # 检查数据库连接
    echo "=== 数据库连接检查 ==="
    source $BACKEND_DIR/.env
    if mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "USE $DB_NAME; SELECT 1;" >/dev/null 2>&1; then
        log_success "数据库连接正常"
    else
        log_error "数据库连接失败"
    fi
    echo
    
    # 检查磁盘空间
    echo "=== 磁盘空间检查 ==="
    DISK_USAGE=$(df $PROJECT_DIR | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $DISK_USAGE -lt 80 ]; then
        log_success "磁盘空间充足 (${DISK_USAGE}%)"
    elif [ $DISK_USAGE -lt 90 ]; then
        log_warning "磁盘空间告警 (${DISK_USAGE}%)"
    else
        log_error "磁盘空间不足 (${DISK_USAGE}%)"
    fi
    echo
    
    # 检查内存使用
    echo "=== 内存使用检查 ==="
    MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    echo "内存使用率: ${MEMORY_USAGE}%"
    echo
}

# 清理日志文件
cleanup_logs() {
    log_info "开始清理日志文件..."
    
    # 清理应用日志 (保留最近7天)
    find $LOG_DIR -name "*.log" -mtime +7 -exec rm -f {} \;
    
    # 清理Nginx日志 (保留最近30天)
    find /var/log/nginx -name "slowquery_*.log*" -mtime +30 -exec rm -f {} \;
    
    # 清理备份文件 (保留最近30天)
    find $BACKUP_DIR -name "database_backup_*.sql.gz" -mtime +30 -exec rm -f {} \;
    
    log_success "日志清理完成"
    
    # 显示当前日志文件大小
    echo "当前日志文件大小:"
    du -sh $LOG_DIR
    du -sh /var/log/nginx/slowquery_*
}

# 查看配置信息
show_config() {
    echo "============================================"
    echo "慢查询分析系统 - 配置信息"
    echo "============================================"
    echo
    
    echo "=== 项目路径 ==="
    echo "项目目录: $PROJECT_DIR"
    echo "后端目录: $BACKEND_DIR"
    echo "日志目录: $LOG_DIR"
    echo "备份目录: $BACKUP_DIR"
    echo
    
    echo "=== 数据库配置 ==="
    if [ -f "$BACKEND_DIR/.env" ]; then
        grep "DB_" $BACKEND_DIR/.env | sed 's/=.*/=***/'
    else
        echo "配置文件不存在"
    fi
    echo
    
    echo "=== 服务配置 ==="
    echo "Nginx配置: /etc/nginx/sites-available/slowquery-reviewer"
    echo "Supervisor配置: /etc/supervisor/conf.d/slowquery.conf"
    echo
    
    echo "=== 端口配置 ==="
    echo "前端端口: 80"
    echo "后端端口: 5172"
    echo "数据库端口: 3306"
    echo
}

# 用户管理
manage_users() {
    echo "用户管理功能"
    echo
    echo "1) 创建管理员用户"
    echo "2) 重置用户密码"
    echo "3) 列出所有用户"
    echo "4) 删除用户"
    
    read -p "请选择操作 (1-4): " choice
    
    cd $BACKEND_DIR
    
    case $choice in
        1)
            read -p "请输入用户名: " username
            read -p "请输入邮箱: " email
            read -s -p "请输入密码: " password
            echo
            
            sudo -u slowquery bash -c "source ../venv/bin/activate && python -c \"
import sys
sys.path.append('.')
from auth import create_user
if create_user('$username', '$password', '$email', is_admin=True):
    print('管理员用户创建成功')
else:
    print('用户创建失败')
\""
            ;;
        2)
            read -p "请输入用户名: " username
            read -s -p "请输入新密码: " password
            echo
            
            sudo -u slowquery bash -c "source ../venv/bin/activate && python -c \"
import sys
sys.path.append('.')
from auth import reset_password
if reset_password('$username', '$password'):
    print('密码重置成功')
else:
    print('密码重置失败')
\""
            ;;
        3)
            sudo -u slowquery bash -c "source ../venv/bin/activate && python -c \"
import sys
sys.path.append('.')
from db import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute('SELECT id, username, email, status, created_at FROM users')
users = cursor.fetchall()
print('用户列表:')
for user in users:
    print(f'ID: {user[0]}, 用户名: {user[1]}, 邮箱: {user[2]}, 状态: {user[3]}, 创建时间: {user[4]}')
cursor.close()
conn.close()
\""
            ;;
        4)
            read -p "请输入要删除的用户名: " username
            read -p "确认删除用户 $username? (y/N): " confirm
            
            if [[ "$confirm" =~ ^[Yy]$ ]]; then
                sudo -u slowquery bash -c "source ../venv/bin/activate && python -c \"
import sys
sys.path.append('.')
from db import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute('DELETE FROM users WHERE username = %s', ('$username',))
conn.commit()
print(f'用户 $username 已删除')
cursor.close()
conn.close()
\""
            fi
            ;;
        *)
            log_error "无效的选择"
            ;;
    esac
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
        backup)
            backup_database
            ;;
        restore)
            restore_database
            ;;
        update)
            update_application
            ;;
        health)
            health_check
            ;;
        cleanup)
            cleanup_logs
            ;;
        config)
            show_config
            ;;
        user)
            manage_users
            ;;
        help|"")
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 检查是否为root用户
if [[ $EUID -eq 0 ]] && [[ "${1:-}" != "help" ]]; then
    log_warning "建议使用普通用户执行此脚本"
fi

# 执行主函数
main "$@"
