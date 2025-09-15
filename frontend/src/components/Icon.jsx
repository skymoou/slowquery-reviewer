import React from 'react';
import { 
  FiDatabase, 
  FiHome, 
  FiBarChart, 
  FiUser, 
  FiLogOut, 
  FiClock, 
  FiRefreshCw, 
  FiHash, 
  FiSearch 
} from 'react-icons/fi';

// Bootstrap Icons 到 React Icons 的映射
const IconMap = {
  'bi-database-fill': FiDatabase,
  'bi-database': FiDatabase,
  'bi-house-door': FiHome,
  'bi-bar-chart': FiBarChart,
  'bi-person-circle': FiUser,
  'bi-person': FiUser,
  'bi-box-arrow-right': FiLogOut,
  'bi-clock-history': FiClock,
  'bi-repeat': FiRefreshCw,
  'bi-hash': FiHash,
  'bi-search': FiSearch,
};

/**
 * 图标组件 - 替代Bootstrap Icons
 * @param {string} name - Bootstrap图标名称
 * @param {string} className - CSS类名
 * @param {object} style - 内联样式
 * @param {string} size - 图标大小 (默认16px)
 */
export const Icon = ({ name, className = '', style = {}, size = 16, ...props }) => {
  const IconComponent = IconMap[name];
  
  if (!IconComponent) {
    console.warn(`图标 "${name}" 未找到，使用默认图标`);
    return <FiDatabase className={className} style={style} size={size} {...props} />;
  }
  
  return <IconComponent className={className} style={style} size={size} {...props} />;
};

// 常用图标的快捷组件
export const DatabaseIcon = (props) => <Icon name="bi-database" {...props} />;
export const HomeIcon = (props) => <Icon name="bi-house-door" {...props} />;
export const BarChartIcon = (props) => <Icon name="bi-bar-chart" {...props} />;
export const UserIcon = (props) => <Icon name="bi-person" {...props} />;
export const LogoutIcon = (props) => <Icon name="bi-box-arrow-right" {...props} />;
export const ClockIcon = (props) => <Icon name="bi-clock-history" {...props} />;
export const RefreshIcon = (props) => <Icon name="bi-repeat" {...props} />;
export const HashIcon = (props) => <Icon name="bi-hash" {...props} />;
export const SearchIcon = (props) => <Icon name="bi-search" {...props} />;

export default Icon;
