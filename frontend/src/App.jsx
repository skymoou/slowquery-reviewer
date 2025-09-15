import React, { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import SlowQueryList from './SlowQueryList'
import QueryDetail from './QueryDetail'
import UserStats from './components/UserStats'
import Login from './pages/Login'
import { DatabaseIcon, HomeIcon, BarChartIcon, UserIcon, LogoutIcon } from './components/Icon'
import 'bootstrap/dist/css/bootstrap.min.css'
import { Container, Navbar, Nav } from 'react-bootstrap'
import axios from 'axios'

function PrivateRoute({ children }) {
  const isAuthenticated = localStorage.getItem('token');
  return isAuthenticated ? children : <Navigate to="/login" />;
}

function AppNavbar({ user, onLogout }) {
  return (
    <Navbar bg="primary" variant="dark" className="mb-4" expand="lg">
      <Container>
        <Navbar.Brand href="/" className="d-flex align-items-center">
          <DatabaseIcon className="me-2" size={20} />
          慢查询记录系统
        </Navbar.Brand>
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            {user && (
              <>
                <Nav.Link href="/" active={window.location.pathname === '/'}>
                  <HomeIcon className="me-1" size={16} />首页
                </Nav.Link>
                <Nav.Link href="/stats" active={window.location.pathname === '/stats'}>
                  <BarChartIcon className="me-1" size={16} />用户统计
                </Nav.Link>
              </>
            )}
          </Nav>
          {user && (
            <Nav>
              <span className="navbar-text me-3">
                <UserIcon className="me-1" size={16} />
                {user.username} ({user.role_name})
              </span>
              <Nav.Link onClick={onLogout} className="text-white">
                <LogoutIcon className="me-1" size={16} />
                退出登录
              </Nav.Link>
            </Nav>
          )}
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
}

function App() {
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('user')));

  useEffect(() => {
    // 监听用户状态变化
    const handleStorageChange = () => {
      setUser(JSON.parse(localStorage.getItem('user')));
    };
    const handleUserLogin = () => {
      setUser(JSON.parse(localStorage.getItem('user')));
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('userLogin', handleUserLogin);

    // 设置全局 axios 默认值
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('userLogin', handleUserLogin);
    };
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
    window.location.href = '/login';
  };

  return (
    <Router>
      <div className="App">
        <AppNavbar user={user} onLogout={handleLogout} />
        <Container>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={
              <PrivateRoute>
                <SlowQueryList />
              </PrivateRoute>
            } />
            <Route path="/stats" element={
              <PrivateRoute>
                <UserStats />
              </PrivateRoute>
            } />
            <Route path="/query/:checksum" element={
              <PrivateRoute>
                <QueryDetail />
              </PrivateRoute>
            } />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </Container>
      </div>
    </Router>
  )
}

export default App
