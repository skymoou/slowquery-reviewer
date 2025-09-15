import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

// 配置axios基础URL
const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:5172/api' 
  : '/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      checkAuth();
    } else {
      setLoading(false);
    }
  }, []);

  const checkAuth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/user/info`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.data.success) {
        setUser(response.data.data);
      } else {
        localStorage.removeItem('token');
      }
    } catch (error) {
      console.error('检查认证失败:', error);
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/login`, { username, password });
      if (response.data.success) {
        // 后端返回的数据结构是 { data: { token: "...", user: {...} } }
        const { token, user } = response.data.data;
        localStorage.setItem('token', token);
        setUser(user);
      } else {
        throw new Error(response.data.message || '登录失败');
      }
    } catch (error) {
      console.error('登录错误详情:', error);
      if (error.response) {
        console.error('响应状态:', error.response.status);
        console.error('响应数据:', error.response.data);
        throw new Error(error.response.data?.message || '登录失败');
      } else if (error.request) {
        console.error('请求错误:', error.request);
        throw new Error('网络连接失败，请检查后端服务是否运行');
      } else {
        console.error('其他错误:', error.message);
        throw new Error(error.message || '登录失败');
      }
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API_BASE_URL}/logout`, null, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
    } finally {
      localStorage.removeItem('token');
      setUser(null);
    }
  };

  const hasPermission = (permission) => {
    if (!user) return false;
    return user.permissions.includes(permission) || user.roles.includes('ADMIN');
  };

  const hasRole = (role) => {
    if (!user) return false;
    return user.roles.includes(role);
  };

  const value = {
    user,
    loading,
    login,
    logout,
    hasPermission,
    hasRole
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
