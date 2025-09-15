import React from 'react';
import { useAuth } from '../contexts/AuthContext';

export const RequireAuth = ({ children }) => {
  const { user } = useAuth();
  
  if (!user) {
    return window.location.href = '/login';
  }
  
  return children;
};

export const RequirePermission = ({ permission, children }) => {
  const { hasPermission } = useAuth();
  
  if (!hasPermission(permission)) {
    return null;
  }
  
  return children;
};
