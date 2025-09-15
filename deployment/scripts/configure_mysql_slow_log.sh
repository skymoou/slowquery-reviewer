#!/bin/bash

# MySQL慢查询日志配置脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
if [[ $EUID -ne 0 ]]; then
    log_error "此脚本需要root权限运行"
    exit 1
fi

# 检测MySQL配置文件位置
detect_mysql_config() {
    local config_files=(
        "/etc/my.cnf"
        "/etc/mysql/my.cnf"
        "/etc/mysql/mysql.conf.d/mysqld.cnf"
        "/etc/my.cnf.d/server.cnf"
        "/etc/mysql/mariadb.conf.d/50-server.cnf"
    )
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            echo "$config_file"
            return 0
        fi
    done
    
    return 1
}

# 配置慢查询日志
configure_slow_query_log() {
    log_info "配置MySQL慢查询日志..."
    
    # 检测配置文件
    CONFIG_FILE=$(detect_mysql_config)
    if [[ $? -ne 0 ]]; then
        log_error "未找到MySQL配置文件"
        exit 1
    fi
    
    log_info "使用配置文件: $CONFIG_FILE"
    
    # 备份原配置文件
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    log_info "已备份原配置文件到: ${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # 创建日志目录
    mkdir -p /var/log/mysql
    chown mysql:mysql /var/log/mysql
    chmod 755 /var/log/mysql
    
    # 读取用户配置
    echo "请配置慢查询参数："
    read -p "慢查询阈值（秒，默认2）: " SLOW_QUERY_TIME
    SLOW_QUERY_TIME=${SLOW_QUERY_TIME:-2}
    
    read -p "是否记录未使用索引的查询？(y/N): " LOG_QUERIES_NOT_USING_INDEXES
    if [[ $LOG_QUERIES_NOT_USING_INDEXES =~ ^[Yy]$ ]]; then
        LOG_QUERIES_NOT_USING_INDEXES="1"
    else
        LOG_QUERIES_NOT_USING_INDEXES="0"
    fi
    
    read -p "慢查询日志文件路径（默认/var/log/mysql/slow.log）: " SLOW_LOG_PATH
    SLOW_LOG_PATH=${SLOW_LOG_PATH:-/var/log/mysql/slow.log}
    
    # 检查配置文件是否包含[mysqld]或[mariadb]部分
    if ! grep -q "^\[mysqld\]" "$CONFIG_FILE" && ! grep -q "^\[mariadb\]" "$CONFIG_FILE"; then
        log_warn "配置文件中未找到[mysqld]或[mariadb]部分，将添加[mysqld]部分"
        echo -e "\n[mysqld]" >> "$CONFIG_FILE"
    fi
    
    # 添加慢查询配置
    log_info "添加慢查询配置..."
    
    # 检查是否已存在慢查询配置
    if grep -q "slow_query_log" "$CONFIG_FILE"; then
        log_warn "检测到已存在的慢查询配置，将注释掉旧配置"
        sed -i 's/^slow_query_log/#slow_query_log/g' "$CONFIG_FILE"
        sed -i 's/^long_query_time/#long_query_time/g' "$CONFIG_FILE"
        sed -i 's/^slow_query_log_file/#slow_query_log_file/g' "$CONFIG_FILE"
        sed -i 's/^log_queries_not_using_indexes/#log_queries_not_using_indexes/g' "$CONFIG_FILE"
    fi
    
    # 在[mysqld]部分后添加配置
    if grep -q "^\[mysqld\]" "$CONFIG_FILE"; then
        sed -i '/^\[mysqld\]/a\
# Slow Query Log Configuration - Added by deploy script\
slow_query_log = 1\
long_query_time = '$SLOW_QUERY_TIME'\
slow_query_log_file = '$SLOW_LOG_PATH'\
log_queries_not_using_indexes = '$LOG_QUERIES_NOT_USING_INDEXES'\
# End of Slow Query Log Configuration' "$CONFIG_FILE"
    elif grep -q "^\[mariadb\]" "$CONFIG_FILE"; then
        sed -i '/^\[mariadb\]/a\
# Slow Query Log Configuration - Added by deploy script\
slow_query_log = 1\
long_query_time = '$SLOW_QUERY_TIME'\
slow_query_log_file = '$SLOW_LOG_PATH'\
log_queries_not_using_indexes = '$LOG_QUERIES_NOT_USING_INDEXES'\
# End of Slow Query Log Configuration' "$CONFIG_FILE"
    fi
    
    log_info "慢查询配置已添加到 $CONFIG_FILE"
}

# 创建日志轮转配置
configure_log_rotation() {
    log_info "配置日志轮转..."
    
    cat > /etc/logrotate.d/mysql-slow << 'EOF'
/var/log/mysql/slow.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 mysql mysql
    postrotate
        # 重新打开慢查询日志文件
        if test -x /usr/bin/mysqladmin && /usr/bin/mysqladmin ping &>/dev/null; then
            /usr/bin/mysqladmin flush-logs
        fi
    endscript
}
EOF
    
    log_info "日志轮转配置已创建"
}

