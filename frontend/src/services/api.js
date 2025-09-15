import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: process.env.NODE_ENV === 'development' 
    ? 'http://localhost:5172/api'  // 开发环境直接连接后端
    : '/api',  // 生产环境使用相对路径
  timeout: 10000,  // 请求超时时间
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 从localStorage获取token
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // token过期或无效，清除本地存储并重定向到登录页
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API方法集合
export const queryAPI = {
  // 获取慢查询列表
  getQueries: async (params) => {
    console.log('正在请求慢查询列表，参数:', params);
    try {
      const response = await api.get('/queries', { params });
      console.log('获取慢查询列表成功:', response.data);
      return response;
    } catch (error) {
      console.error('获取慢查询列表失败:', error.response || error);
      throw error;
    }
  },

  // 获取慢查询详情
  getQueryDetails: async (checksum) => {
    console.log('正在请求慢查询详情，checksum:', checksum);
    try {
      const response = await api.get(`/queries/${checksum}`);
      console.log('获取慢查询详情成功:', response.data);
      return response;
    } catch (error) {
      console.error('获取慢查询详情失败:', error.response || error);
      throw error;
    }
  },

  // 更新查询评论和状态
  updateComments: async (checksum, data) => {
    console.log('正在更新慢查询评论，checksum:', checksum, '数据:', data);
    try {
      const response = await api.post(`/queries/${checksum}/review`, data);
      console.log('更新慢查询评论成功:', response.data);
      return response;
    } catch (error) {
      console.error('更新慢查询评论失败:', error.response || error);
      throw error;
    }
  },

  // 导出慢查询数据
  exportQueries: (params) => api.get('/queries/export', { 
    params,
    responseType: 'blob'
  }),

  // 获取用户慢查询统计
  getUserStats: async (params) => {
    console.log('正在请求用户慢查询统计，参数:', params);
    try {
      const response = await api.get('/queries/stats/by-user', { params });
      console.log('获取用户慢查询统计成功:', response.data);
      return response;
    } catch (error) {
      console.error('获取用户慢查询统计失败:', error.response || error);
      throw error;
    }
  },

  // 获取指定用户的详细统计
  getUserDetailStats: async (username, params) => {
    console.log('正在请求用户详细统计，用户:', username, '参数:', params);
    try {
      const response = await api.get(`/queries/stats/by-user/${username}`, { params });
      console.log('获取用户详细统计成功:', response.data);
      return response;
    } catch (error) {
      console.error('获取用户详细统计失败:', error.response || error);
      throw error;
    }
  }
};

// 用户相关API
export const userAPI = {
  // 用户登录
  login: (credentials) => api.post('/login', credentials),
  
  // 获取用户信息
  getUserInfo: () => api.get('/user/info'),
  
  // 更新用户信息
  updateProfile: (data) => api.put('/user/profile', data),
  
  // 修改密码
  changePassword: (data) => api.put('/user/password', data)
};
