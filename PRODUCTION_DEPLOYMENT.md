# 慢查询分析系统 - 生产环境部署文档

## 📋 目录
- [系统概述](#系统概述)
- [环境要求](#环境要求)
- [部署准备](#部署准备)
- [数据库配置](#数据库配置)
- [后端部署](#后端部署)
- [前端部署](#前端部署)
- [Nginx配置](#nginx配置)
- [进程管理](#进程管理)
- [安全配置](#安全配置)
- [监控与日志](#监控与日志)
- [运维管理](#运维管理)
- [故障排查](#故障排查)

---

## 系统概述

慢查询分析系统是一个基于Python Flask的Web应用，用于分析和监控MySQL慢查询日志。系统采用前后端分离架构：

- **后端**: Python Flask + Gunicorn
- **前端**: Vue.js单页应用
- **数据库**: MySQL 8.0+
- **Web服务器**: Nginx
- **进程管理**: Supervisor

---

## 环境要求

### 操作系统
- Ubuntu 20.04 LTS / CentOS 7+ / RHEL 8+
- 最低配置：2核CPU, 4GB内存, 50GB磁盘空间
- 推荐配置：4核CPU, 8GB内存, 100GB磁盘空间

### 软件依赖
```bash
# 系统包
- Python 3.8+
- MySQL 8.0+
- Nginx 1.18+
- Supervisor 4.0+
- Node.js 16+ (构建前端使用)

# Python包 (详见requirements.txt)
- Flask==2.3.3
- mysql-connector-python==8.1.0
- gunicorn==21.2.0
- PyJWT==2.8.0
- bcrypt==4.0.1
```

---

## 部署准备

### 1. 创建系统用户
```bash
# 创建专用用户
sudo useradd -r -s /bin/false -m -d /opt/slowquery-reviewer slowquery

# 创建必要目录
sudo mkdir -p /opt/slowquery-reviewer
sudo mkdir -p /var/log/slowquery
sudo mkdir -p /var/run/slowquery

# 设置权限
sudo chown -R slowquery:slowquery /opt/slowquery-reviewer
sudo chown -R slowquery:slowquery /var/log/slowquery
sudo chown -R slowquery:slowquery /var/run/slowquery
```

### 2. 上传代码
```bash
# 将项目代码上传到服务器
sudo cp -r /path/to/slowquery-reviewer/* /opt/slowquery-reviewer/
sudo chown -R slowquery:slowquery /opt/slowquery-reviewer
```

### 3. 安装Python依赖
```bash
# 切换到项目目录
cd /opt/slowquery-reviewer

# 创建虚拟环境
sudo -u slowquery python3 -m venv venv

# 激活虚拟环境并安装依赖
sudo -u slowquery bash -c "source venv/bin/activate && pip install -r backend/requirements.txt"
```

---

## 数据库配置

### 1. 创建数据库和用户
```sql
-- 连接到MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE IF NOT EXISTS slow_query_analysis 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建专用用户
CREATE USER 'slowquery'@'localhost' IDENTIFIED BY 'your_secure_password';
CREATE USER 'slowquery'@'%' IDENTIFIED BY 'your_secure_password';

-- 授予权限
GRANT ALL PRIVILEGES ON slow_query_analysis.* TO 'slowquery'@'localhost';
GRANT ALL PRIVILEGES ON slow_query_analysis.* TO 'slowquery'@'%';
FLUSH PRIVILEGES;
```

### 2. 初始化数据库表
```bash
cd /opt/slowquery-reviewer/backend

# 初始化数据库
sudo -u slowquery bash -c "source ../venv/bin/activate && python init_database.py"

# 创建表结构
sudo -u slowquery bash -c "source ../venv/bin/activate && python init_tables.py"

# 创建管理员用户
sudo -u slowquery bash -c "source ../venv/bin/activate && python init_admin.py"
```

### 3. 数据库优化配置
在 `/etc/mysql/mysql.conf.d/mysqld.cnf` 中添加：
```ini
[mysqld]
# 慢查询日志配置
slow_query_log = 1
slow_query_log_file = /var/log/mysql/mysql-slow.log
long_query_time = 1

# 性能优化
max_connections = 200
innodb_buffer_pool_size = 2G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
```

---

## 后端部署

### 1. 环境配置
创建 `/opt/slowquery-reviewer/backend/.env` 文件：
```bash
# 数据库配置
DB_HOST=localhost
DB_USER=slowquery
DB_PASSWORD=your_secure_password
DB_NAME=slow_query_analysis
DB_POOL_SIZE=15

# JWT配置
JWT_SECRET_KEY=your-super-secret-jwt-key-2024
JWT_ACCESS_TOKEN_EXPIRES=86400

# 应用配置
FLASK_ENV=production
FLASK_DEBUG=false
```

### 2. 权限设置
```bash
# 设置环境文件权限
sudo chmod 600 /opt/slowquery-reviewer/backend/.env
sudo chown slowquery:slowquery /opt/slowquery-reviewer/backend/.env

# 设置日志目录权限
sudo chmod 755 /var/log/slowquery
sudo chown slowquery:slowquery /var/log/slowquery
```

### 3. 测试后端服务
```bash
cd /opt/slowquery-reviewer/backend

# 测试启动
sudo -u slowquery bash -c "source ../venv/bin/activate && python app.py"

# 测试API
curl http://localhost:5172/api/status
```

---

## 前端部署

### 1. 安装Node.js依赖
```bash
cd /opt/slowquery-reviewer/frontend

# 安装依赖 (如果需要重新构建)
sudo -u slowquery npm install

# 构建生产版本
sudo -u slowquery npm run build
```

### 2. 验证构建结果
```bash
# 检查构建目录
ls -la /opt/slowquery-reviewer/frontend/dist/
```

---

## Nginx配置

### 1. 安装Nginx
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx
```

### 2. 配置虚拟主机
创建 `/etc/nginx/sites-available/slowquery-reviewer`：
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为实际域名或IP
    
    # 日志配置
    access_log /var/log/nginx/slowquery_access.log;
    error_log /var/log/nginx/slowquery_error.log;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 文件上传限制
    client_max_body_size 100M;
    
    # 前端静态文件
    location / {
        root /opt/slowquery-reviewer/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # 静态资源缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:5172;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:5172/api/status;
        access_log off;
    }
}
```

### 3. 启用配置
```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/slowquery-reviewer /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 进程管理

### 1. 安装Supervisor
```bash
# Ubuntu/Debian
sudo apt install supervisor

# CentOS/RHEL
sudo yum install supervisor
```

### 2. 配置Supervisor
创建 `/etc/supervisor/conf.d/slowquery.conf`：
```ini
[group:slowquery]
programs=slowquery-backend

[program:slowquery-backend]
command=/opt/slowquery-reviewer/venv/bin/gunicorn -c gunicorn.conf.py app:app
directory=/opt/slowquery-reviewer/backend
user=slowquery
group=slowquery
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/slowquery/backend.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
environment=PYTHONPATH="/opt/slowquery-reviewer/backend"
```

### 3. 启动服务
```bash
# 重新加载配置
sudo supervisorctl reread
sudo supervisorctl update

# 启动服务
sudo supervisorctl start slowquery-backend

# 查看状态
sudo supervisorctl status
```

---

## 安全配置

### 1. 防火墙配置
```bash
# Ubuntu (UFW)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

### 2. SSL证书配置 (可选)
```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. 数据库安全
```bash
# 运行MySQL安全脚本
sudo mysql_secure_installation

# 配置SSL连接 (可选)
# 在.env中添加SSL配置
```

---

## 监控与日志

### 1. 日志文件位置
```bash
# 应用日志
/var/log/slowquery/backend.log

# Nginx日志
/var/log/nginx/slowquery_access.log
/var/log/nginx/slowquery_error.log

# Gunicorn日志
/var/log/gunicorn-access.log
/var/log/gunicorn-error.log
```

### 2. 日志轮转配置
创建 `/etc/logrotate.d/slowquery`：
```bash
/var/log/slowquery/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 slowquery slowquery
    postrotate
        supervisorctl restart slowquery-backend
    endscript
}
```

### 3. 监控脚本
```bash
#!/bin/bash
# /opt/slowquery-reviewer/scripts/health_check.sh

# 检查服务状态
if ! curl -s http://localhost:5172/api/status > /dev/null; then
    echo "Backend service is down, restarting..."
    supervisorctl restart slowquery-backend
fi

# 检查磁盘空间
DISK_USAGE=$(df /opt/slowquery-reviewer | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "Warning: Disk usage is ${DISK_USAGE}%"
fi
```

---

## 运维管理

### 1. 常用命令
```bash
# 查看服务状态
sudo supervisorctl status

# 重启后端服务
sudo supervisorctl restart slowquery-backend

# 查看日志
sudo tail -f /var/log/slowquery/backend.log

# 重启Nginx
sudo systemctl restart nginx

# 数据库连接测试
mysql -h localhost -u slowquery -p slow_query_analysis
```

### 2. 备份脚本
```bash
#!/bin/bash
# /opt/slowquery-reviewer/scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/slowquery"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
mysqldump -u slowquery -p slow_query_analysis > $BACKUP_DIR/database_$DATE.sql

# 备份配置文件
cp /opt/slowquery-reviewer/backend/.env $BACKUP_DIR/env_$DATE

# 保留最近30天的备份
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
```

### 3. 更新部署
```bash
#!/bin/bash
# /opt/slowquery-reviewer/scripts/deploy.sh

cd /opt/slowquery-reviewer

# 备份当前版本
sudo -u slowquery cp -r backend backend_backup_$(date +%Y%m%d)

# 更新代码
# (手动上传新版本)

# 安装新依赖
sudo -u slowquery bash -c "source venv/bin/activate && pip install -r backend/requirements.txt"

# 重启服务
sudo supervisorctl restart slowquery-backend

# 重载Nginx
sudo nginx -s reload
```

---

## 故障排查

### 1. 常见问题

#### 后端服务无法启动
```bash
# 检查日志
sudo tail -f /var/log/slowquery/backend.log

# 检查端口占用
sudo netstat -tlnp | grep 5172

# 手动启动测试
cd /opt/slowquery-reviewer/backend
sudo -u slowquery bash -c "source ../venv/bin/activate && python app.py"
```

#### 数据库连接失败
```bash
# 测试数据库连接
mysql -h localhost -u slowquery -p slow_query_analysis

# 检查数据库服务
sudo systemctl status mysql

# 查看数据库错误日志
sudo tail -f /var/log/mysql/error.log
```

#### Nginx代理错误
```bash
# 检查Nginx配置
sudo nginx -t

# 查看Nginx错误日志
sudo tail -f /var/log/nginx/slowquery_error.log

# 检查upstream状态
curl -I http://localhost:5172/api/status
```

### 2. 性能优化

#### 数据库优化
```sql
-- 查看慢查询
SHOW VARIABLES LIKE 'slow_query_log';
SHOW VARIABLES LIKE 'long_query_time';

-- 分析表结构
SHOW CREATE TABLE slow_query_fingerprint;
SHOW INDEX FROM slow_query_fingerprint;
```

#### 应用优化
```bash
# 监控内存使用
ps aux | grep gunicorn

# 监控数据库连接
sudo netstat -an | grep 3306 | wc -l
```

---

## 附录

### A. 端口列表
- 80: Nginx HTTP
- 443: Nginx HTTPS (可选)
- 5172: 后端API服务
- 3306: MySQL数据库

### B. 关键文件路径
```
/opt/slowquery-reviewer/          # 项目根目录
├── backend/                      # 后端代码
│   ├── .env                      # 环境配置
│   ├── app.py                    # 主应用
│   ├── gunicorn.conf.py         # Gunicorn配置
│   └── requirements.txt         # Python依赖
├── frontend/dist/               # 前端构建文件
└── venv/                        # Python虚拟环境

/etc/nginx/sites-available/slowquery-reviewer  # Nginx配置
/etc/supervisor/conf.d/slowquery.conf          # Supervisor配置
/var/log/slowquery/                             # 应用日志
```

### C. 联系信息
- 技术支持：[技术团队邮箱]
- 紧急联系：[紧急联系方式]
- 文档版本：v1.0
- 更新日期：2025年9月15日

---

**部署完成后，请访问 http://your-domain.com 验证系统正常运行！**
