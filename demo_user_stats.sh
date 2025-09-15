#!/bin/bash
# 用户统计功能演示脚本
# Quick Demo Script for User Statistics Features

echo "🎬 慢查询用户统计功能演示 - User Statistics Demo"
echo "=================================================="

# 检查环境
check_environment() {
    echo "🔍 检查演示环境..."
    
    # 检查后端是否运行
    if curl -s http://localhost:5172/api/health > /dev/null 2>&1; then
        echo "✅ 后端服务运行正常 (Backend: ✓)"
    else
        echo "❌ 后端服务未运行，请先启动: cd backend && python app.py"
        return 1
    fi
    
    # 检查前端是否运行
    if curl -s http://localhost:3001 > /dev/null 2>&1; then
        echo "✅ 前端服务运行正常 (Frontend: ✓)"
    else
        echo "❌ 前端服务未运行，请先启动: cd frontend && npm run dev"
        return 1
    fi
    
    echo "✅ 环境检查完成！"
    return 0
}

# 演示数据准备
prepare_demo_data() {
    echo "📊 准备演示数据..."
    
    # 检查是否有测试数据
    result=$(curl -s -H "Authorization: Bearer demo-token" \
        "http://localhost:5172/api/queries/stats/by-user?start_time=2024-01-01&end_time=2024-12-31")
    
    if echo "$result" | grep -q "users.*count"; then
        echo "✅ 发现现有数据，可以开始演示"
    else
        echo "⚠️  未发现足够数据，建议运行: cd backend && python insert_test_data.py"
        echo "   或者继续演示空数据状态"
    fi
}

# 功能演示
demo_features() {
    echo "🎭 开始功能演示..."
    echo ""
    
    echo "📈 1. 图表视图演示"
    echo "   - 访问: http://localhost:3001"
    echo "   - 登录后点击 '用户统计' 菜单"
    echo "   - 默认显示图表视图，包含4种图表："
    echo "     * 柱状图：用户查询数量对比"
    echo "     * 饼图：查询分布占比"
    echo "     * 折线图：时间趋势分析"
    echo "     * 面积图：累积趋势显示"
    echo ""
    
    echo "📋 2. 表格视图演示"
    echo "   - 点击右上角 '表格视图' 按钮"
    echo "   - 功能包括："
    echo "     * 🔍 搜索：输入用户名过滤"
    echo "     * 🔄 排序：点击列标题排序"
    echo "     * 📄 分页：底部翻页控制"
    echo "     * 👁️ 详情：点击眼睛图标查看详细统计"
    echo ""
    
    echo "🎯 3. 交互功能演示"
    echo "   - 图表悬浮：鼠标移动查看详细数据"
    echo "   - 用户详情：点击用户名查看时间分布"
    echo "   - 时间筛选：选择日期范围过滤数据"
    echo "   - 响应式：调整浏览器窗口测试适配"
    echo ""
}

# API演示
demo_api() {
    echo "🔌 API接口演示..."
    echo ""
    
    echo "📊 用户统计API:"
    echo "GET /api/queries/stats/by-user"
    echo "示例请求："
    curl -s -H "Authorization: Bearer demo-token" \
        "http://localhost:5172/api/queries/stats/by-user?start_time=2024-01-01&end_time=2024-12-31" | \
        python -m json.tool 2>/dev/null || echo "请求失败，请检查后端服务"
    echo ""
    
    echo "👤 用户详情API:"
    echo "GET /api/queries/stats/by-user/<username>"
    echo "示例：获取用户 'admin' 的详细统计"
}

