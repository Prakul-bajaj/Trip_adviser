// context/AuthContext.js
import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext();

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

  // Check if user is logged in on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      const savedUser = localStorage.getItem('user');
      
      if (token && savedUser) {
        try {
          setUser(JSON.parse(savedUser));
        } catch (error) {
          console.error('Failed to parse user data:', error);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
      
      setLoading(false);
    };
    
    checkAuth();
  }, []);

  const signup = async (userData) => {
    try {
      console.log('🔐 AuthContext: Starting signup...');
      
      const response = await authAPI.signup(userData);
      
      console.log('✅ AuthContext: Signup response received');
      
      // Set user from response
      if (response.data.user) {
        setUser(response.data.user);
      }
      
      return { 
        success: true, 
        user: response.data.user 
      };
      
    } catch (error) {
      console.error('❌ AuthContext: Signup error:', error);
      
      // Extract error details
      let errorMessage = 'Signup failed. Please try again.';
      let fieldErrors = {};
      
      if (error.response?.data) {
        const errorData = error.response.data;
        
        // Check for field-specific errors
        if (errorData.email) {
          fieldErrors.email = Array.isArray(errorData.email) 
            ? errorData.email[0] 
            : errorData.email;
        }
        
        if (errorData.password) {
          fieldErrors.password = Array.isArray(errorData.password) 
            ? errorData.password[0] 
            : errorData.password;
        }
        
        if (errorData.password_confirm) {
          fieldErrors.confirmPassword = Array.isArray(errorData.password_confirm) 
            ? errorData.password_confirm[0] 
            : errorData.password_confirm;
        }
        
        if (errorData.first_name) {
          fieldErrors.username = Array.isArray(errorData.first_name) 
            ? errorData.first_name[0] 
            : errorData.first_name;
        }
        
        if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData.non_field_errors) {
          errorMessage = Array.isArray(errorData.non_field_errors)
            ? errorData.non_field_errors[0]
            : errorData.non_field_errors;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      return { 
        success: false, 
        error: errorMessage,
        errors: Object.keys(fieldErrors).length > 0 ? fieldErrors : null
      };
    }
  };

  const login = async (credentials) => {
    try {
      console.log('🔐 AuthContext: Starting login...');
      
      const response = await authAPI.login(credentials);
      
      console.log('✅ AuthContext: Login response received');
      
      if (response.data.user) {
        setUser(response.data.user);
      }
      
      return { 
        success: true, 
        user: response.data.user 
      };
      
    } catch (error) {
      console.error('❌ AuthContext: Login error:', error);
      
      let errorMessage = 'Login failed. Please check your credentials.';
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      return { 
        success: false, 
        error: errorMessage 
      };
    }
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
  };

  const value = {
    user,
    loading,
    signup,
    login,
    logout,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};