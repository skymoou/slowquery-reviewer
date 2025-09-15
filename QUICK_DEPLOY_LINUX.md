# 🚀 Linux服务器一键部署

## 快速部署命令

### 1. 下载部署脚本到服务器
```bash
# 方法1: 直接从GitHub下载
wget https://raw.githubusercontent.com/skymoou/slowquery-reviewer/main/deploy_linux.sh
chmod +x deploy_linux.sh

# 方法2: 如果项目已存在，从项目目录复制
cp /path/to/slowquery-reviewer/deploy_linux.sh ./
chmod +x deploy_linux.sh
```

### 2. 配置部署参数
编辑脚本中的配置参数：
```bash
nano deploy_linux.sh

# 修改以下参数：
PROJECT_PATH="/opt/slowquery-reviewer"  # 你的项目部署路径
SERVICE_NAME="slowquery-reviewer"       # Supervisor服务名称
```

### 3. 执行部署
```bash
# 执行增量部署
sudo ./deploy_linux.sh
```

## 📋 部署前置条件

确保你的Linux服务器已安装并配置：

### 系统要求
- Ubuntu 18.04+ / CentOS 7+ / Debian 10+
- Python 3.8+
- Node.js 16+
- MySQL 5.7+

### 必需服务
- Nginx
- Supervisor
- Git

### 快速安装命令
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv nginx supervisor mysql-server curl

# 安装Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# CentOS/RHEL
sudo yum install -y git python3 python3-pip nginx supervisor mysql-server curl
sudo yum install -y nodejs npm
```

## 🔧 首次部署流程

如果是首次部署，需要先完成初始化：

### 1. 克隆项目
```bash
cd /opt
sudo git clone https://github.com/skymoou/slowquery-reviewer.git
sudo chown -R www-data:www-data slowquery-reviewer
```

### 2. 配置后端
```bash
cd /opt/slowquery-reviewer/backend
sudo -u www-data python3 -m venv venv
sudo -u www-data ./venv/bin/pip install -r requirements.txt

# 配置数据库连接
sudo cp config.py.example config.py
sudo nano config.py  # 编辑数据库配置
```

### 3. 构建前端
```bash
cd /opt/slowquery-reviewer/frontend
sudo -u www-data npm install
sudo -u www-data npm run build
```

### 4. 配置Nginx
```bash
sudo nano /etc/nginx/sites-available/slowquery-reviewer
```

配置内容：
```nginx
server {
    listen 80;
    server_name _;

    location / {
        root /opt/slowquery-reviewer/frontend/dist;
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5172;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/slowquery-reviewer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. 配置Supervisor
```bash
sudo nano /etc/supervisor/conf.d/slowquery-reviewer.conf
```

配置内容：
```ini
[program:slowquery-reviewer]
command=/opt/slowquery-reviewer/backend/venv/bin/python app.py
directory=/opt/slowquery-reviewer/backend
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/slowquery-reviewer.log
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start slowquery-reviewer
```

## 🔄 后续增量部署

完成首次部署后，每次代码更新只需要：

```bash
# 下载并执行部署脚本
wget https://raw.githubusercontent.com/skymoou/slowquery-reviewer/main/deploy_linux.sh
chmod +x deploy_linux.sh
sudo ./deploy_linux.sh
```

## ✅ 验证部署

### 1. 检查服务状态
```bash
# 检查后端服务
sudo supervisorctl status slowquery-reviewer

# 检查Nginx
sudo systemctl status nginx

# 检查端口监听
netstat -tlnp | grep :5172  # 后端端口
netstat -tlnp | grep :80    # 前端端口
```

### 2. 测试功能
```bash
# 测试API接口
curl http://localhost:5172/api/health

# 测试前端页面
curl http://localhost/

# 测试新的排序功能
# 访问前端页面，使用过滤功能验证排序效果
```

## 🚨 故障排除

### 常见问题解决
```bash
# 查看应用日志
sudo tail -f /var/log/slowquery-reviewer.log

# 查看Nginx错误日志
sudo tail -f /var/log/nginx/error.log

# 重启服务
sudo supervisorctl restart slowquery-reviewer
sudo systemctl restart nginx

# 检查防火墙
sudo ufw status
sudo firewall-cmd --list-all  # CentOS
```

### 权限问题
```bash
# 确保正确的文件权限
sudo chown -R www-data:www-data /opt/slowquery-reviewer
sudo chmod +x /opt/slowquery-reviewer/backend/app.py
```

## 📞 获取支持

如果遇到问题：
1. 查看项目文档：`LINUX_DEPLOYMENT_GUIDE.md`
2. 检查日志文件
3. 确认服务配置
4. 验证网络连接

部署完成后访问：`http://your-server-ip/` 验证新的排序功能！
