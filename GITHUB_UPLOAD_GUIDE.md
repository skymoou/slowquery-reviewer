# GitHub代码上传指南

## 📋 准备工作

### 1. 安装Git
如果系统还没有安装Git，请先安装：

**Windows:**
- 下载并安装 [Git for Windows](https://git-scm.com/download/win)
- 或使用包管理器：`winget install Git.Git`

**验证安装:**
```bash
git --version
```

### 2. 配置Git用户信息
```bash
git config --global user.name "你的用户名"
git config --global user.email "你的邮箱"
```

## 🚀 上传步骤

### 第一步：创建GitHub仓库
1. 登录 [GitHub](https://github.com)
2. 点击右上角的 "+" 号，选择 "New repository"
3. 填写仓库信息：
   - Repository name: `slowquery-reviewer`
   - Description: `MySQL慢查询分析系统 - 生产环境版本`
   - 选择 Public 或 Private
   - 不要勾选 "Initialize this repository with a README"
4. 点击 "Create repository"

### 第二步：初始化本地仓库
在项目根目录执行：
```bash
cd /path/to/slowquery-reviewer
git init
```

### 第三步：创建.gitignore文件
创建 `.gitignore` 文件来忽略不需要上传的文件：

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# 虚拟环境
venv/
env/
ENV/

# 环境变量文件
.env
.env.local
.env.production

# 日志文件
*.log
logs/

# 数据库文件
*.sql
*.db
*.sqlite

# 备份文件
*_backup_*
*.bak

# 临时文件
*.tmp
*.temp

# IDE文件
.vscode/
.idea/
*.swp
*.swo

# 系统文件
.DS_Store
Thumbs.db

# Node.js (前端)
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# 构建文件
dist/
build/

# 生产环境特定文件
/var/
/opt/
*.pid
*.sock

# 敏感配置文件
mysql.cnf
database.conf
ssl/
certificates/
```

### 第四步：添加文件到Git
```bash
# 添加所有文件
git add .

# 检查要提交的文件
git status
```

### 第五步：创建初始提交
```bash
git commit -m "初始提交: MySQL慢查询分析系统生产版本

特性:
- Python Flask后端API
- Vue.js前端界面
- MySQL慢查询日志解析
- 用户认证和权限管理
- 生产环境部署配置
- Nginx + Gunicorn + Supervisor配置
- 完整的运维管理脚本

技术栈:
- 后端: Python 3.8+, Flask, MySQL
- 前端: Vue.js, Element UI
- 部署: Nginx, Gunicorn, Supervisor
- 数据库: MySQL 8.0+

已移除:
- 所有测试和调试文件
- Docker相关配置
- Windows特定脚本(.bat, .ps1)
- 开发文档和临时文件"
```

### 第六步：添加远程仓库
将 `your-username` 和 `slowquery-reviewer` 替换为实际的GitHub用户名和仓库名：
```bash
git remote add origin https://github.com/your-username/slowquery-reviewer.git
```

### 第七步：推送到GitHub
```bash
# 推送主分支
git push -u origin main

# 如果遇到main分支不存在的错误，可以先创建：
git branch -M main
git push -u origin main
```

## 📁 项目结构说明

上传后的项目结构：
```
slowquery-reviewer/
├── backend/                     # Python后端
│   ├── app.py                  # Flask主应用
│   ├── config.py               # 配置文件
│   ├── requirements.txt        # Python依赖
│   ├── gunicorn.conf.py       # Gunicorn配置
│   ├── auth.py                # 认证模块
│   ├── db.py                  # 数据库模块
│   ├── slow_log_parser_optimized.py  # 优化后的解析器
│   ├── slow_log_parser_clean.py      # 清洁版解析器
│   └── routes/                # API路由
├── frontend/                   # 前端资源
│   ├── dist/                  # 构建后的文件
│   └── src/                   # 源代码
├── deployment/                 # 部署配置
│   ├── configs/               # 配置文件
│   └── scripts/               # 部署脚本
├── nginx-production.conf       # Nginx生产配置
├── PRODUCTION_DEPLOYMENT.md    # 生产部署文档
├── quick_deploy.sh            # 快速部署脚本
├── manage.sh                  # 运维管理脚本
└── README.md                  # 项目说明
```

## 🔧 创建README.md

为项目创建一个清晰的README.md：

```markdown
# MySQL慢查询分析系统

一个用于分析MySQL慢查询日志的Web应用系统，帮助数据库管理员快速定位和优化性能问题。

## ✨ 特性

- 🚀 **高性能解析**: 优化的MySQL慢查询日志解析器
- 📊 **可视化分析**: 直观的图表和统计数据
- 👥 **用户管理**: 完整的用户认证和权限系统
- 🔍 **智能过滤**: 支持时间范围、用户黑名单等过滤功能
- 📈 **性能监控**: 实时监控和历史趋势分析
- 🛠️ **运维友好**: 完整的部署和管理脚本

## 🏗️ 技术架构

- **后端**: Python 3.8+ + Flask + MySQL
- **前端**: Vue.js + Element UI
- **部署**: Nginx + Gunicorn + Supervisor
- **数据库**: MySQL 8.0+

## 📦 快速部署

### 自动化部署
```bash
# 下载并运行快速部署脚本
wget https://raw.githubusercontent.com/your-username/slowquery-reviewer/main/quick_deploy.sh
sudo bash quick_deploy.sh
```

### 手动部署
详细部署说明请参考 [生产环境部署文档](PRODUCTION_DEPLOYMENT.md)

## 🚀 使用方法

1. 访问系统: `http://your-server-ip`
2. 默认管理员账号: `admin/admin`
3. 上传慢查询日志文件进行分析
4. 查看分析结果和优化建议

## 📖 文档

- [生产环境部署指南](PRODUCTION_DEPLOYMENT.md)
- [API接口文档](backend/routes/)
- [运维管理手册](manage.sh)

## 🛠️ 运维管理

```bash
# 查看系统状态
./manage.sh status

# 启动/停止/重启服务
./manage.sh start|stop|restart

# 备份数据库
./manage.sh backup

# 健康检查
./manage.sh health
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 支持

如有问题请提交Issue或联系开发团队。
```

## 🔄 后续维护

### 更新代码
```bash
# 拉取最新代码
git pull origin main

# 添加新的更改
git add .
git commit -m "描述你的更改"
git push origin main
```

### 创建分支
```bash
# 创建功能分支
git checkout -b feature/new-feature

# 完成开发后合并
git checkout main
git merge feature/new-feature
git push origin main
```

### 标签管理
```bash
# 创建版本标签
git tag -a v1.0.0 -m "版本 1.0.0 - 生产环境初始版本"
git push origin v1.0.0
```

## 🚨 注意事项

1. **敏感信息**: 确保 `.env` 文件已在 `.gitignore` 中
2. **大文件**: 避免上传日志文件、数据库文件等
3. **权限设置**: 确保仓库访问权限设置正确
4. **分支策略**: 建议使用 main 分支作为生产版本
5. **定期备份**: 重要更改前先备份代码

---

按照以上步骤，你就可以成功将慢查询分析系统上传到GitHub仓库了！
