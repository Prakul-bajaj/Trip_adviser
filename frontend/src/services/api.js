// frontend/src/services/api.js - COMPREHENSIVE FIX

import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // ✅ FIX: Only use withCredentials if you're using cookies for auth
  // Remove this if using JWT tokens in localStorage
  withCredentials: false, // Change to true only if backend sends cookies
});

// Add token to requests - BUT NOT for login/register
api.interceptors.request.use(
  (config) => {
    // ✅ FIX: More comprehensive auth request detection
    const isAuthRequest = config.url?.includes('/login') || 
                         config.url?.includes('/register') ||
                         config.url?.includes('/signup') ||
                         config.url?.includes('/auth');
    
    if (!isAuthRequest) {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log('🔑 Added token to request:', config.url);
      }
    } else {
      console.log('🚫 Skipping token for auth request:', config.url);
    }
    
    return config;
  },
  (error) => {
    console.error('❌ Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Handle response errors
api.interceptors.response.use(
  (response) => {
    console.log('✅ Response success:', response.config.url);
    return response;
  },
  (error) => {
    // ✅ FIX: Better error logging
    if (error.response) {
      console.error('❌ Response error:', {
        url: error.config?.url,
        status: error.response.status,
        data: error.response.data,
        headers: error.response.headers
      });
    } else if (error.request) {
      console.error('❌ No response received:', error.request);
    } else {
      console.error('❌ Request setup error:', error.message);
    }
    
    if (error.response?.status === 401) {
      const publicPaths = ['/login', '/signup', '/register'];
      const currentPath = window.location.pathname;
      const requestUrl = error.config?.url || '';
      
      const isAuthRequest = requestUrl.includes('/login') || 
                          requestUrl.includes('/register') ||
                          requestUrl.includes('/signup');
      
      // Only redirect if NOT on auth pages and NOT an auth request
      if (!publicPaths.includes(currentPath) && !isAuthRequest) {
        console.log('🚪 401 Unauthorized - redirecting to login');
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

// Auth endpoints
export const authAPI = {
  login: async (credentials) => {
    try {
      console.log('🔐 Attempting login:', { 
        email: credentials.email,
        endpoint: '/users/login/'
      });
      
      const response = await api.post('/users/login/', {
        email: credentials.email,
        password: credentials.password
      });
      
      console.log('✅ Login response:', {
        status: response.status,
        hasToken: !!(response.data.access || response.data.token),
        hasUser: !!response.data.user
      });
      
      // ✅ FIX: Standardized token extraction
      const token = response.data.access || 
                   response.data.token || 
                   response.data.access_token;
      
      if (!token) {
        console.error('❌ No token in login response:', response.data);
        throw new Error('No authentication token received');
      }
      
      localStorage.setItem('token', token);
      console.log('✅ Token saved to localStorage');
      
      // Save user data
      if (response.data.user) {
        localStorage.setItem('user', JSON.stringify(response.data.user));
        console.log('✅ User data saved:', response.data.user.email);
      } else {
        console.warn('⚠️ No user data in response');
      }
      
      return response;
      
    } catch (error) {
      console.error('❌ Login failed:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });
      throw error;
    }
  },
  
  signup: async (userData) => {
    try {
      console.log('📝 Attempting signup:', {
        email: userData.email,
        name: userData.name,
        endpoint: '/users/register/'
      });
      
      // ✅ FIX: Split name into first_name and last_name
      const nameParts = (userData.name || '').trim().split(' ');
      const firstName = nameParts[0] || '';
      const lastName = nameParts.slice(1).join(' ') || '';
      
      // ✅ FIX: Include password_confirm (required by Django serializer)
      const signupData = {
        email: userData.email,
        password: userData.password,
        password_confirm: userData.password_confirm || userData.password, // ⬅️ KEY FIX!
        first_name: firstName,
        last_name: lastName,
        username: userData.username || userData.email.split('@')[0], // Optional: use email prefix
      };
      
      console.log('📤 Sending signup data:', {
        email: signupData.email,
        first_name: signupData.first_name,
        last_name: signupData.last_name,
        username: signupData.username,
        hasPassword: !!signupData.password,
        hasPasswordConfirm: !!signupData.password_confirm
      });
      
      const response = await api.post('/users/register/', signupData);
      
      console.log('✅ Signup response:', {
        status: response.status,
        hasToken: !!(response.data.access || response.data.token),
        hasUser: !!response.data.user
      });
      
      // ✅ FIX: Standardized token extraction
      const token = response.data.access || 
                   response.data.token || 
                   response.data.access_token;
      
      if (token) {
        localStorage.setItem('token', token);
        console.log('✅ Token saved after signup');
      } else {
        console.warn('⚠️ No token in signup response - user may need to login');
      }
      
      if (response.data.user) {
        localStorage.setItem('user', JSON.stringify(response.data.user));
        console.log('✅ User data saved:', response.data.user.email);
      }
      
      return response;
      
    } catch (error) {
      console.error('❌ Signup failed:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        validationErrors: error.response?.data?.errors || error.response?.data
      });
      
      // ✅ FIX: Provide detailed error message
      if (error.response?.data) {
        const errorData = error.response.data;
        
        // Extract meaningful error messages
        let errorMessage = 'Signup failed. ';
        
        if (errorData.email) {
          errorMessage += `Email: ${Array.isArray(errorData.email) ? errorData.email[0] : errorData.email}. `;
        }
        if (errorData.password) {
          errorMessage += `Password: ${Array.isArray(errorData.password) ? errorData.password[0] : errorData.password}. `;
        }
        if (errorData.name) {
          errorMessage += `Name: ${Array.isArray(errorData.name) ? errorData.name[0] : errorData.name}. `;
        }
        if (errorData.detail) {
          errorMessage += errorData.detail;
        }
        if (errorData.message) {
          errorMessage += errorData.message;
        }
        
        // If no specific errors found, use generic message
        if (errorMessage === 'Signup failed. ') {
          errorMessage = errorData.non_field_errors || 
                        JSON.stringify(errorData);
        }
        
        error.message = errorMessage;
      }
      
      throw error;
    }
  },
  
  logout: async () => {
    try {
      const token = localStorage.getItem('token');
      
      if (token) {
        await api.post('/users/logout/', {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
      }
      
      console.log('✅ Logged out successfully');
      
    } catch (error) {
      console.error('❌ Logout error:', error.message);
      // Continue with local cleanup even if server logout fails
      
    } finally {
      // Always clean up local storage
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      console.log('🧹 Local auth data cleared');
    }
  },
  
  getCurrentUser: async () => {
    try {
      const response = await api.get('/users/me/');
      console.log('✅ Got current user:', response.data.email);
      return response;
    } catch (error) {
      console.error('❌ Get current user failed:', error.message);
      throw error;
    }
  },
  
  isAuthenticated: () => {
    const token = localStorage.getItem('token');
    const isAuth = !!token;
    console.log('🔍 Checking auth status:', isAuth);
    return isAuth;
  },
};

// Chat endpoints
export const chatAPI = {
  getConversations: () => {
    console.log('📋 Fetching conversations');
    return api.get('/chatbot/sessions/');
  },
  
  getConversation: (id) => {
    console.log('📋 Fetching conversation:', id);
    return api.get(`/chatbot/sessions/${id}/`);
  },
  
  getMessages: (sessionId) => {
    console.log('💬 Fetching messages for session:', sessionId);
    return api.get(`/chatbot/sessions/${sessionId}/messages/`);
  },
  
  createConversation: (title = 'New Chat') => {
    console.log('➕ Creating conversation:', title);
    return api.post('/chatbot/sessions/', { title });
  },
  
  updateConversation: (id, data) => {
    console.log('✏️ Updating conversation:', id);
    return api.patch(`/chatbot/sessions/${id}/`, data);
  },
  
  sendMessage: (conversationId, message) => {
    console.log('📤 Sending message to session:', conversationId);
    return api.post(`/chatbot/sessions/${conversationId}/messages/`, { 
      message: message,
      content: message,
    });
  },
  
  deleteConversation: (id) => {
    console.log('🗑️ Deleting conversation:', id);
    return api.delete(`/chatbot/sessions/${id}/`);
  },
  
  chat: (message, sessionId = null) => {
    console.log('💬 Sending chat message:', { 
      messageLength: message.length,
      hasSession: !!sessionId 
    });
    return api.post('/chatbot/chat/', { 
      message, 
      session_id: sessionId 
    });
  },
  
  sendFeedback: (data) => {
    console.log('👍 Sending feedback');
    return api.post('/chatbot/feedback/', data);
  },
};

// Destinations endpoints
export const destinationsAPI = {
  getDestinations: (params) => api.get('/destinations/', { params }),
  getDestination: (id) => api.get(`/destinations/${id}/`),
  searchDestinations: (query) => api.get(`/destinations/search/?q=${query}`),
  getByExperience: (type) => api.get(`/destinations/experience/${type}/`),
  getByGeography: (type) => api.get(`/destinations/geography/${type}/`),
  getByLandscape: (type) => api.get(`/destinations/landscape/${type}/`),
  getSpiritualDestinations: () => api.get('/destinations/spiritual/'),
  saveDestination: (id) => api.post(`/destinations/${id}/save/`),
  unsaveDestination: (id) => api.post(`/destinations/${id}/unsave/`),
  getSavedDestinations: () => api.get('/destinations/saved/'),
};

// Recommendations endpoints
export const recommendationsAPI = {
  getRecommendations: (preferences) => 
    api.post('/recommendations/', preferences),
  getDestinations: () => api.get('/recommendations/destinations/'),
  searchDestinations: (query) => 
    api.get('/recommendations/search/', { params: { q: query } }),
  getPopularDestinations: () => api.get('/recommendations/popular/'),
};

// Weather endpoints
export const weatherAPI = {
  getCurrentWeather: (destinationId) => 
    api.get(`/weather/weather/${destinationId}/`),
  getWeatherForecast: (destinationId) => 
    api.get(`/weather/weather/${destinationId}/forecast/`),
  getSeasonalRecommendation: (destinationId) => 
    api.get(`/weather/weather/${destinationId}/seasonal/`),
  checkWeatherSuitability: (data) => 
    api.post('/weather/weather/check-suitability/', data),
};

export default api;