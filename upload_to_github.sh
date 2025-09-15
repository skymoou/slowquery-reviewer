#!/bin/bash

# ============================================
# GitHub代码上传脚本
# ============================================
# 使用方法：bash upload_to_github.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Git是否安装
check_git() {
    if ! command -v git &> /dev/null; then
        log_error "Git未安装，请先安装Git"
        log_info "Ubuntu/Debian: sudo apt install git"
        log_info "CentOS/RHEL: sudo yum install git"
        log_info "Windows: 下载 https://git-scm.com/download/win"
        exit 1
    fi
    
    log_success "Git已安装: $(git --version)"
}

# 配置Git用户信息
setup_git_config() {
    log_info "配置Git用户信息..."
    
    # 检查是否已配置
    if git config --global user.name >/dev/null 2>&1; then
        log_info "Git用户名已配置: $(git config --global user.name)"
    else
        read -p "请输入Git用户名: " git_username
        git config --global user.name "$git_username"
        log_success "Git用户名已设置: $git_username"
    fi
    
    if git config --global user.email >/dev/null 2>&1; then
        log_info "Git邮箱已配置: $(git config --global user.email)"
    else
        read -p "请输入Git邮箱: " git_email
        git config --global user.email "$git_email"
        log_success "Git邮箱已设置: $git_email"
    fi
}

# 初始化Git仓库
init_repository() {
    log_info "初始化Git仓库..."
    
    if [ -d ".git" ]; then
        log_info "Git仓库已存在"
    else
        git init
        log_success "Git仓库初始化完成"
    fi
}

# 添加文件到Git
add_files() {
    log_info "添加文件到Git..."
    
    # 检查.gitignore是否存在
    if [ ! -f ".gitignore" ]; then
        log_warning ".gitignore文件不存在，建议先创建"
    fi
    
    # 添加所有文件
    git add .
    
    # 显示将要提交的文件
    echo
    log_info "将要提交的文件:"
    git status --porcelain
    echo
    
    read -p "确认添加这些文件? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "操作已取消"
        exit 0
    fi
}

# 创建提交
create_commit() {
    log_info "创建Git提交..."
    
    # 检查是否有文件要提交
    if git diff --staged --quiet; then
        log_warning "没有文件需要提交"
        return 0
    fi
    
    # 默认提交信息
    default_message="初始提交: MySQL慢查询分析系统生产版本

特性:
✨ Python Flask后端API
✨ Vue.js前端界面
✨ MySQL慢查询日志解析和分析
✨ 用户认证和权限管理
✨ 生产环境部署配置
✨ 完整的运维管理脚本

技术栈:
🔧 后端: Python 3.8+, Flask, MySQL
🎨 前端: Vue.js, Element UI
🚀 部署: Nginx, Gunicorn, Supervisor
💾 数据库: MySQL 8.0+

优化:
⚡ 74.8%代码精简，性能优化
🧹 移除测试文件、Docker配置、Windows脚本
📝 完整的生产环境部署文档"
    
    echo "提交信息预览:"
    echo "----------------------------------------"
    echo "$default_message"
    echo "----------------------------------------"
    echo
    
    read -p "使用默认提交信息? (Y/n): " use_default
    
    if [[ "$use_default" =~ ^[Nn]$ ]]; then
        read -p "请输入提交信息: " commit_message
    else
        commit_message="$default_message"
    fi
    
    git commit -m "$commit_message"
    log_success "提交创建完成"
}

# 添加远程仓库
add_remote() {
    log_info "配置远程仓库..."
    
    # 检查是否已有远程仓库
    if git remote get-url origin >/dev/null 2>&1; then
        current_remote=$(git remote get-url origin)
        log_info "远程仓库已配置: $current_remote"
        
        read -p "是否要更改远程仓库地址? (y/N): " change_remote
        if [[ ! "$change_remote" =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi
    
    echo
    log_warning "请先在GitHub上创建一个新仓库:"
    log_info "1. 访问 https://github.com"
    log_info "2. 点击右上角 '+' -> 'New repository'"
    log_info "3. 仓库名建议: slowquery-reviewer"
    log_info "4. 选择 Public 或 Private"
    log_info "5. 不要勾选 'Initialize with README'"
    log_info "6. 点击 'Create repository'"
    echo
    
    read -p "请输入GitHub用户名: " github_username
    read -p "请输入仓库名称 (默认: slowquery-reviewer): " repo_name
    repo_name=${repo_name:-slowquery-reviewer}
    
    remote_url="https://github.com/$github_username/$repo_name.git"
    
    if git remote get-url origin >/dev/null 2>&1; then
        git remote set-url origin "$remote_url"
        log_success "远程仓库地址已更新: $remote_url"
    else
        git remote add origin "$remote_url"
        log_success "远程仓库已添加: $remote_url"
    fi
}

# 推送到GitHub
push_to_github() {
    log_info "推送代码到GitHub..."
    
    # 检查当前分支
    current_branch=$(git branch --show-current)
    if [ -z "$current_branch" ]; then
        # 如果没有分支，创建main分支
        git checkout -b main
        current_branch="main"
        log_info "创建并切换到main分支"
    fi
    
    log_info "当前分支: $current_branch"
    
    # 推送代码
    if git ls-remote --heads origin "$current_branch" | grep -q "$current_branch"; then
        # 分支已存在，直接推送
        git push origin "$current_branch"
    else
        # 分支不存在，首次推送
        git push -u origin "$current_branch"
    fi
    
    log_success "代码推送完成！"
    
    # 显示仓库信息
    remote_url=$(git remote get-url origin)
    echo
    echo "============================================"
    log_success "代码已成功上传到GitHub！"
    echo "============================================"
    echo
    echo "🔗 仓库地址: $remote_url"
    echo "📱 访问方式: ${remote_url%.git}"
    echo "🌿 当前分支: $current_branch"
    echo
    echo "📋 后续操作建议:"
    echo "1. 访问GitHub仓库页面查看代码"
    echo "2. 编辑仓库描述和标签"
    echo "3. 设置仓库访问权限"
    echo "4. 启用GitHub Pages (如需要)"
    echo "5. 配置CI/CD流水线 (如需要)"
    echo
}

# 主函数
main() {
    echo
    echo "============================================"
    echo "慢查询分析系统 - GitHub上传脚本"
    echo "============================================"
    echo
    
    # 检查当前目录
    if [ ! -f "README.md" ] || [ ! -d "backend" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi
    
    log_info "准备上传慢查询分析系统到GitHub..."
    echo
    
    check_git
    setup_git_config
    init_repository
    add_files
    create_commit
    add_remote
    push_to_github
    
    echo
    log_success "🎉 上传完成！感谢使用慢查询分析系统！"
}

# 错误处理
trap 'log_error "上传过程中发生错误"; exit 1' ERR

# 执行主函数
main "$@"
