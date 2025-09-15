# 🐌 MySQL慢查询分析系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask Version](https://img.shields.io/badge/flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)

一个功能强大的MySQL慢查询日志分析系统，帮助数据库管理员快速定位性能瓶颈，优化数据库查询性能。

## ✨ 核心特性

### 🚀 高性能解析
- **智能解析器**: 经过优化的MySQL慢查询日志解析引擎
- **批量处理**: 支持大文件的高效批量解析
- **内存优化**: 74.8%代码精简，内存使用更少

### 📊 可视化分析
- **统计图表**: 直观的查询时间分布和趋势图
- **性能指标**: 执行时间、扫描行数、返回行数等关键指标
- **SQL指纹**: 自动生成SQL指纹，识别相似查询

### 🔍 智能过滤
- **时间范围**: 支持自定义时间段分析
- **用户黑名单**: 过滤系统用户（如pmm_user, root等）
- **性能阈值**: 按执行时间、扫描行数等条件筛选

### 👥 用户管理
- **JWT认证**: 安全的用户认证机制
- **权限控制**: 多级用户权限管理
- **会话管理**: 自动会话过期和续期

### 🛠️ 运维友好
- **一键部署**: 完整的自动化部署脚本
- **健康监控**: 实时系统状态监控
- **日志管理**: 完善的日志记录和轮转

## 🏗️ 技术架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端 (Vue.js)  │    │  Nginx 反向代理  │    │  MySQL 数据库   │
│                 │    │                 │    │                 │
│ - Element UI    │◄──►│ - 静态文件服务   │    │ - 慢查询存储     │
│ - 图表可视化     │    │ - API代理       │    │ - 用户数据       │
│ - 响应式设计     │    │ - 负载均衡       │    │ - 权限管理       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                        ┌─────────────────┐
                        │ 后端 (Flask)     │
                        │                 │
                        │ - RESTful API   │
                        │ - JWT认证       │
                        │ - 日志解析       │
                        │ - 业务逻辑       │
                        └─────────────────┘
                                │
                        ┌─────────────────┐
                        │ 部署层           │
                        │                 │
                        │ - Gunicorn      │
                        │ - Supervisor    │
                        │ - 进程管理       │
                        └─────────────────┘
```

### 技术栈详情

**后端技术**
- **Python 3.8+**: 主要开发语言
- **Flask 2.3.3**: Web框架
- **PyJWT**: JWT认证
- **mysql-connector-python**: 数据库连接
- **Gunicorn**: WSGI服务器

**前端技术**
- **Vue.js**: 前端框架
- **Element UI**: UI组件库
- **ECharts**: 图表可视化
- **Axios**: HTTP客户端

**部署技术**
- **Nginx**: Web服务器和反向代理
- **Supervisor**: 进程管理
- **MySQL 8.0+**: 数据存储

## 📦 快速开始

### 方式一：自动化部署（推荐）

```bash
# 下载部署脚本
wget https://raw.githubusercontent.com/your-username/slowquery-reviewer/main/quick_deploy.sh

# 运行自动部署
sudo bash quick_deploy.sh
```

### 方式二：手动部署

#### 1. 环境要求
```bash
# 系统要求
- Ubuntu 20.04 LTS / CentOS 7+
- Python 3.8+
- MySQL 8.0+
- Nginx 1.18+
- 4GB+ 内存，50GB+ 磁盘空间
```

#### 2. 克隆代码
```bash
git clone https://github.com/your-username/slowquery-reviewer.git
cd slowquery-reviewer
```

#### 3. 安装依赖
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
pip install -r backend/requirements.txt
```

#### 4. 配置数据库
```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE slow_query_analysis;"

# 初始化表结构
python backend/init_database.py
python backend/init_tables.py
python backend/init_admin.py
```

#### 5. 配置环境变量
```bash
# 复制配置文件
cp backend/.env.example backend/.env

# 编辑配置
vim backend/.env
```

#### 6. 启动服务
```bash
# 启动后端
cd backend
gunicorn -c gunicorn.conf.py app:app

# 配置Nginx（参考nginx-production.conf）
```

## 🚀 使用方法

### 1. 访问系统
```
URL: http://your-server-ip
默认账号: admin
默认密码: admin
```

### 2. 上传慢查询日志
- 点击"上传日志"按钮
- 选择MySQL慢查询日志文件
- 等待解析完成

### 3. 查看分析结果
- **概览页面**: 查看整体统计信息
- **详细列表**: 查看每条慢查询详情
- **图表分析**: 查看性能趋势图表
- **SQL优化**: 获取优化建议

## 📊 功能截图

