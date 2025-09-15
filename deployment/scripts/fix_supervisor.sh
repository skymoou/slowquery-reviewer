#!/bin/bash

# ============================================
# Supervisor配置修复脚本
# 解决环境变量格式错误问题
# ============================================

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

# 检查是否存在配置文件
CONFIG_FILE="/etc/supervisor/conf.d/slowquery.conf"

if [[ ! -f "$CONFIG_FILE" ]]; then
    log_error "Supervisor配置文件不存在: $CONFIG_FILE"
    exit 1
fi

log_info "检查Supervisor配置文件..."

# 备份原配置文件
log_info "备份原配置文件..."
sudo cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

# 检查是否存在多行环境变量配置错误
if grep -q "environment=.*,$" "$CONFIG_FILE"; then
    log_warning "发现多行环境变量配置，正在修复..."
    
    # 创建临时文件修复配置
    TEMP_FILE="/tmp/slowquery_fixed.conf"
    
    # 使用awk修复多行环境变量
    awk '
    /^environment=/ {
        # 如果是环境变量行且以逗号结尾，收集所有相关行
        line = $0
        while (line ~ /,$/ && getline next > 0) {
            # 移除换行和前导空格
            gsub(/^[ \t]+/, "", next)
            line = line next
        }
        # 如果next不是以逗号结尾，也添加到line中
        if (next && next !~ /,$/) {
            gsub(/^[ \t]+/, "", next)
            line = line next
        }
        print line
        next
    }
    # 跳过以空格开头的环境变量继续行
    /^[ \t]+[A-Z_]+=/ { next }
    # 打印其他所有行
    { print }
    ' "$CONFIG_FILE" > "$TEMP_FILE"
    
    # 替换原配置文件
    sudo mv "$TEMP_FILE" "$CONFIG_FILE"
    sudo chown root:root "$CONFIG_FILE"
    sudo chmod 644 "$CONFIG_FILE"
    
    log_success "配置文件已修复"
else
    log_info "配置文件格式正确，无需修复"
fi

# 验证配置文件语法
log_info "验证Supervisor配置语法..."
if sudo supervisorctl reread 2>&1 | grep -q "ERROR"; then
    log_error "配置文件仍有语法错误，请手动检查"
    log_info "配置文件路径: $CONFIG_FILE"
    log_info "查看错误: sudo supervisorctl reread"
    exit 1
else
    log_success "配置文件语法验证通过"
fi

# 重载配置
log_info "重载Supervisor配置..."
sudo supervisorctl reread
sudo supervisorctl update

# 检查服务状态
log_info "检查服务状态..."
sudo supervisorctl status slowquery:*

log_success "Supervisor配置修复完成！"
echo ""
log_info "如果服务未运行，请执行:"
echo "  sudo supervisorctl start slowquery:*"
echo ""
log_info "查看服务日志:"
echo "  sudo supervisorctl tail slowquery-backend"
echo "  sudo supervisorctl tail slowquery-frontend"
