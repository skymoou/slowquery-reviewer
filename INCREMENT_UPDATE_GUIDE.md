# 🔄 服务器代码增量更新指南

## 使用场景
当你在本地修改代码并推送到GitHub后，需要将变更同步到已运行的Linux服务器上。

## 🚀 一键更新命令

### 方法1: 使用自动化脚本（推荐）
```bash
# 1. 下载更新脚本到服务器
wget https://raw.githubusercontent.com/skymoou/slowquery-reviewer/main/update_server.sh -O update_server.sh
chmod +x update_server.sh

# 2. 编辑配置（首次使用）
nano update_server.sh
# 修改 PROJECT_PATH 为你的实际项目路径
# 修改 SERVICE_NAME 为你的实际服务名称

# 3. 执行更新
sudo ./update_server.sh
```

### 方法2: 手动更新（简单快速）
```bash
# 进入项目目录
cd /path/to/your/slowquery-reviewer

# 停止服务
sudo supervisorctl stop slowquery-reviewer

# 拉取最新代码
git pull origin main

# 重启服务
sudo supervisorctl start slowquery-reviewer

# 检查服务状态
sudo supervisorctl status slowquery-reviewer
```

## 📋 更新流程说明

### 自动化脚本执行的步骤：
1. ✅ 检查当前代码版本
2. ✅ 从GitHub拉取最新代码
3. ✅ 识别变更的文件类型（后端/前端）
4. ✅ 停止后端服务
5. ✅ 应用代码更新
6. ✅ 根据变更类型执行对应操作：
   - 后端变更：检查Python依赖
   - 前端变更：重新构建静态文件
7. ✅ 重启后端服务
8. ✅ 重新加载Nginx（如有前端变更）
9. ✅ 执行健康检查
10. ✅ 显示更新结果

### 针对本次排序功能更新：
- 只有 `backend/routes/queries.py` 文件变更
- 无需重新构建前端
- 只需重启后端服务即可生效

## 🔧 配置参数

在使用脚本前，需要修改以下配置：

```bash
# 编辑脚本配置
nano update_server.sh

# 主要配置项：
PROJECT_PATH="/opt/slowquery-reviewer"  # 你的项目部署路径
SERVICE_NAME="slowquery-reviewer"       # Supervisor中的服务名称
```

## 🏥 健康检查

更新完成后，脚本会自动执行健康检查：

```bash
# 检查服务状态
sudo supervisorctl status slowquery-reviewer

# 检查后端API
curl http://localhost:5172/

# 检查前端页面
curl http://localhost/

# 查看应用日志
sudo tail -f /var/log/slowquery-reviewer.log
```

## ⚡ 验证新功能

更新完成后，验证排序功能：

1. 访问前端页面：`http://your-server-ip/`
2. 登录系统
3. 在慢查询列表中使用**用户名过滤**或**数据库名过滤**
4. 观察结果是否按**执行次数倒序排列**
5. 执行次数显示在每个查询项右上角的蓝色徽章中

## 🚨 故障处理

如果更新失败：

```bash
# 查看详细错误
sudo supervisorctl tail slowquery-reviewer

# 手动重启服务
sudo supervisorctl restart slowquery-reviewer

# 检查代码状态
cd /path/to/project
git status
git log --oneline -5

# 回滚到上一版本（如果必要）
git reset --hard HEAD~1
sudo supervisorctl restart slowquery-reviewer
```

## 📝 更新记录

每次使用脚本更新后，建议记录：
- 更新时间
- 提交ID
- 变更内容
- 验证结果

## 💡 最佳实践

1. **更新前备份**：重要变更前先备份关键文件
2. **分步验证**：更新后逐步验证各项功能
3. **日志监控**：更新后观察日志确保无异常
4. **回滚准备**：了解快速回滚方法以防问题

---

使用这个增量更新方案，你可以快速将GitHub上的代码变更同步到服务器，无需重新部署整个应用！
