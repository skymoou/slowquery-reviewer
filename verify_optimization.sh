#!/bin/bash

# 验证优化效果脚本
# Usage: ./verify_optimization.sh [your-domain-or-ip]

DOMAIN=${1:-localhost}
PORT=${2:-80}
URL="http://$DOMAIN:$PORT"

echo "=== 慢查询审查系统优化验证 ==="
echo "检查目标: $URL"
echo ""

# 1. 检查HTTP访问是否正常
echo "1. 检查 HTTP 访问..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ HTTP 访问正常 (状态码: $HTTP_STATUS)"
else
    echo "❌ HTTP 访问异常 (状态码: $HTTP_STATUS)"
fi

# 2. 检查是否强制跳转HTTPS
echo ""
echo "2. 检查 HTTPS 重定向..."
REDIRECT_STATUS=$(curl -s -o /dev/null -w "%{redirect_url}" "$URL")
if [ -z "$REDIRECT_STATUS" ] || [[ "$REDIRECT_STATUS" != *"https"* ]]; then
    echo "✅ 没有强制 HTTPS 重定向"
else
    echo "❌ 仍然重定向到 HTTPS: $REDIRECT_STATUS"
fi

# 3. 检查Gzip压缩
echo ""
echo "3. 检查 Gzip 压缩..."
GZIP_RESPONSE=$(curl -s -H "Accept-Encoding: gzip" -I "$URL" | grep -i "content-encoding: gzip")
if [ ! -z "$GZIP_RESPONSE" ]; then
    echo "✅ Gzip 压缩已启用"
else
    echo "⚠️  Gzip 压缩未检测到"
fi

# 4. 检查API端点
echo ""
echo "4. 检查 API 端点..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL/api/status" || echo "000")
if [ "$API_STATUS" = "200" ]; then
    echo "✅ API 端点正常 (状态码: $API_STATUS)"
else
    echo "❌ API 端点异常 (状态码: $API_STATUS)"
fi

# 5. 检查静态文件缓存
echo ""
echo "5. 检查静态文件缓存..."
CACHE_HEADER=$(curl -s -I "$URL/assets/" 2>/dev/null | grep -i "cache-control" | head -1)
if [ ! -z "$CACHE_HEADER" ]; then
    echo "✅ 静态文件缓存配置: $CACHE_HEADER"
else
    echo "⚠️  静态文件缓存头未检测到"
fi

# 6. 页面加载时间测试
echo ""
echo "6. 页面加载时间测试..."
LOAD_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$URL")
if (( $(echo "$LOAD_TIME < 3.0" | bc -l) )); then
    echo "✅ 页面加载时间: ${LOAD_TIME}秒 (< 3秒)"
else
    echo "⚠️  页面加载时间: ${LOAD_TIME}秒 (> 3秒)"
fi

# 7. 检查前端构建文件
echo ""
echo "7. 检查前端构建优化..."
if [ -d "/opt/slowquery-reviewer/frontend/dist" ]; then
    DIST_SIZE=$(du -sh /opt/slowquery-reviewer/frontend/dist 2>/dev/null | cut -f1)
    JS_COUNT=$(find /opt/slowquery-reviewer/frontend/dist -name "*.js" | wc -l)
    echo "✅ 构建目录大小: $DIST_SIZE"
    echo "✅ JS 文件数量: $JS_COUNT (代码分割)"
else
    echo "⚠️  构建目录不存在，请运行 npm run build"
fi

# 8. 进程状态检查
echo ""
echo "8. 检查服务进程..."
if command -v supervisorctl >/dev/null 2>&1; then
    SUPERVISOR_STATUS=$(supervisorctl status slowquery-app 2>/dev/null | grep RUNNING)
    if [ ! -z "$SUPERVISOR_STATUS" ]; then
        echo "✅ Supervisor 进程运行正常"
    else
        echo "❌ Supervisor 进程状态异常"
    fi
else
    echo "⚠️  Supervisor 未安装或不在PATH中"
fi

echo ""
echo "=== 验证完成 ==="
echo ""
echo "💡 优化建议："
echo "   - 如果有 ❌ 标记，请检查相应配置"
echo "   - 如果有 ⚠️ 标记，建议进一步优化"
echo "   - 定期运行此脚本监控性能"
echo ""
echo "📚 详细信息请参考: DEPLOYMENT_OPTIMIZATION.md"