# 设置慢日志解析定时任务
setup_cron_job() {
    log_info "设置慢日志解析定时任务..."
    
    # 为slowquery用户创建crontab
    sudo -u slowquery bash -c '
    # 检查是否已存在定时任务
    if ! crontab -l 2>/dev/null | grep -q "server_side_slow_log_parser.py"; then
        # 创建新的crontab条目
        (crontab -l 2>/dev/null; echo "0 2 * * * cd /opt/slowquery-reviewer/backend && ./venv/bin/python server_side_slow_log_parser.py --auto-save >> /var/log/slowquery/parser.log 2>&1") | crontab -
        echo "定时任务已添加"
    else
        echo "定时任务已存在，跳过添加"
    fi
    '
    
    log_info "定时任务配置完成（每天凌晨2点执行）"
}

# 测试配置
test_configuration() {
    log_info "测试MySQL配置..."
    
    # 测试配置文件语法
    if command -v mysqld &> /dev/null; then
        if mysqld --help --verbose &>/dev/null; then
            log_info "✓ MySQL配置文件语法正确"
        else
            log_error "✗ MySQL配置文件语法错误"
            return 1
        fi
    fi
    
    return 0
}

# 重启MySQL服务
restart_mysql() {
    log_info "重启MySQL服务以应用配置..."
    
    # 检测服务名称
    if systemctl is-active --quiet mariadb; then
        SERVICE_NAME="mariadb"
    elif systemctl is-active --quiet mysql; then
        SERVICE_NAME="mysql"
    elif systemctl is-active --quiet mysqld; then
        SERVICE_NAME="mysqld"
    else
        log_error "未找到运行中的MySQL服务"
        return 1
    fi
    
    log_info "重启 $SERVICE_NAME 服务..."
    systemctl restart "$SERVICE_NAME"
    
    # 等待服务启动
    sleep 3
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "✓ $SERVICE_NAME 服务重启成功"
    else
        log_error "✗ $SERVICE_NAME 服务重启失败"
        systemctl status "$SERVICE_NAME"
        return 1
    fi
}

# 验证慢查询日志配置
verify_slow_query_config() {
    log_info "验证慢查询日志配置..."
    
    # 读取MySQL root密码
    read -p "请输入MySQL root密码以验证配置: " -s ROOT_PASSWORD
    echo
    
    # 检查慢查询日志设置
    mysql -u root -p"$ROOT_PASSWORD" -e "
    SHOW VARIABLES LIKE 'slow_query_log%';
    SHOW VARIABLES LIKE 'long_query_time';
    SHOW VARIABLES LIKE 'log_queries_not_using_indexes';
    "
    
    if [[ $? -eq 0 ]]; then
        log_info "✓ 慢查询日志配置验证成功"
    else
        log_error "✗ 慢查询日志配置验证失败"
        return 1
    fi
    
    # 检查日志文件权限
    if [[ -f "$SLOW_LOG_PATH" ]]; then
        log_info "✓ 慢查询日志文件已创建: $SLOW_LOG_PATH"
        ls -la "$SLOW_LOG_PATH"
    else
        log_warn "慢查询日志文件尚未创建，将在有慢查询时自动创建"
    fi
}

# 显示配置摘要
show_configuration_summary() {
    echo
    log_info "=== 配置摘要 ==="
    echo "慢查询阈值: ${SLOW_QUERY_TIME} 秒"
    echo "记录未使用索引的查询: $([ "$LOG_QUERIES_NOT_USING_INDEXES" = "1" ] && echo "是" || echo "否")"
    echo "慢查询日志文件: $SLOW_LOG_PATH"
    echo "配置文件: $CONFIG_FILE"
    echo "定时解析: 每天凌晨2点"
    echo "日志轮转: 每天，保留30天"
    echo
    log_info "=== 后续步骤 ==="
    echo "1. 监控慢查询日志文件生成"
    echo "2. 等待定时任务自动解析，或手动运行:"
    echo "   cd /opt/slowquery-reviewer/backend"
    echo "   sudo -u slowquery ./venv/bin/python server_side_slow_log_parser.py"
    echo "3. 通过Web界面查看解析结果"
    echo
}

# 主函数
main() {
    log_info "开始配置MySQL慢查询日志..."
    
    configure_slow_query_log
    configure_log_rotation
    
    if test_configuration; then
        restart_mysql
        setup_cron_job
        verify_slow_query_config
        show_configuration_summary
        
        log_info "MySQL慢查询日志配置完成！"
    else
        log_error "配置验证失败，请检查配置文件"
        exit 1
    fi
}

# 执行主函数
main "$@"
