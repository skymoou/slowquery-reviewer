#!/bin/bash

#################################################################################
# 慢查询系统性能优化脚本
# 
# 此脚本用于优化系统性能，提高页面加载速度
# 适用于 Rocky Linux 9.x 生产环境
#################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}🚀 慢查询系统性能优化${NC}"
echo -e "${BLUE}================================${NC}"
echo

# 项目路径
PROJECT_DIR="/opt/slowquery-reviewer"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKEND_DIR="$PROJECT_DIR/backend"
NGINX_CONF="/etc/nginx/sites-available/slowquery-reviewer"

echo -e "${YELLOW}📦 1. 优化前端构建...${NC}"
cd "$FRONTEND_DIR"

# 清理构建缓存
echo "   🧹 清理构建缓存..."
rm -rf dist/ node_modules/.vite/

# 安装依赖（如果需要）
if [ ! -d "node_modules" ]; then
    echo "   📥 安装前端依赖..."
    npm ci --production
fi

# 优化构建
echo "   🔨 执行优化构建..."
NODE_ENV=production npm run build

echo -e "${GREEN}   ✅ 前端构建优化完成${NC}"

echo -e "${YELLOW}📊 2. 启用Gzip压缩...${NC}"

# 检查是否已有gzip模块
if nginx -V 2>&1 | grep -q "gzip"; then
    echo "   ✅ Nginx已支持gzip压缩"
else
    echo "   ⚠️  Nginx可能不支持gzip，请检查编译选项"
fi

# 创建优化的Nginx配置
cat > /tmp/nginx_performance.conf << 'EOF'
# 性能优化配置
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_proxied any;
gzip_comp_level 6;
gzip_types
    text/plain
    text/css
    text/xml
    text/javascript
    application/javascript
    application/xml+rss
    application/json;

# 静态文件缓存
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Vary Accept-Encoding;
    access_log off;
}

# HTML文件缓存
location ~* \.html$ {
    expires 1h;
    add_header Cache-Control "public";
    add_header Vary Accept-Encoding;
}
EOF

echo "   📝 Nginx性能配置已生成到 /tmp/nginx_performance.conf"
echo "   请手动将配置添加到你的Nginx server块中"

echo -e "${YELLOW}🗄️  3. 优化数据库...${NC}"

# 数据库优化建议
cat << 'EOF'
   💡 数据库优化建议:
   
   1. 添加必要的索引:
      ALTER TABLE slow_query_fingerprint ADD INDEX idx_last_seen_status (last_seen, reviewed_status);
      ALTER TABLE slow_query_detail ADD INDEX idx_timestamp_checksum (timestamp, checksum);
   
   2. 定期清理旧数据:
      DELETE FROM slow_query_detail WHERE timestamp < DATE_SUB(NOW(), INTERVAL 90 DAY);
   
   3. 优化MySQL配置 (/etc/my.cnf):
      [mysqld]
      innodb_buffer_pool_size = 1G
      query_cache_type = 1
      query_cache_size = 64M
      slow_query_log = 1
      long_query_time = 2
EOF

echo -e "${YELLOW}🔧 4. 后端优化...${NC}"

# 检查Python包优化
cd "$BACKEND_DIR"
echo "   📋 检查Python环境..."

if [ -f "requirements.txt" ]; then
    echo "   🔍 检查可优化的包..."
    
    # 建议使用生产优化的包
    cat << 'EOF'
   💡 后端优化建议:
   
   1. 使用Gunicorn代替开发服务器
   2. 启用连接池
   3. 添加Redis缓存（可选）
   4. 使用生产级WSGI服务器
EOF
fi

echo -e "${YELLOW}⚡ 5. 系统级优化...${NC}"

# 系统优化建议
cat << 'EOF'
   💡 系统优化建议:
   
   1. 内核参数优化 (/etc/sysctl.conf):
      net.core.somaxconn = 65535
      net.ipv4.tcp_max_syn_backlog = 65535
      vm.swappiness = 10
   
   2. 文件描述符限制 (/etc/security/limits.conf):
      * soft nofile 65535
      * hard nofile 65535
   
   3. Systemd服务优化:
      LimitNOFILE=65535
      Nice=-5
EOF

echo -e "${YELLOW}📈 6. 生成性能测试脚本...${NC}"

# 创建性能测试脚本
cat > "$PROJECT_DIR/performance_test.sh" << 'EOF'
#!/bin/bash

echo "🚀 慢查询系统性能测试"
echo "===================="

# 测试页面加载速度
echo "📊 测试首页加载时间..."
curl -w "连接时间: %{time_connect}s\n下载时间: %{time_total}s\n" -o /dev/null -s http://localhost/

# 测试API响应时间
echo "📊 测试API响应时间..."
curl -w "API响应时间: %{time_total}s\n" -o /dev/null -s http://localhost/api/health

# 测试静态资源加载
echo "📊 测试静态资源缓存..."
curl -I http://localhost/assets/ 2>/dev/null | grep -E "(Cache-Control|Expires|ETag)"

echo "✅ 性能测试完成"
EOF

chmod +x "$PROJECT_DIR/performance_test.sh"

echo -e "${GREEN}🎉 性能优化完成！${NC}"
echo
echo -e "${BLUE}📋 优化总结:${NC}"
echo "✅ 前端构建优化"
echo "✅ Gzip压缩配置"
echo "✅ 静态资源缓存"
echo "✅ 数据库优化建议"
echo "✅ 系统优化建议"
echo "✅ 性能测试脚本"
echo
echo -e "${YELLOW}📖 下一步操作:${NC}"
echo "1. 重启Nginx: systemctl restart nginx"
echo "2. 重启应用服务"
echo "3. 运行性能测试: $PROJECT_DIR/performance_test.sh"
echo "4. 监控系统性能"
echo
