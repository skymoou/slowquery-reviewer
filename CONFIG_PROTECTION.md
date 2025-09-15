# ⚠️ 配置文件保护机制说明

## 🔒 自动保护的配置文件

更新脚本会自动保护以下重要配置文件，确保不被覆盖：

### 后端配置文件
- `backend/config.py` - 数据库连接、API配置等
- `backend/.env` - 环境变量配置文件

### 前端配置文件  
- `frontend/.env` - 前端环境变量
- `frontend/.env.local` - 本地环境配置

## 🛡️ 保护机制工作流程

### 1. 备份阶段
```bash
# 创建临时备份目录
/tmp/slowquery_config_backup_20250915_143022/

# 备份重要配置文件
cp backend/config.py → 备份目录
cp backend/.env → 备份目录
```

### 2. 更新阶段
```bash
# 使用 Git Stash 暂存本地配置
git stash push -m "自动备份本地配置"

# 拉取远程代码更新
git pull origin main
```

### 3. 恢复阶段
```bash
# 从备份恢复配置文件
cp 备份目录/config.py → backend/config.py
cp 备份目录/.env → backend/.env
```

## 📋 保护的配置项示例

### backend/config.py
```python
# 数据库连接配置
MYSQL_CONFIG = {
    'host': 'your-db-host',      # 受保护
    'port': 3306,                # 受保护
    'user': 'your-username',     # 受保护
    'password': 'your-password', # 受保护
    'database': 'your-database'  # 受保护
}

# API配置
API_CONFIG = {
    'SECRET_KEY': 'your-secret-key',  # 受保护
    'DEBUG': False,                   # 受保护
    'PORT': 5172                      # 受保护
}
```

### backend/.env
```bash
# 环境变量
DB_HOST=your-db-host        # 受保护
DB_PASSWORD=your-password   # 受保护
SECRET_KEY=your-secret      # 受保护
```

## 🚨 手动保护措施

### 推荐做法
1. **定期备份配置**
   ```bash
   # 手动备份重要配置
   cp backend/config.py ~/backup/config_$(date +%Y%m%d).py
   ```

2. **使用环境变量**
   ```python
   # 在 config.py 中使用环境变量
   import os
   
   MYSQL_CONFIG = {
       'host': os.getenv('DB_HOST', 'localhost'),
       'password': os.getenv('DB_PASSWORD', ''),
   }
   ```

3. **Git 忽略配置文件**
   ```bash
   # 在 .gitignore 中添加
   backend/config.py
   backend/.env
   frontend/.env.local
   ```

## 🔧 自定义保护配置

如果你有其他需要保护的配置文件，可以编辑更新脚本：

```bash
# 编辑 update_server.sh
nano update_server.sh

# 在备份部分添加你的配置文件
if [ -f "your/custom/config.conf" ]; then
    cp "your/custom/config.conf" "$CONFIG_BACKUP_DIR/"
    log_success "已备份 your/custom/config.conf"
fi

# 在恢复部分添加对应恢复逻辑
if [ -f "$CONFIG_BACKUP_DIR/config.conf" ]; then
    cp "$CONFIG_BACKUP_DIR/config.conf" "your/custom/config.conf"
    log_success "已恢复 your/custom/config.conf"
fi
```

## ✅ 验证保护效果

更新完成后，检查配置是否被保护：

```bash
# 检查数据库配置是否保持原样
grep -A 10 "MYSQL_CONFIG" backend/config.py

# 检查环境变量是否保持原样  
cat backend/.env

# 查看备份目录
ls -la /tmp/slowquery_config_backup_*
```

## 🆘 紧急恢复

如果配置意外丢失，可以从备份恢复：

```bash
# 查找最新的备份目录
ls -la /tmp/slowquery_config_backup_*

# 恢复配置文件
LATEST_BACKUP=$(ls -t /tmp/slowquery_config_backup_* | head -1)
cp "$LATEST_BACKUP/config.py" backend/config.py
cp "$LATEST_BACKUP/.env" backend/.env

# 重启服务
sudo supervisorctl restart slowquery-reviewer
```

## 📝 最佳实践

1. **首次使用前**：检查脚本中的保护配置列表
2. **定期备份**：除自动备份外，定期手动备份重要配置
3. **版本控制**：将配置文件模板（去敏感信息）加入版本控制
4. **监控验证**：每次更新后验证配置是否正确
5. **文档记录**：记录自定义配置文件的位置和作用

---

**总结：脚本已经内置了配置文件保护机制，你的数据库连接、密钥等重要配置不会被覆盖！**
