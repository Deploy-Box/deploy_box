import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/auth.css';

const Login = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      const baseUrl = window.env.REACT_APP_BACKEND_URL?.endsWith("/")
        ? window.env.REACT_APP_BACKEND_URL
        : `${window.env.REACT_APP_BACKEND_URL}/`;
      const response = await axios.post(`${baseUrl}api/auth/login`, formData);
      localStorage.setItem('accessToken', response.data.accessToken);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.message || 'An error occurred during login');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <div className="auth-header">
          <h2 className="auth-title">Sign in to your account</h2>
          <p className="auth-subtitle">
            Or{' '}
            <a href="/register" className="auth-link">
              create a new account
            </a>
          </p>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          {error && (
            <div className="auth-error" role="alert">
              <span>{error}</span>
            </div>
          )}
          <div className="auth-input-group">
            <input
              id="email"
              name="email"
              type="email"
              required
              className="auth-input"
              placeholder="Email address"
              value={formData.email}
              onChange={handleChange}
            />
            <input
              id="password"
              name="password"
              type="password"
              required
              className="auth-input"
              placeholder="Password"
              value={formData.password}
              onChange={handleChange}
            />
          </div>

          <button
            type="submit"
            className="auth-button"
          >
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;
