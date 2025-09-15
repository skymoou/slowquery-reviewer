import React, { useState } from 'react';
import { Container, Form, Button, Alert, Card } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { userAPI } from '../services/api';

function Login() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await userAPI.login({
                username,
                password
            });

            if (response.data.success) {
                const token = response.data.data.token;
                // 保存token
                localStorage.setItem('token', token);
                // 保存用户信息
                localStorage.setItem('user', JSON.stringify(response.data.data.user));
                // 触发一个自定义事件以更新用户状态
                window.dispatchEvent(new Event('userLogin'));
                // 跳转到首页
                navigate('/');
            } else {
                setError(response.data.message || '登录失败');
            }
        } catch (err) {
            console.error('登录失败:', err);
            setError(err.response?.data?.message || '登录失败，请稍后重试');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Container className="d-flex align-items-center justify-content-center" style={{ minHeight: '100vh' }}>
            <div style={{ width: '100%', maxWidth: '400px' }}>
                <Card>
                    <Card.Body>
                        <h2 className="text-center mb-4">慢查询记录系统</h2>
                        {error && <Alert variant="danger">{error}</Alert>}
                        <Form onSubmit={handleSubmit}>
                            <Form.Group className="mb-3">
                                <Form.Label>用户名</Form.Label>
                                <Form.Control
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    required
                                    placeholder="请输入用户名"
                                />
                            </Form.Group>

                            <Form.Group className="mb-4">
                                <Form.Label>密码</Form.Label>
                                <Form.Control
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    placeholder="请输入密码"
                                />
                            </Form.Group>

                            <Button
                                className="w-100"
                                type="submit"
                                disabled={loading}
                            >
                                {loading ? '登录中...' : '登录'}
                            </Button>
                        </Form>
                    </Card.Body>
                </Card>
            </div>
        </Container>
    );
}

export default Login;
