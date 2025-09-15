# -*- coding: utf-8 -*-
"""
慢查询解析器用户名到数据库名映射配置
当慢查询日志中无法获取数据库名时，根据用户名推断数据库名
"""

# 用户名到数据库名的映射字典
# 格式: '用户名': '数据库名'
# 支持精确匹配和部分匹配

USER_TO_DATABASE_MAPPING = {
    # 现有映射
    'agentuser': 'posx_agent',
    'tras_user': 'posx_prd',
    
    # 可以添加更多映射关系
    # 'username1': 'database1',
    # 'username2': 'database2',
    
    # 示例: 更多可能的映射
    # 'admin': 'admin_db',
    # 'readonly': 'readonly_db',
    # 'backup': 'backup_db',
    # 'monitor': 'monitor_db',
}

# 如果需要在主脚本中使用，可以在脚本开头添加:
# try:
#     from username_mapping_config import USER_TO_DATABASE_MAPPING
# except ImportError:
#     # 使用默认映射
#     USER_TO_DATABASE_MAPPING = {
#         'agentuser': 'posx_agent',
#         'tras_user': 'posx_prd',
#     }
