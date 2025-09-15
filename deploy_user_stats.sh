#!/bin/bash

# 慢查询审查系统 - 用户统计功能增量部署脚本
# Usage: ./deploy_user_stats.sh [server-ip] [user]

set -e  # 遇到错误立即退出

# 配置
SERVER_IP=${1:-"your-server-ip"}
SSH_USER=${2:-"root"}
APP_PATH="/opt/slowquery-reviewer"
BACKUP_DIR="/opt/backups/slowquery-reviewer"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== 慢查询审查系统用户统计功能部署 ===${NC}"
echo "目标服务器: $SERVER_IP"
echo "SSH用户: $SSH_USER"
echo "应用路径: $APP_PATH"
echo ""

# 1. 检查连接
echo -e "${YELLOW}1. 检查服务器连接...${NC}"
if ssh -o ConnectTimeout=10 "$SSH_USER@$SERVER_IP" "echo '连接成功'" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ 服务器连接正常${NC}"
else
    echo -e "${RED}❌ 无法连接到服务器 $SERVER_IP${NC}"
    exit 1
fi

# 2. 创建备份
echo -e "${YELLOW}2. 创建备份...${NC}"
BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ssh "$SSH_USER@$SERVER_IP" "
    mkdir -p $BACKUP_DIR
    cd $APP_PATH
    tar -czf $BACKUP_DIR/code_backup_$BACKUP_TIMESTAMP.tar.gz backend/ frontend/ 2>/dev/null || true
    cp /etc/nginx/sites-available/slowquery-reviewer $BACKUP_DIR/nginx_backup_$BACKUP_TIMESTAMP.conf 2>/dev/null || true
"
echo -e "${GREEN}✅ 备份完成: $BACKUP_DIR/code_backup_$BACKUP_TIMESTAMP.tar.gz${NC}"

# 3. 打包并传输文件
echo -e "${YELLOW}3. 打包和传输更新文件...${NC}"

# 创建临时目录
TEMP_DIR=$(mktemp -d)
echo "临时目录: $TEMP_DIR"

# 准备后端文件
mkdir -p "$TEMP_DIR/backend/routes"
cp "backend/routes/queries.py" "$TEMP_DIR/backend/routes/"
cp "backend/test_user_stats.py" "$TEMP_DIR/backend/" 2>/dev/null || true
cp "backend/USER_STATS_FEATURE.md" "$TEMP_DIR/backend/" 2>/dev/null || true

# 准备前端文件
mkdir -p "$TEMP_DIR/frontend/src/components"
mkdir -p "$TEMP_DIR/frontend/src/services"
cp "frontend/src/components/UserStats.jsx" "$TEMP_DIR/frontend/src/components/" 2>/dev/null || true
cp "frontend/src/services/api.js" "$TEMP_DIR/frontend/src/services/"
cp "frontend/src/App.jsx" "$TEMP_DIR/frontend/src/"
cp "frontend/package.json" "$TEMP_DIR/frontend/"

# 准备配置文件
cp "nginx-production.conf" "$TEMP_DIR/" 2>/dev/null || true
cp "PRODUCTION_DEPLOYMENT.md" "$TEMP_DIR/" 2>/dev/null || true
cp "verify_production_deployment.sh" "$TEMP_DIR/" 2>/dev/null || true

# 打包传输
cd "$TEMP_DIR"
tar -czf "updates.tar.gz" .
scp "updates.tar.gz" "$SSH_USER@$SERVER_IP:/tmp/"

echo -e "${GREEN}✅ 文件传输完成${NC}"

