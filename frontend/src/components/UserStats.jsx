import React, { useState, useEffect, useCallback } from 'react';
import { queryAPI } from '../services/api';
import { Clock, PieChart } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  LineChart,
  Line
} from 'recharts';

const UserStats = () => {
  const [userStats, setUserStats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userDetail, setUserDetail] = useState(null);

  // 图表颜色配置
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFC658', '#FF7C7C'];

  // 获取用户统计数据 - 简化版本
  const fetchUserStats = useCallback(async () => {
    setLoading(true);
    try {
      const response = await queryAPI.getUserStats({});
      if (response.data.success) {
        setUserStats(response.data.data.user_stats);
      }
    } catch (error) {
      console.error('获取用户统计失败:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // 获取用户详细统计 - 简化版本
  const fetchUserDetail = useCallback(async (username) => {
    setLoading(true);
    try {
      const response = await queryAPI.getUserDetailStats(username, {});
      if (response.data.success) {
        setUserDetail(response.data.data);
        setSelectedUser(username);
      }
    } catch (error) {
      console.error('获取用户详细统计失败:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUserStats();
  }, [fetchUserStats]);

  // 格式化函数
  const formatTime = useCallback((seconds) => {
    if (seconds < 1) {
      return `${(seconds * 1000).toFixed(0)}ms`;
    }
    return `${seconds.toFixed(2)}s`;
  }, []);

  const formatNumber = useCallback((num) => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">用户慢查询统计</h1>
        <p className="text-gray-600">统计各用户的慢查询次数，排除已优化</p>
      </div>

      {/* 图表视图 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* 用户执行次数柱状图 */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">用户执行次数排行</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={userStats.slice(0, 10)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="username" 
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis />
              <Tooltip 
                formatter={(value, name) => [formatNumber(value), name]}
              />
              <Bar dataKey="total_occurrences" fill="#ef4444" name="执行次数" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 用户查询数饼图 */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">唯一查询数分布</h3>
          <ResponsiveContainer width="100%" height={300}>
            <RechartsPieChart>
              <Pie
                data={userStats.slice(0, 8)}
                cx="50%"
                cy="50%"
                outerRadius={100}
                dataKey="unique_queries"
                nameKey="username"
                label={({ username, unique_queries }) => `${username}: ${unique_queries}`}
              >
                {userStats.slice(0, 8).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </RechartsPieChart>
          </ResponsiveContainer>
        </div>

        {/* 平均响应时间对比 */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">平均响应时间对比</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={userStats.slice(0, 10)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="username" 
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis />
              <Tooltip 
                formatter={(value) => [formatTime(value), '平均响应时间']}
              />
              <Bar 
                dataKey="avg_query_time" 
                fill="#f59e0b" 
                name="平均响应时间"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 时间分布图（如果有用户详情数据） */}
        {userDetail && userDetail.time_distribution && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              {selectedUser} - 最近30天查询分布
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={userDetail.time_distribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="query_date" 
                  tickFormatter={(date) => new Date(date).toLocaleDateString()}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(date) => new Date(date).toLocaleDateString()}
                  formatter={(value, name) => [value, name]}
                />
                <Line 
                  type="monotone" 
                  dataKey="daily_count" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  name="每日查询数"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* 用户详细统计面板 */}
      {selectedUser && userDetail && (
        <div className="bg-white rounded-lg shadow-sm border mt-6">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center">
              <PieChart className="w-5 h-5 mr-2" />
              {selectedUser} 详细统计
            </h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 数据库分布 */}
              {userDetail.db_distribution && userDetail.db_distribution.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">数据库分布</h3>
                  <div className="space-y-2">
                    {userDetail.db_distribution.map((db, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <span className="font-medium">{db.dbname || '未知'}</span>
                        <div className="text-right">
                          <div className="text-sm text-gray-600">
                            {db.total_occurrences} 次执行
                          </div>
                          <div className="text-xs text-gray-500">
                            平均 {formatTime(db.avg_query_time)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 问题查询TOP5 */}
              {userDetail.queries && userDetail.queries.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">问题查询 TOP 5</h3>
                  <div className="space-y-3">
                    {userDetail.queries.slice(0, 5).map((query, index) => (
                      <div key={index} className="p-4 border border-gray-200 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-gray-900">
                            {query.dbname} - {query.occurrences} 次执行
                          </span>
                          <span className="text-sm text-red-600 font-bold">
                            {formatTime(query.avg_query_time)}
                          </span>
                        </div>
                        <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded font-mono">
                          {query.normalized_sql.length > 100 
                            ? `${query.normalized_sql.substring(0, 100)}...`
                            : query.normalized_sql
                          }
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-2">
                          <span>最近执行: {new Date(query.last_occurrence).toLocaleString()}</span>
                          <span>状态: {query.reviewed_status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserStats;
