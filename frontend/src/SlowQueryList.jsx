import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Form, Badge, Button } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { Pagination } from 'react-bootstrap'
import { queryAPI } from './services/api'
import { DatabaseIcon, UserIcon, ClockIcon, RefreshIcon, HashIcon, SearchIcon } from './components/Icon'

const StatusBadge = ({ status }) => (
  <Badge bg={
    status === '待优化' ? 'danger' : 
    status === 'SQL已有优化建议' ? 'success' : 'secondary'
  }>{status}</Badge>
)
const QueryItem = React.memo(({ fingerprint }) => {
  const navigate = useNavigate();

  const handleClick = useCallback(() => {
    navigate(`/query/${fingerprint.checksum}`);
  }, [navigate, fingerprint.checksum]);

  return (
    <div 
      className="border rounded p-3 mb-3 shadow-sm hover-shadow" 
      style={{ 
        cursor: 'pointer',
        backgroundColor: '#fff',
        transition: 'all 0.2s ease-in-out'
      }}
      onClick={handleClick}
    >
      <div className="d-flex flex-column">
        {/* 顶部状态栏 */}
        <div className="d-flex justify-content-between align-items-center mb-3">
          <div className="d-flex align-items-center">
            <StatusBadge status={fingerprint.reviewed_status} />
            <span className="ms-3 fw-medium text-primary">
              <DatabaseIcon className="me-2" size={16} />
              {fingerprint.dbname}
            </span>
            <span className="ms-3">
              <UserIcon className="me-2" size={16} />
              {fingerprint.username}
            </span>
          </div>
          <div className="d-flex align-items-center">
            <span className="me-3 text-muted small">
              <ClockIcon className="me-1" size={14} />
              {fingerprint.last_occurrence ? (() => {
                const date = new Date(fingerprint.last_occurrence);
                date.setHours(date.getHours() - 8); // 减去8小时
                return date.toLocaleString('zh-CN', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                  hour12: false
                });
              })() : '无执行记录'}
            </span>
            <Badge bg="info" className="me-2">
              <RefreshIcon className="me-1" size={14} />
              {fingerprint.total_occurrences}
            </Badge>
            <Badge bg="secondary" className="text-monospace">
              <HashIcon className="me-1" size={14} />
              {fingerprint.checksum.slice(0, 6)}
            </Badge>
          </div>
        </div>
        
        {/* SQL语句 */}
        <pre className="p-3 bg-light rounded border" style={{ 
          whiteSpace: 'pre-wrap',
          fontSize: '0.9em',
          margin: 0
        }}>
          {fingerprint.normalized_sql}
        </pre>
      </div>
    </div>
  )
});

export default function SlowQueryList() {
  const [filter, setFilter] = useState({});
  const [queries, setQueries] = useState({ data: [], total: 0 });
  const [pagination, setPagination] = useState({ page: 1, per_page: 20 });
  const [loading, setLoading] = useState(false);

  // 优化的查询加载函数
  const loadQueries = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        ...filter,
        ...pagination
      };
      
      const response = await queryAPI.getQueries(params);
      
      if (response.data.success) {
        setQueries(response.data.data);
      } else {
        throw new Error(response.data.message);
      }
    } catch (error) {
      console.error('加载查询列表失败:', error);
      alert('加载查询列表失败: ' + (error.response?.data?.message || error.message));
    } finally {
      setLoading(false);
    }
  }, [filter, pagination]);

  useEffect(() => {
    loadQueries();
  }, [filter, pagination]); // 移除loadQueries依赖避免无限循环

  const handlePageChange = useCallback((newPage) => {
    setPagination(prev => ({ ...prev, page: newPage }))
  }, []);

  // 优化过滤器处理
  const handleFilterChange = useCallback((key, value) => {
    setFilter(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 })); // 重置到第一页
  }, []);

  return (
    <div className="container-fluid mt-4" style={{ maxWidth: '1400px' }}>
      {/* 过滤栏 */}
      <div className="row mb-4 g-3">
        <div className="col-lg-4 col-md-6">
          <div className="input-group">
            <span className="input-group-text">
              <SearchIcon size={16} />
            </span>
            <Form.Control 
              placeholder="按用户名过滤"
              className="form-control-lg"
              onChange={e => handleFilterChange('username', e.target.value)}
            />
          </div>
        </div>
        <div className="col-lg-4 col-md-6">
          <div className="input-group">
            <span className="input-group-text">
              <DatabaseIcon size={16} />
            </span>
            <Form.Control
              placeholder="按数据库过滤"
              className="form-control-lg"
              onChange={e => handleFilterChange('dbname', e.target.value)}
            />
          </div>
        </div>
      </div>
      
      {/* 慢查询列表 */}
      <div className="mb-3">
        {queries.data.map(query => (
          <QueryItem key={query.checksum} fingerprint={query} />
        ))}
      </div>

      {/* 分页 */}
      <div className="d-flex justify-content-center">
        <Pagination>
          <Pagination.Prev 
            onClick={() => handlePageChange(pagination.page - 1)}
            disabled={pagination.page === 1}
          />
          
          {(() => {
            const totalPages = Math.ceil(queries.total / pagination.per_page);
            const start = Math.max(1, pagination.page - 2);
            const end = Math.min(totalPages, pagination.page + 2);
            
            return Array.from({ length: end - start + 1 }, (_, i) => (
              <Pagination.Item
                key={start + i}
                active={start + i === pagination.page}
                onClick={() => handlePageChange(start + i)}
              >
                {start + i}
              </Pagination.Item>
            ))
          })()}

          <Pagination.Next
            onClick={() => handlePageChange(pagination.page + 1)}
            disabled={pagination.page >= Math.ceil(queries.total / pagination.per_page)}
          />
        </Pagination>
      </div>
    </div>
  )
}