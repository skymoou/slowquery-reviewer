import React, { useState, useRef, useEffect } from 'react';
import { Form, Badge, Button } from 'react-bootstrap';
import { DatabaseIcon, ChevronDownIcon, ChevronUpIcon } from './Icon';

const MultiSelectDropdown = ({ 
  options = [], 
  selectedValues = [], 
  onChange, 
  placeholder = "选择数据库",
  maxDisplayItems = 2,
  disabled = false 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef(null);

  // 过滤选项
  const filteredOptions = options.filter(option =>
    option.dbname.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // 处理选择变更
  const handleSelect = (dbname) => {
    const newSelected = selectedValues.includes(dbname)
      ? selectedValues.filter(item => item !== dbname)
      : [...selectedValues, dbname];
    
    onChange(newSelected);
  };

  // 全选/取消全选
  const handleSelectAll = () => {
    if (selectedValues.length === filteredOptions.length) {
      onChange([]);
    } else {
      onChange(filteredOptions.map(option => option.dbname));
    }
  };

  // 清空选择
  const handleClear = () => {
    onChange([]);
  };

  // 点击外部关闭下拉框
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 显示的文本
  const getDisplayText = () => {
    if (selectedValues.length === 0) {
      return placeholder;
    }
    
    if (selectedValues.length <= maxDisplayItems) {
      return selectedValues.join(', ');
    }
    
    return `${selectedValues.slice(0, maxDisplayItems).join(', ')} 等 ${selectedValues.length} 个`;
  };

  return (
    <div className="position-relative" ref={dropdownRef}>
      <div className="input-group">
        <span className="input-group-text">
          <DatabaseIcon size={16} />
        </span>
        <div
          className={`form-control form-control-lg d-flex align-items-center justify-content-between ${disabled ? 'disabled' : ''}`}
          style={{ 
            cursor: disabled ? 'not-allowed' : 'pointer',
            backgroundColor: disabled ? '#e9ecef' : '#fff'
          }}
          onClick={() => !disabled && setIsOpen(!isOpen)}
        >
          <span className={selectedValues.length === 0 ? 'text-muted' : ''}>
            {getDisplayText()}
          </span>
          {isOpen ? <ChevronUpIcon size={16} /> : <ChevronDownIcon size={16} />}
        </div>
      </div>

      {/* 选中项的徽章显示 */}
      {selectedValues.length > 0 && (
        <div className="mt-2 d-flex flex-wrap gap-1">
          {selectedValues.map(dbname => (
            <Badge 
              key={dbname} 
              bg="primary" 
              className="d-flex align-items-center"
            >
              {dbname}
              <button
                type="button"
                className="btn-close btn-close-white ms-1"
                style={{ fontSize: '0.6em' }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleSelect(dbname);
                }}
              />
            </Badge>
          ))}
        </div>
      )}

      {/* 下拉选项 */}
      {isOpen && !disabled && (
        <div 
          className="position-absolute w-100 bg-white border rounded shadow-lg"
          style={{ top: '100%', zIndex: 1050, maxHeight: '300px' }}
        >
          {/* 搜索框 */}
          <div className="p-2 border-bottom">
            <Form.Control
              size="sm"
              placeholder="搜索数据库..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClick={(e) => e.stopPropagation()}
            />
          </div>

          {/* 操作按钮 */}
          <div className="p-2 border-bottom d-flex gap-2">
            <Button 
              size="sm" 
              variant="outline-primary"
              onClick={handleSelectAll}
            >
              {selectedValues.length === filteredOptions.length ? '取消全选' : '全选'}
            </Button>
            <Button 
              size="sm" 
              variant="outline-secondary"
              onClick={handleClear}
              disabled={selectedValues.length === 0}
            >
              清空
            </Button>
          </div>

          {/* 选项列表 */}
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {filteredOptions.length === 0 ? (
              <div className="p-3 text-muted text-center">
                {searchTerm ? '未找到匹配的数据库' : '暂无数据库'}
              </div>
            ) : (
              filteredOptions.map(option => (
                <div
                  key={option.dbname}
                  className={`p-2 d-flex align-items-center justify-content-between hover-bg-light ${
                    selectedValues.includes(option.dbname) ? 'bg-light' : ''
                  }`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => handleSelect(option.dbname)}
                >
                  <div className="d-flex align-items-center">
                    <Form.Check
                      type="checkbox"
                      checked={selectedValues.includes(option.dbname)}
                      onChange={() => {}} // 由外层div处理
                      className="me-2"
                    />
                    <span className="fw-medium">{option.dbname}</span>
                  </div>
                  <div className="text-muted small">
                    <span>{option.query_count} 个查询</span>
                    <span className="ms-2">{option.total_occurrences} 次执行</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        .hover-bg-light:hover {
          background-color: #f8f9fa !important;
        }
      `}</style>
    </div>
  );
};

export default MultiSelectDropdown;
