#!/bin/bash

# 增量代码更新脚本
# 用途：将GitHub上的最新代码变更同步到已运行的Linux服务器

set -e

# 配置参数 - 请根据你的服务器实际情况修改
PROJECT_PATH="/opt/slowquery-reviewer"  # 服务器上的项目路径
SERVICE_NAME="slowquery-reviewer"       # Supervisor中的服务名称

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# 检查项目目录是否存在
if [ ! -d "$PROJECT_PATH" ]; then
    log_error "项目目录不存在: $PROJECT_PATH"
    log_error "请检查路径或先完成初始部署"
    exit 1
fi

cd "$PROJECT_PATH"

log_info "🔄 开始增量代码更新..."

# 1. 查看当前状态
log_info "📊 当前版本信息："
CURRENT_COMMIT=$(git rev-parse HEAD)
echo "   当前提交: ${CURRENT_COMMIT:0:7} - $(git log -1 --format='%s')"

# 2. 拉取最新代码
log_info "📥 拉取最新代码..."
git fetch origin main

# 3. 检查是否有更新
LATEST_COMMIT=$(git rev-parse origin/main)
if [ "$CURRENT_COMMIT" = "$LATEST_COMMIT" ]; then
    log_success "✅ 代码已是最新版本，无需更新"
    exit 0
fi

log_info "📋 发现代码更新："
echo "   从: ${CURRENT_COMMIT:0:7}"
echo "   到: ${LATEST_COMMIT:0:7}"

# 4. 显示变更的文件
log_info "📝 变更文件列表："
git diff --name-only $CURRENT_COMMIT $LATEST_COMMIT | while read file; do
    echo "   - $file"
done

# 5. 停止后端服务
log_info "⏹️  停止后端服务..."
if sudo supervisorctl status $SERVICE_NAME >/dev/null 2>&1; then
    sudo supervisorctl stop $SERVICE_NAME
    log_success "后端服务已停止"
else
    log_warning "服务可能已经停止或不存在"
fi

# 6. 备份配置文件
log_info "💾 备份重要配置文件..."
CONFIG_BACKUP_DIR="/tmp/slowquery_config_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$CONFIG_BACKUP_DIR"

# 备份重要配置文件
if [ -f "backend/config.py" ]; then
    cp "backend/config.py" "$CONFIG_BACKUP_DIR/"
    log_success "已备份 backend/config.py"
fi

if [ -f "backend/.env" ]; then
    cp "backend/.env" "$CONFIG_BACKUP_DIR/"
    log_success "已备份 backend/.env"
fi

# 7. 更新代码（使用 stash 保护本地配置）
log_info "🔄 应用代码更新（保护本地配置）..."

# 暂存本地配置文件
git add -A
if git diff --cached --quiet; then
    log_info "无本地配置变更"
else
    git stash push -m "自动备份本地配置 $(date)"
    log_info "已暂存本地配置文件"
fi

# 拉取远程更新
git pull origin main

# 恢复本地配置文件
if [ -f "$CONFIG_BACKUP_DIR/config.py" ]; then
    cp "$CONFIG_BACKUP_DIR/config.py" "backend/config.py"
    log_success "已恢复 backend/config.py 配置"
fi

if [ -f "$CONFIG_BACKUP_DIR/.env" ]; then
    cp "$CONFIG_BACKUP_DIR/.env" "backend/.env"
    log_success "已恢复 backend/.env 配置"
fi

# 8. 检查是否有后端文件变更
BACKEND_CHANGED=$(git diff --name-only $CURRENT_COMMIT $LATEST_COMMIT | grep -c "backend/" || echo "0")
FRONTEND_CHANGED=$(git diff --name-only $CURRENT_COMMIT $LATEST_COMMIT | grep -c "frontend/" || echo "0")

if [ "$BACKEND_CHANGED" -gt 0 ]; then
    log_info "🔧 检测到后端变更，检查依赖..."
    cd backend
    
    # 激活虚拟环境
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        # 检查是否需要更新依赖
        if git diff --name-only $CURRENT_COMMIT $LATEST_COMMIT | grep -q "requirements.txt"; then
            log_info "📦 更新Python依赖..."
            pip install -r requirements.txt
        fi
    else
        log_warning "虚拟环境不存在，请检查部署"
    fi
    cd ..
fi

if [ "$FRONTEND_CHANGED" -gt 0 ]; then
    log_info "🏗️  检测到前端变更，重新构建..."
    cd frontend
    
    # 检查package.json是否有变更
    if git diff --name-only $CURRENT_COMMIT $LATEST_COMMIT | grep -q "package.json"; then
        log_info "📦 更新前端依赖..."
        npm install
    fi
    
    log_info "🔨 重新构建前端..."
    npm run build
    cd ..
else
    log_info "✅ 前端无变更，跳过构建"
fi

# 9. 启动后端服务
log_info "🚀 启动后端服务..."
sudo supervisorctl start $SERVICE_NAME

# 10. 等待服务启动并检查状态
sleep 3
if sudo supervisorctl status $SERVICE_NAME | grep -q "RUNNING"; then
    log_success "✅ 后端服务启动成功"
else
    log_error "❌ 后端服务启动失败"
    log_info "📋 服务日志："
    sudo supervisorctl tail $SERVICE_NAME
    exit 1
fi

# 11. 重新加载Nginx（如果有前端变更）
if [ "$FRONTEND_CHANGED" -gt 0 ]; then
    log_info "🔄 重新加载Nginx..."
    sudo systemctl reload nginx
fi

# 12. 健康检查
log_info "🏥 执行健康检查..."
sleep 2

# 检查后端API
if curl -f -s http://localhost:5172/ >/dev/null 2>&1; then
    log_success "✅ 后端API响应正常"
else
    log_warning "⚠️  后端API检查失败，请手动验证"
fi

# 检查前端
if curl -f -s http://localhost/ >/dev/null 2>&1; then
    log_success "✅ 前端页面访问正常"
else
    log_warning "⚠️  前端页面检查失败，请手动验证"
fi

# 13. 显示更新完成信息
log_success "🎉 增量更新完成！"
echo
echo "📊 更新摘要："
echo "   更新版本: ${LATEST_COMMIT:0:7} - $(git log -1 --format='%s')"
echo "   后端变更: $BACKEND_CHANGED 个文件"
echo "   前端变更: $FRONTEND_CHANGED 个文件"
echo
echo "🔗 验证地址："
echo "   前端: http://your-server-ip/"
echo "   后端: http://your-server-ip:5172/"
echo
echo "📝 查看服务状态："
echo "   sudo supervisorctl status $SERVICE_NAME"
echo "   sudo tail -f /var/log/slowquery-reviewer.log"

# 特别提醒新功能
if git log --oneline $CURRENT_COMMIT..$LATEST_COMMIT | grep -q "排序\|sort"; then
    echo
    log_success "🎯 提醒：本次更新包含排序功能优化"
    echo "   请在前端测试用户名/数据库名过滤后的排序效果"
fi
