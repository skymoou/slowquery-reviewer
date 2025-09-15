#!/bin/bash

# 生产环境部署验证脚本
# Usage: ./verify_production_deployment.sh [domain-or-ip]

DOMAIN=${1:-localhost}
BASE_URL="http://$DOMAIN"

echo "=== 慢查询审查系统部署验证 ==="
echo "检查目标: $BASE_URL"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查主页访问
echo "1. 检查主页访问..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL" 2>/dev/null || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ 主页访问正常 (状态码: $HTTP_STATUS)${NC}"
else
    echo -e "${RED}❌ 主页访问异常 (状态码: $HTTP_STATUS)${NC}"
fi

# 2. 检查静态资源
echo ""
echo "2. 检查静态资源加载..."
JS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/assets/" 2>/dev/null || echo "000")
if [ "$JS_STATUS" = "200" ] || [ "$JS_STATUS" = "403" ]; then
    echo -e "${GREEN}✅ 静态资源目录可访问${NC}"
else
    echo -e "${YELLOW}⚠️  静态资源目录状态: $JS_STATUS${NC}"
fi

# 3. 检查API代理
echo ""
echo "3. 检查API代理..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/status" 2>/dev/null || echo "000")
if [ "$API_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ API代理正常 (状态码: $API_STATUS)${NC}"
else
    echo -e "${RED}❌ API代理异常 (状态码: $API_STATUS)${NC}"
fi

# 4. 检查健康检查端点
echo ""
echo "4. 检查健康检查端点..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")
if [ "$HEALTH_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ 健康检查正常 (状态码: $HEALTH_STATUS)${NC}"
else
    echo -e "${YELLOW}⚠️  健康检查状态: $HEALTH_STATUS${NC}"
fi

# 5. 检查Gzip压缩
echo ""
echo "5. 检查Gzip压缩..."
GZIP_RESPONSE=$(curl -s -H "Accept-Encoding: gzip" -I "$BASE_URL" 2>/dev/null | grep -i "content-encoding: gzip")
if [ ! -z "$GZIP_RESPONSE" ]; then
    echo -e "${GREEN}✅ Gzip压缩已启用${NC}"
else
    echo -e "${YELLOW}⚠️  Gzip压缩未检测到${NC}"
fi

# 6. 检查安全头
echo ""
echo "6. 检查安全头配置..."
SECURITY_HEADERS=$(curl -s -I "$BASE_URL" 2>/dev/null | grep -i -E "(x-frame-options|x-content-type-options|x-xss-protection)")
if [ ! -z "$SECURITY_HEADERS" ]; then
    echo -e "${GREEN}✅ 安全头已配置${NC}"
    echo "$SECURITY_HEADERS" | sed 's/^/   /'
else
    echo -e "${YELLOW}⚠️  安全头未检测到${NC}"
fi

# 7. 检查缓存头
echo ""
echo "7. 检查静态文件缓存..."
CACHE_HEADER=$(curl -s -I "$BASE_URL/assets/index.css" 2>/dev/null | grep -i "cache-control" | head -1)
if [ ! -z "$CACHE_HEADER" ]; then
    echo -e "${GREEN}✅ 静态文件缓存配置: $CACHE_HEADER${NC}"
else
    echo -e "${YELLOW}⚠️  静态文件缓存头未检测到${NC}"
fi

# 8. 测试页面加载时间
echo ""
echo "8. 页面加载性能测试..."
LOAD_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL" 2>/dev/null)
if (( $(echo "$LOAD_TIME < 2.0" | bc -l 2>/dev/null || echo "0") )); then
    echo -e "${GREEN}✅ 页面加载时间: ${LOAD_TIME}秒 (< 2秒)${NC}"
elif (( $(echo "$LOAD_TIME < 5.0" | bc -l 2>/dev/null || echo "0") )); then
    echo -e "${YELLOW}⚠️  页面加载时间: ${LOAD_TIME}秒 (可优化)${NC}"
else
    echo -e "${RED}❌ 页面加载时间: ${LOAD_TIME}秒 (较慢)${NC}"
fi

# 9. 检查端口访问（应该被阻止）
echo ""
echo "9. 检查后端端口安全性..."
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN:5172/api/status" 2>/dev/null || echo "000")
if [ "$BACKEND_STATUS" = "000" ] || [ "$BACKEND_STATUS" = "7" ]; then
    echo -e "${GREEN}✅ 后端端口5172已正确屏蔽外网访问${NC}"
else
    echo -e "${RED}❌ 警告: 后端端口5172可以从外网访问 (状态码: $BACKEND_STATUS)${NC}"
fi

# 10. 验证登录功能
echo ""
echo "10. 测试登录API..."
LOGIN_TEST=$(curl -s -X POST "$BASE_URL/api/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"Admin@123"}' 2>/dev/null)

if echo "$LOGIN_TEST" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ 登录API测试成功${NC}"
    
    # 提取token测试统计API
    TOKEN=$(echo "$LOGIN_TEST" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    if [ ! -z "$TOKEN" ]; then
        STATS_TEST=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/queries/stats/by-user" 2>/dev/null)
        if echo "$STATS_TEST" | grep -q '"success":true'; then
            echo -e "${GREEN}✅ 用户统计API测试成功${NC}"
        else
            echo -e "${YELLOW}⚠️  用户统计API测试失败${NC}"
        fi
    fi
else
    echo -e "${RED}❌ 登录API测试失败${NC}"
fi

echo ""
echo "=== 验证完成 ==="
echo ""
echo -e "${GREEN}🎉 部署建议：${NC}"
echo "   ✓ 用户访问地址: $BASE_URL"
echo "   ✓ 使用账号登录: admin/Admin@123, dba/Dba@123, dev/Dev@123"
echo "   ✓ 点击'用户统计'查看新功能"
echo ""
echo -e "${YELLOW}📊 性能监控：${NC}"
echo "   • 页面加载时间: ${LOAD_TIME}秒"
echo "   • 建议监控API响应时间"
echo "   • 建议配置日志轮转"
echo ""
if [ "$HTTP_STATUS" = "200" ] && [ "$API_STATUS" = "200" ]; then
    echo -e "${GREEN}🎊 部署成功！系统运行正常${NC}"
else
    echo -e "${RED}⚠️  部署存在问题，请检查相关配置${NC}"
fi
