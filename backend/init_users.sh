#!/bin/bash

#################################################################################
# 慢查询分析系统 - 用户初始化脚本
# 
# 此脚本用于初始化系统默认用户账户
# 适用于 Rocky Linux 9.x 生产环境
#
# 创建的默认账户：
# - admin / Admin@123  (系统管理员)
# - dba / Dba@123      (数据库管理员)  
# - dev / Dev@123      (开发者)
#
# 使用方法：
# chmod +x init_users.sh
# ./init_users.sh
#################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
BACKEND_DIR="/opt/slowquery-reviewer/backend"
VENV_DIR="/opt/slowquery-reviewer/venv"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}🚀 慢查询分析系统 - 用户初始化${NC}"
echo -e "${BLUE}================================${NC}"
echo

# 检查是否为root用户
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ 此脚本需要root权限运行${NC}"
   echo "请使用: sudo $0"
   exit 1
fi

# 检查项目目录
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}❌ 后端目录不存在: $BACKEND_DIR${NC}"
    echo "请确保慢查询分析系统已正确部署"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ Python虚拟环境不存在: $VENV_DIR${NC}"
    echo "请先运行部署脚本创建虚拟环境"
    exit 1
fi

# 检查配置文件
if [ ! -f "$BACKEND_DIR/config.py" ]; then
    echo -e "${RED}❌ 配置文件不存在: $BACKEND_DIR/config.py${NC}"
    echo "请先配置数据库连接信息"
    exit 1
fi

echo -e "${YELLOW}📋 环境检查完成${NC}"
echo

# 激活虚拟环境并运行初始化脚本
cd "$BACKEND_DIR"

echo -e "${BLUE}🔧 激活Python虚拟环境...${NC}"
source "$VENV_DIR/bin/activate"

echo -e "${BLUE}📦 检查必要的Python包...${NC}"
pip install --quiet bcrypt mysql-connector-python 2>/dev/null || {
    echo -e "${RED}❌ 安装Python依赖失败${NC}"
    exit 1
}

echo -e "${BLUE}👥 开始初始化用户...${NC}"
echo

# 选择初始化脚本
if [ -f "$BACKEND_DIR/quick_init_users.py" ]; then
    echo -e "${GREEN}使用快速初始化脚本...${NC}"
    python quick_init_users.py
elif [ -f "$BACKEND_DIR/init_default_users.py" ]; then
    echo -e "${GREEN}使用完整初始化脚本...${NC}"
    python init_default_users.py
else
    echo -e "${RED}❌ 找不到用户初始化脚本${NC}"
    echo "请确保以下文件之一存在："
    echo "  - quick_init_users.py"
    echo "  - init_default_users.py"
    exit 1
fi

echo
echo -e "${GREEN}✅ 用户初始化完成！${NC}"
echo
echo -e "${YELLOW}📝 默认登录账户信息：${NC}"
echo -e "${YELLOW}================================${NC}"
echo -e "• 系统管理员:"
echo -e "  用户名: ${GREEN}admin${NC}"
echo -e "  密码:   ${GREEN}Admin@123${NC}"
echo
echo -e "• 数据库管理员:"
echo -e "  用户名: ${GREEN}dba${NC}"
echo -e "  密码:   ${GREEN}Dba@123${NC}"
echo
echo -e "• 开发者:"
echo -e "  用户名: ${GREEN}dev${NC}"
echo -e "  密码:   ${GREEN}Dev@123${NC}"
echo -e "${YELLOW}================================${NC}"
echo
echo -e "${RED}🔒 安全提醒：${NC}"
echo -e "${RED}1. 首次登录后请立即修改默认密码${NC}"
echo -e "${RED}2. 建议定期更换密码${NC}"
echo -e "${RED}3. 不要在生产环境长期使用默认密码${NC}"
echo

# 测试数据库连接
echo -e "${BLUE}🔍 测试数据库连接...${NC}"
python -c "
import sys
sys.path.append('.')
try:
    from config import DB_CONFIG
    import mysql.connector
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('SELECT username, role_id FROM users WHERE username IN (\"admin\", \"dba\", \"dev\")')
    users = cursor.fetchall()
    print(f'✅ 数据库连接正常，找到 {len(users)} 个用户')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ 数据库连接测试失败: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}🎉 用户初始化和验证全部完成！${NC}"
    echo -e "${GREEN}现在可以使用上述账户登录慢查询分析系统${NC}"
else
    echo -e "${RED}❌ 数据库连接验证失败${NC}"
    echo "请检查数据库配置和服务状态"
    exit 1
fi

echo
