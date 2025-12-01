import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle response errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth endpoints
export const authAPI = {
  login: (credentials) => api.post('/users/login/', credentials),
  signup: (userData) => api.post('/users/register/', userData),
  logout: () => api.post('/users/logout/'),
  getCurrentUser: () => api.get('/users/me/'),
};

// Chat endpoints
export const chatAPI = {
  getConversations: () => api.get('/chatbot/conversations/'),
  getConversation: (id) => api.get(`/chatbot/conversations/${id}/`),
  createConversation: () => api.post('/chatbot/conversations/'),
  sendMessage: (conversationId, message) => 
    api.post(`/chatbot/conversations/${conversationId}/messages/`, { message }),
  deleteConversation: (id) => api.delete(`/chatbot/conversations/${id}/`),
};

// Destinations endpoints
export const destinationsAPI = {
  getDestinations: (params) => api.get('/destinations/', { params }),
  getDestination: (id) => api.get(`/destinations/${id}/`),
  searchDestinations: (query) => api.get(`/destinations/search/?q=${query}`),
};

// Recommendations endpoints
export const recommendationsAPI = {
  getRecommendations: (preferences) => 
    api.post('/recommendations/', preferences),
};

export default api;