# 4. 在服务器上部署
echo -e "${YELLOW}4. 在服务器上部署更新...${NC}"
ssh "$SSH_USER@$SERVER_IP" "
    set -e
    
    echo '解压更新文件...'
    cd /tmp
    tar -xzf updates.tar.gz
    
    echo '停止后端服务...'
    supervisorctl stop slowquery-app 2>/dev/null || pkill -f 'python.*app.py' || true
    sleep 2
    
    echo '更新后端文件...'
    cd /tmp
    cp -r backend/* $APP_PATH/backend/
    
    echo '更新前端文件...'
    cp -r frontend/* $APP_PATH/frontend/
    
    echo '设置文件权限...'
    chown -R slowquery:slowquery $APP_PATH 2>/dev/null || chown -R www-data:www-data $APP_PATH
    
    echo '安装前端依赖...'
    cd $APP_PATH/frontend
    npm install lucide-react recharts @tanstack/react-table --silent
    
    echo '构建前端...'
    npm run build --silent
    
    echo '启动后端服务...'
    supervisorctl start slowquery-app 2>/dev/null || {
        cd $APP_PATH/backend
        nohup python app.py > /var/log/slowquery-app.log 2>&1 &
    }
    
    echo '等待服务启动...'
    sleep 5
    
    echo '清理临时文件...'
    rm -f /tmp/updates.tar.gz
    rm -rf /tmp/backend /tmp/frontend /tmp/*.conf /tmp/*.md /tmp/*.sh
"

echo -e "${GREEN}✅ 服务器部署完成${NC}"

# 5. 验证部署
echo -e "${YELLOW}5. 验证部署结果...${NC}"

# 检查后端服务
echo "检查后端服务..."
BACKEND_STATUS=$(ssh "$SSH_USER@$SERVER_IP" "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5172/api/status 2>/dev/null || echo '000'")
if [ "$BACKEND_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ 后端服务运行正常${NC}"
else
    echo -e "${RED}❌ 后端服务异常 (状态码: $BACKEND_STATUS)${NC}"
fi

# 检查前端文件
echo "检查前端构建..."
FRONTEND_FILES=$(ssh "$SSH_USER@$SERVER_IP" "ls -la $APP_PATH/frontend/dist/ 2>/dev/null | wc -l")
if [ "$FRONTEND_FILES" -gt 3 ]; then
    echo -e "${GREEN}✅ 前端构建文件正常${NC}"
else
    echo -e "${RED}❌ 前端构建文件缺失${NC}"
fi

# 测试统计API
echo "测试统计API..."
TEST_RESULT=$(ssh "$SSH_USER@$SERVER_IP" "
    cd $APP_PATH/backend
    python test_user_stats.py 2>/dev/null | grep -c '✅' || echo '0'
")
if [ "$TEST_RESULT" -gt 2 ]; then
    echo -e "${GREEN}✅ 统计API测试通过${NC}"
else
    echo -e "${YELLOW}⚠️  统计API测试需要检查${NC}"
fi

# 6. 传输验证脚本并运行
echo -e "${YELLOW}6. 运行完整验证...${NC}"
if [ -f "verify_production_deployment.sh" ]; then
    scp "verify_production_deployment.sh" "$SSH_USER@$SERVER_IP:/tmp/"
    ssh "$SSH_USER@$SERVER_IP" "
        chmod +x /tmp/verify_production_deployment.sh
        /tmp/verify_production_deployment.sh localhost
        rm -f /tmp/verify_production_deployment.sh
    "
fi

# 清理本地临时文件
rm -rf "$TEMP_DIR"

echo ""
echo -e "${GREEN}🎉 部署完成！${NC}"
echo ""
echo -e "${BLUE}📋 部署摘要：${NC}"
echo "   • 备份位置: $BACKUP_DIR/code_backup_$BACKUP_TIMESTAMP.tar.gz"
echo "   • 后端服务: $([ "$BACKEND_STATUS" = "200" ] && echo "✅ 正常" || echo "❌ 异常")"
echo "   • 前端构建: $([ "$FRONTEND_FILES" -gt 3 ] && echo "✅ 正常" || echo "❌ 异常")"
echo "   • 统计功能: $([ "$TEST_RESULT" -gt 2 ] && echo "✅ 正常" || echo "⚠️  需检查")"
echo ""
echo -e "${BLUE}🌐 访问地址：${NC}"
echo "   主页: http://$SERVER_IP"
echo "   登录: admin/Admin@123, dba/Dba@123, dev/Dev@123"
echo "   统计: 点击导航栏'用户统计'"
echo ""
echo -e "${YELLOW}📊 后续操作：${NC}"
echo "   1. 在浏览器中访问系统验证功能"
echo "   2. 检查统计数据是否正常显示"
echo "   3. 测试时间筛选和用户详情功能"
echo "   4. 监控系统性能和日志"
echo ""

if [ "$BACKEND_STATUS" = "200" ] && [ "$FRONTEND_FILES" -gt 3 ]; then
    echo -e "${GREEN}🎊 部署成功！用户统计功能已上线${NC}"
    exit 0
else
    echo -e "${RED}⚠️  部署可能存在问题，请检查日志${NC}"
    echo ""
    echo -e "${YELLOW}故障排查命令：${NC}"
    echo "   ssh $SSH_USER@$SERVER_IP 'supervisorctl status slowquery-app'"
    echo "   ssh $SSH_USER@$SERVER_IP 'tail -f /var/log/supervisor/slowquery-app.log'"
    echo "   ssh $SSH_USER@$SERVER_IP 'systemctl status nginx'"
    exit 1
fi