### 主要界面
```
┌─────────────────────────────────────────────────────────────┐
│ 🏠 慢查询分析系统                    👤 admin ▼  🚪 退出    │
├─────────────────────────────────────────────────────────────┤
│ 📊 概览  📋 查询列表  📈 统计图表  ⚙️ 设置                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📈 总查询数: 1,234    ⏱️ 平均执行时间: 2.5s                │
│  🐌 最慢查询: 45.2s    📊 今日新增: 89条                    │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ 执行时间分布 │  │ 查询频率统计 │  │ 数据库分布   │          │
│  │ [图表区域]  │  │ [图表区域]  │  │ [图表区域]  │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                             │
│  🔍 最新慢查询                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ SELECT * FROM users WHERE ... │ 12.3s │ 2024-09-15 ... ││
│  │ UPDATE orders SET status = ...│  8.7s │ 2024-09-15 ... ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ 运维管理

### 使用管理脚本
```bash
# 查看系统状态
./manage.sh status

# 启动服务
./manage.sh start

# 停止服务
./manage.sh stop

# 重启服务
./manage.sh restart

# 查看实时日志
./manage.sh logs

# 备份数据库
./manage.sh backup

# 恢复数据库
./manage.sh restore

# 健康检查
./manage.sh health

# 清理日志
./manage.sh cleanup

# 用户管理
./manage.sh user
```

### 监控和告警
```bash
# 系统状态检查
curl http://localhost:5172/api/status

# 查看服务进程
ps aux | grep -E "(gunicorn|nginx)"

# 查看资源使用
top -p $(pgrep -f gunicorn | tr '\n' ',' | sed 's/,$//')
```

## 📈 性能优化

### 数据库优化
```sql
-- 慢查询日志配置
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;
SET GLOBAL slow_query_log_file = '/var/log/mysql/mysql-slow.log';

-- 索引优化
CREATE INDEX idx_fingerprint_checksum ON slow_query_fingerprint(checksum);
CREATE INDEX idx_detail_timestamp ON slow_query_detail(timestamp);
```

### 应用优化
```bash
# 调整Gunicorn工作进程数
# gunicorn.conf.py
workers = CPU核心数 × 2 + 1

# 优化数据库连接池
# config.py
DB_POOL_SIZE = 15
```

## 🔧 配置说明

### 环境变量配置
```bash
# 数据库配置
DB_HOST=localhost
DB_USER=slowquery
DB_PASSWORD=your_secure_password
DB_NAME=slow_query_analysis
DB_POOL_SIZE=15

# JWT配置
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ACCESS_TOKEN_EXPIRES=86400

# 应用配置
FLASK_ENV=production
FLASK_DEBUG=false
```

### Nginx配置
```nginx
# 关键配置项
upstream backend {
    server 127.0.0.1:5172;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        root /opt/slowquery-reviewer/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🚨 故障排查

### 常见问题

**1. 后端服务启动失败**
```bash
# 检查日志
tail -f /var/log/slowquery/backend.log

# 检查端口占用
netstat -tlnp | grep 5172

# 手动启动测试
cd backend && python app.py
```

**2. 数据库连接失败**
```bash
# 测试连接
mysql -h localhost -u slowquery -p slow_query_analysis

# 检查权限
SHOW GRANTS FOR 'slowquery'@'localhost';
```

**3. 前端页面无法访问**
```bash
# 检查Nginx状态
systemctl status nginx

# 检查配置语法
nginx -t

# 查看错误日志
tail -f /var/log/nginx/error.log
```

## 📚 API文档

### 认证接口
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin"
}
```

### 慢查询接口
```http
GET /api/slow-queries?page=1&limit=20&start_time=2024-01-01&end_time=2024-12-31
Authorization: Bearer <token>
```

### 统计接口
```http
GET /api/statistics/summary
Authorization: Bearer <token>
```

## 🤝 贡献指南

### 开发环境设置
```bash
# 克隆代码
git clone https://github.com/your-username/slowquery-reviewer.git
cd slowquery-reviewer

# 安装开发依赖
pip install -r backend/requirements-dev.txt

# 启动开发服务器
cd backend && python app.py
```

### 提交规范
```bash
# 提交格式
git commit -m "类型(范围): 描述

详细说明"

# 类型说明
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建过程或辅助工具的变动
```

## 📄 许可证

本项目采用 [MIT许可证](LICENSE)

## 🆘 支持

- **GitHub Issues**: [提交问题](https://github.com/your-username/slowquery-reviewer/issues)
- **文档**: [查看详细文档](PRODUCTION_DEPLOYMENT.md)
- **社区**: [加入讨论](https://github.com/your-username/slowquery-reviewer/discussions)

## 🏆 致谢

感谢所有为这个项目做出贡献的开发者！

---

**⭐ 如果这个项目对你有帮助，请给它一个星标！**
