// App.js - Fixed layout structure

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { authAPI } from './services/api';

// Components
import Navbar from './components/Layout/Navbar';
import Login from './components/Auth/Login';
import Signup from './components/Auth/Signup';
import ChatInterface from './components/Chat/ChatInterface';

// Add global styles
import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const isAuthenticated = authAPI.isAuthenticated();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

// Layout with Navbar
const LayoutWithNavbar = ({ children }) => (
  <div className="app-layout">
    <Navbar />
    <div className="app-content">
      {children}
    </div>
  </div>
);

// Layout without Navbar (for auth pages)
const AuthLayout = ({ children }) => (
  <div style={{ height: '100vh', overflow: 'hidden' }}>
    {children}
  </div>
);

// Chat Layout (full screen, no navbar)
const ChatLayout = ({ children }) => (
  <div className="chat-page">
    {children}
  </div>
);

function App() {
  return (
    <Router>
      <Routes>
        {/* Auth Routes - No Navbar */}
        <Route path="/login" element={
          <AuthLayout>
            <Login />
          </AuthLayout>
        } />
        
        <Route path="/signup" element={
          <AuthLayout>
            <Signup />
          </AuthLayout>
        } />
        
        {/* Chat Route - Full Screen with Navbar on top */}
        <Route path="/chat/*" element={
          <ProtectedRoute>
            <LayoutWithNavbar>
              <Routes>
                <Route path="/" element={<ChatInterface />} />
                <Route path="/:conversationId" element={<ChatInterface />} />
              </Routes>
            </LayoutWithNavbar>
          </ProtectedRoute>
        } />
        
        {/* Other routes with Navbar */}
        <Route path="/" element={
          <ProtectedRoute>
            <LayoutWithNavbar>
              <Navigate to="/chat" replace />
            </LayoutWithNavbar>
          </ProtectedRoute>
        } />
        
        {/* Add other routes here as needed */}
      </Routes>
    </Router>
  );
}

export default App;