# 性能测试
demo_performance() {
    echo "⚡ 性能测试演示..."
    echo ""
    
    echo "🔄 测试API响应时间..."
    time_start=$(date +%s%N)
    curl -s -H "Authorization: Bearer demo-token" \
        "http://localhost:5172/api/queries/stats/by-user" > /dev/null
    time_end=$(date +%s%N)
    time_diff=$(( (time_end - time_start) / 1000000 ))
    echo "✅ API响应时间: ${time_diff}ms"
    
    echo "📦 前端包大小检查..."
    if [ -d "frontend/dist" ]; then
        bundle_size=$(du -sh frontend/dist/assets/*.js 2>/dev/null | tail -1 | cut -f1)
        echo "✅ 构建包大小: ${bundle_size:-"未找到构建文件"}"
    else
        echo "⚠️  请先运行: cd frontend && npm run build"
    fi
}

# 错误场景演示
demo_error_scenarios() {
    echo "🚨 错误处理演示..."
    echo ""
    
    echo "1. 无效Token测试"
    result=$(curl -s -H "Authorization: Bearer invalid-token" \
        "http://localhost:5172/api/queries/stats/by-user")
    if echo "$result" | grep -q "error\|unauthorized"; then
        echo "✅ 正确处理无效Token"
    else
        echo "⚠️  Token验证可能有问题"
    fi
    
    echo ""
    echo "2. 无效日期范围测试"
    result=$(curl -s -H "Authorization: Bearer demo-token" \
        "http://localhost:5172/api/queries/stats/by-user?start_time=invalid&end_time=invalid")
    if echo "$result" | grep -q "error\|invalid"; then
        echo "✅ 正确处理无效日期"
    else
        echo "⚠️  日期验证可能需要加强"
    fi
}

# 浏览器兼容性检查
demo_browser_compatibility() {
    echo "🌐 浏览器兼容性说明..."
    echo ""
    echo "✅ 推荐浏览器："
    echo "   - Chrome 90+ (最佳体验)"
    echo "   - Firefox 88+"
    echo "   - Safari 14+"
    echo "   - Edge 90+"
    echo ""
    echo "📱 移动端支持："
    echo "   - 响应式设计，支持手机/平板访问"
    echo "   - 触摸友好的交互界面"
    echo "   - 自适应图表和表格布局"
}

# 主演示流程
main_demo() {
    echo "🚀 开始完整演示流程..."
    echo ""
    
    # 环境检查
    if ! check_environment; then
        echo "❌ 环境检查失败，请先启动服务"
        exit 1
    fi
    
    echo ""
    prepare_demo_data
    echo ""
    demo_features
    demo_api
    echo ""
    demo_performance
    echo ""
    demo_error_scenarios
    echo ""
    demo_browser_compatibility
    
    echo ""
    echo "🎉 演示完成！"
    echo ""
    echo "📋 演示总结："
    echo "1. ✅ 图表视图 - 4种可视化图表"
    echo "2. ✅ 表格视图 - 搜索、排序、分页"
    echo "3. ✅ 交互功能 - 悬浮、点击、筛选"
    echo "4. ✅ API接口 - RESTful设计，JSON响应"
    echo "5. ✅ 性能优化 - 快速响应，小包体积"
    echo "6. ✅ 错误处理 - 友好的错误提示"
    echo "7. ✅ 兼容性 - 跨浏览器，响应式"
    echo ""
    echo "🔗 快速访问："
    echo "   前端界面: http://localhost:3001"
    echo "   API文档: http://localhost:5172/api/docs (如果有)"
    echo ""
    echo "📞 如有问题，请检查："
    echo "   - 服务是否正常运行"
    echo "   - 网络连接是否正常"
    echo "   - 浏览器控制台是否有错误"
}

# 快速启动模式
quick_start() {
    echo "⚡ 快速启动演示环境..."
    
    # 启动后端
    echo "🔧 启动后端服务..."
    cd backend && python app.py &
    BACKEND_PID=$!
    sleep 3
    
    # 启动前端
    echo "🎨 启动前端服务..."
    cd ../frontend && npm run dev &
    FRONTEND_PID=$!
    sleep 5
    
    # 等待服务启动
    echo "⏳ 等待服务启动..."
    for i in {1..10}; do
        if curl -s http://localhost:5172/api/health > /dev/null 2>&1 && \
           curl -s http://localhost:3001 > /dev/null 2>&1; then
            echo "✅ 服务启动成功！"
            break
        fi
        echo "   等待中... ($i/10)"
        sleep 2
    done
    
    # 打开浏览器
    if command -v xdg-open > /dev/null; then
        xdg-open http://localhost:3001
    elif command -v open > /dev/null; then
        open http://localhost:3001
    else
        echo "🌐 请手动打开浏览器访问: http://localhost:3001"
    fi
    
    echo "🎬 演示环境已启动！"
    echo "   前端: http://localhost:3001"
    echo "   后端: http://localhost:5172"
    echo ""
    echo "按任意键停止服务..."
    read -n 1
    
    # 停止服务
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "🛑 服务已停止"
}

# 命令行参数处理
case "${1:-demo}" in
    "quick")
        quick_start
        ;;
    "demo")
        main_demo
        ;;
    "env")
        check_environment
        ;;
    "api")
        demo_api
        ;;
    "perf")
        demo_performance
        ;;
    *)
        echo "用法: $0 [quick|demo|env|api|perf]"
        echo ""
        echo "参数说明："
        echo "  quick - 快速启动演示环境"
        echo "  demo  - 完整功能演示 (默认)"
        echo "  env   - 仅检查环境"
        echo "  api   - 仅演示API"
        echo "  perf  - 仅性能测试"
        ;;
esac
