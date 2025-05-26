import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/auth.css';

const Register = () => {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
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

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    try {
      const baseUrl = window.env.REACT_APP_BACKEND_URL?.endsWith("/")
        ? window.env.REACT_APP_BACKEND_URL
        : `${window.env.REACT_APP_BACKEND_URL}/`;
      const response = await axios.post(`${baseUrl}api/auth/register`, {
        fullName: formData.fullName,
        email: formData.email,
        password: formData.password,
        phoneNumber: formData.phoneNumber
      });
      
      if (response.data.success) {
        navigate('/login');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'An error occurred during registration');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <div className="auth-header">
          <h2 className="auth-title">Create your account</h2>
          <p className="auth-subtitle">
            Or{' '}
            <a href="/login" className="auth-link">
              sign in to your account
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
              id="fullName"
              name="fullName"
              type="text"
              required
              className="auth-input"
              placeholder="Full name"
              value={formData.fullName}
              onChange={handleChange}
            />
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
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              required
              className="auth-input"
              placeholder="Confirm Password"
              value={formData.confirmPassword}
              onChange={handleChange}
            />
          </div>

          <button
            type="submit"
            className="auth-button"
          >
            Create Account
          </button>
        </form>
      </div>
    </div>
  );
};

export default Register; 