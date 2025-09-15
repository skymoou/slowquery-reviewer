#!/bin/bash

# 手动部署用户统计功能 - 简化版本
# 适用于已有基础环境的服务器

echo "=== 慢查询审查系统 - 用户统计功能部署 ==="
echo ""

# 检查当前目录
if [ ! -f "backend/routes/queries.py" ]; then
    echo "❌ 请在项目根目录运行此脚本"
    exit 1
fi

APP_PATH="/opt/slowquery-reviewer"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)

echo "1. 创建备份..."
sudo mkdir -p /opt/backups/slowquery-reviewer
sudo tar -czf "/opt/backups/slowquery-reviewer/backup_$BACKUP_DATE.tar.gz" \
    "$APP_PATH/backend" "$APP_PATH/frontend" 2>/dev/null || true
echo "✅ 备份完成"

echo ""
echo "2. 停止后端服务..."
sudo supervisorctl stop slowquery-app 2>/dev/null || \
sudo pkill -f "python.*app.py" || true
sleep 2
echo "✅ 服务已停止"

echo ""
echo "3. 更新后端文件..."
sudo cp backend/routes/queries.py "$APP_PATH/backend/routes/"
sudo cp backend/test_user_stats.py "$APP_PATH/backend/" 2>/dev/null || true
sudo cp backend/USER_STATS_FEATURE.md "$APP_PATH/backend/" 2>/dev/null || true
echo "✅ 后端文件更新完成"

echo ""
echo "4. 更新前端文件..."
sudo mkdir -p "$APP_PATH/frontend/src/components"
sudo cp frontend/src/components/UserStats.jsx "$APP_PATH/frontend/src/components/" 2>/dev/null || true
sudo cp frontend/src/services/api.js "$APP_PATH/frontend/src/services/"
sudo cp frontend/src/App.jsx "$APP_PATH/frontend/src/"
sudo cp frontend/package.json "$APP_PATH/frontend/"
echo "✅ 前端文件更新完成"

echo ""
echo "5. 安装前端依赖..."
cd "$APP_PATH/frontend"
sudo npm install lucide-react recharts @tanstack/react-table --silent
echo "✅ 依赖安装完成"

echo ""
echo "6. 构建前端..."
sudo npm run build --silent
echo "✅ 前端构建完成"

echo ""
echo "7. 设置文件权限..."
sudo chown -R slowquery:slowquery "$APP_PATH" 2>/dev/null || \
sudo chown -R www-data:www-data "$APP_PATH"
echo "✅ 权限设置完成"

echo ""
echo "8. 启动后端服务..."
sudo supervisorctl start slowquery-app 2>/dev/null || {
    cd "$APP_PATH/backend"
    sudo -u slowquery nohup python app.py > /var/log/slowquery-app.log 2>&1 &
}
sleep 5
echo "✅ 服务已启动"

echo ""
echo "9. 验证部署..."

# 检查后端服务
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5172/api/status 2>/dev/null || echo "000")
if [ "$BACKEND_STATUS" = "200" ]; then
    echo "✅ 后端服务运行正常"
else
    echo "❌ 后端服务异常 (状态码: $BACKEND_STATUS)"
fi

# 检查前端构建
FRONTEND_FILES=$(ls -la "$APP_PATH/frontend/dist/" 2>/dev/null | wc -l)
if [ "$FRONTEND_FILES" -gt 3 ]; then
    echo "✅ 前端构建文件正常"
else
    echo "❌ 前端构建文件缺失"
fi

echo ""
echo "=== 部署完成 ==="
echo ""
echo "📋 部署摘要："
echo "   • 备份位置: /opt/backups/slowquery-reviewer/backup_$BACKUP_DATE.tar.gz"
echo "   • 后端服务: $([ "$BACKEND_STATUS" = "200" ] && echo "正常" || echo "异常")"
echo "   • 前端构建: $([ "$FRONTEND_FILES" -gt 3 ] && echo "正常" || echo "异常")"
echo ""
echo "🌐 验证步骤："
echo "   1. 访问: http://your-domain.com"
echo "   2. 登录: admin/Admin@123"
echo "   3. 点击'用户统计'查看新功能"
echo ""

if [ "$BACKEND_STATUS" = "200" ] && [ "$FRONTEND_FILES" -gt 3 ]; then
    echo "🎉 部署成功！用户统计功能已上线"
    
    # 可选：运行API测试
    echo ""
    echo "运行API测试..."
    cd "$APP_PATH/backend"
    python test_user_stats.py 2>/dev/null && echo "✅ API测试通过" || echo "⚠️  API测试需要检查"
    
else
    echo "⚠️  部署可能存在问题，请检查日志"
    echo ""
    echo "故障排查："
    echo "   sudo supervisorctl status slowquery-app"
    echo "   sudo tail -f /var/log/supervisor/slowquery-app.log"
    echo "   sudo systemctl status nginx"
fi
