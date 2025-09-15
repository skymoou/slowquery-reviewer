import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Form, Button, Alert, Spinner } from 'react-bootstrap';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { queryAPI } from './services/api';

const QueryDetail = () => {
  const { checksum } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [detailsData, setDetailsData] = useState(null);
  const [comments, setComments] = useState('');
  const [reviewedStatus, setReviewedStatus] = useState('待优化');
  const [user] = useState(JSON.parse(localStorage.getItem('user')));
  const canEdit = user?.permissions?.includes('OPTIMIZATION_EDIT');

  useEffect(() => {
    loadDetails();
  }, [checksum]);

  const loadDetails = async () => {
    try {
      const response = await queryAPI.getQueryDetails(checksum);
      if (response.data.success) {
        const data = response.data.data;
        setDetailsData(data);
        setComments(data.details[0]?.comments || '');
        setReviewedStatus(data.details[0]?.reviewed_status || '待优化');
      } else {
        throw new Error(response.data.message);
      }
    } catch (err) {
      setError(err.response?.data?.message || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveComments = async () => {
    try {
      const response = await queryAPI.updateComments(checksum, {
        comments,
        reviewed_status: reviewedStatus
      });
      if (response.data.success) {
        alert('优化建议保存成功！');
        // 刷新数据
        loadDetails();
      } else {
        throw new Error(response.data.message);
      }
    } catch (err) {
      alert('保存失败: ' + (err.response?.data?.message || err.message));
    }
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center my-5">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">加载中...</span>
        </Spinner>
      </div>
    );
  }

  if (error) {
    return <Alert variant="danger">{error}</Alert>;
  }

  if (!detailsData) {
    return <Alert variant="warning">未找到查询详情</Alert>;
  }

  const { details, trend } = detailsData;
  const queryDetail = details[0];

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>查询详情</h2>
        <Button variant="outline-secondary" onClick={() => navigate('/')}>
          返回列表
        </Button>
      </div>

      <Card className="mb-4">
        <Card.Header>
          <h5 className="mb-0">基本信息</h5>
        </Card.Header>
        <Card.Body>
          <p><strong>检查码：</strong>{checksum}</p>
          <p><strong>SQL语句：</strong></p>
          <pre className="bg-light p-3 rounded">{queryDetail?.sql_text}</pre>
        </Card.Body>
      </Card>

      <Card className="mb-4">
        <Card.Header>
          <h5 className="mb-0">执行趋势</h5>
        </Card.Header>
        <Card.Body>
          <LineChart width={800} height={300} data={trend}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="query_time" stroke="#8884d8" name="查询耗时(s)" />
          </LineChart>
        </Card.Body>
      </Card>

      <Card>
        <Card.Header>
          <h5 className="mb-0">优化建议</h5>
        </Card.Header>
        <Card.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>处理状态</Form.Label>
              <Form.Select 
                value={reviewedStatus}
                onChange={(e) => setReviewedStatus(e.target.value)}
                disabled={!canEdit}
              >
                <option value="待优化">待优化</option>
                <option value="已加索引优化">已加索引优化</option>
                <option value="已自主添加索引优化">已自主添加索引优化</option>
                <option value="周期性跑批">周期性跑批</option>
                <option value="SQL已最优">SQL已最优</option>
                <option value="需研发修改SQL~SQL改写">需研发修改SQL~SQL改写</option>
                <option value="需研发修改SQL~隐式转换">需研发修改SQL~隐式转换</option>
                <option value="放弃-1.全表扫描">放弃-1.全表扫描</option>
                <option value="放弃-2.全表聚合">放弃-2.全表聚合</option>
                <option value="放弃-3.扫描行数超40W">放弃-3.扫描行数超40W</option>
                <option value="放弃-模糊查询">放弃-模糊查询</option>
                <option value="放弃-模糊查询+or查询">放弃-模糊查询+or查询</option>
                <option value="放弃-分页查询">放弃-分页查询</option>
                <option value="放弃-or查询">放弃-or查询</option>
              </Form.Select>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>补充说明（可选）</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="如有需要，请输入补充说明..."
                disabled={!canEdit}
              />
            </Form.Group>
            
            {canEdit && (
              <Button
                variant="primary"
                onClick={handleSaveComments}
              >
                保存优化建议
              </Button>
            )}
          </Form>
        </Card.Body>
      </Card>
    </div>
  );
};

export default QueryDetail;
