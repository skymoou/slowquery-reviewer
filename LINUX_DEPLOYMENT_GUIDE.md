# Linux服务器部署指南

## 🚀 快速部署流程

### 步骤1: 服务器准备
```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装必要的系统依赖
sudo apt install -y git python3 python3-pip python3-venv nginx supervisor mysql-server curl
```

### 步骤2: 获取最新代码
```bash
# 如果是首次部署
git clone https://github.com/skymoou/slowquery-reviewer.git
cd slowquery-reviewer

# 如果是更新部署
cd /path/to/slowquery-reviewer
git pull origin main
```

### 步骤3: 后端部署
```bash
# 进入后端目录
cd backend

# 创建Python虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置数据库连接
cp config.py.example config.py
# 编辑config.py设置数据库连接信息
nano config.py
```

### 步骤4: 前端构建
```bash
# 进入前端目录
cd ../frontend

# 安装Node.js (如果未安装)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装依赖并构建
npm install
npm run build
```

### 步骤5: Nginx配置
```bash
# 创建Nginx配置文件
sudo nano /etc/nginx/sites-available/slowquery-reviewer
```

配置内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或IP

    # 前端静态文件
    location / {
        root /path/to/slowquery-reviewer/frontend/dist;
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    # API代理到后端
    location /api/ {
        proxy_pass http://127.0.0.1:5172;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/slowquery-reviewer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 步骤6: Supervisor配置 (进程管理)
```bash
# 创建Supervisor配置
sudo nano /etc/supervisor/conf.d/slowquery-reviewer.conf
```

配置内容：
```ini
[program:slowquery-reviewer]
command=/path/to/slowquery-reviewer/backend/venv/bin/python app.py
directory=/path/to/slowquery-reviewer/backend
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/slowquery-reviewer.log
environment=FLASK_ENV=production
```

```bash
# 重新加载Supervisor配置
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start slowquery-reviewer
```

## 🔄 增量更新部署

### 方法1: 使用Git拉取更新
```bash
# 进入项目目录
cd /path/to/slowquery-reviewer

# 停止服务
sudo supervisorctl stop slowquery-reviewer

# 拉取最新代码
git pull origin main

# 重新构建前端（如果有前端变更）
cd frontend
npm run build

# 重启服务
cd ../backend
source venv/bin/activate
sudo supervisorctl start slowquery-reviewer

# 重新加载Nginx
sudo systemctl reload nginx
```

### 方法2: 使用自动化脚本
创建自动化部署脚本：

```bash
# 创建部署脚本
nano deploy_update.sh
```

脚本内容：
```bash
#!/bin/bash

# 设置项目路径
PROJECT_PATH="/path/to/slowquery-reviewer"
SERVICE_NAME="slowquery-reviewer"

echo "🚀 开始增量部署..."

# 进入项目目录
cd $PROJECT_PATH

# 停止服务
echo "⏹️  停止服务..."
sudo supervisorctl stop $SERVICE_NAME

# 备份当前版本
echo "💾 备份当前版本..."
cp -r backend/routes/queries.py backup/queries_$(date +%Y%m%d_%H%M%S).py

# 拉取最新代码
echo "📥 拉取最新代码..."
git pull origin main

# 检查是否有后端变更
if git diff --name-only HEAD~1 HEAD | grep -q "backend/"; then
    echo "🔄 发现后端变更，重新安装依赖..."
    cd backend
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# 检查是否有前端变更
if git diff --name-only HEAD~1 HEAD | grep -q "frontend/"; then
    echo "🏗️  发现前端变更，重新构建..."
    cd frontend
    npm install
    npm run build
    cd ..
fi

# 重启服务
echo "🔄 重启服务..."
sudo supervisorctl start $SERVICE_NAME

# 检查服务状态
echo "✅ 检查服务状态..."
sudo supervisorctl status $SERVICE_NAME

# 重新加载Nginx
sudo systemctl reload nginx

echo "🎉 部署完成！"
echo "📊 访问地址: http://your-domain.com"
```

```bash
# 给脚本执行权限
chmod +x deploy_update.sh

# 执行部署
./deploy_update.sh
```

## ⚡ 快速验证部署

### 检查服务状态
```bash
# 检查后端服务
sudo supervisorctl status slowquery-reviewer
curl http://localhost:5172/api/health

# 检查Nginx
sudo systemctl status nginx
curl http://localhost/

# 查看日志
sudo tail -f /var/log/slowquery-reviewer.log
sudo tail -f /var/log/nginx/access.log
```

### 测试新功能
1. 访问前端页面：`http://your-domain.com`
2. 登录系统
3. 在慢查询列表中输入用户名或数据库名过滤
4. 验证结果是否按执行次数倒序排序

## 🔧 配置要点

### 数据库配置
确保 `backend/config.py` 中的数据库连接信息正确：
```python
# MySQL数据库配置
MYSQL_CONFIG = {
    'host': 'localhost',  # 数据库主机
    'port': 3306,         # 数据库端口
    'user': 'your_user',  # 数据库用户名
    'password': 'your_password',  # 数据库密码
    'database': 'slowquery_db'    # 数据库名称
}
```

### 端口配置
- 后端端口：5172
- 前端端口：80 (通过Nginx代理)
- 确保防火墙允许80端口访问

## 🚨 故障排除

### 常见问题
1. **服务无法启动**：检查Python依赖和数据库连接
2. **前端404错误**：检查Nginx配置和静态文件路径
3. **API无法访问**：检查后端服务状态和端口配置

### 日志查看
```bash
# 应用日志
sudo tail -f /var/log/slowquery-reviewer.log

# Nginx日志
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Supervisor日志
sudo tail -f /var/log/supervisor/supervisord.log
```

## 📝 部署清单
- [ ] 系统依赖安装完成
- [ ] 代码已拉取最新版本
- [ ] 后端虚拟环境配置完成
- [ ] 前端构建完成
- [ ] Nginx配置完成
- [ ] Supervisor配置完成
- [ ] 服务正常运行
- [ ] 新功能验证通过
