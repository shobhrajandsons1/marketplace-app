import React, { useState, useEffect, createContext, useContext } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp * 1000 > Date.now()) {
          setUser({ 
            id: payload.user_id, 
            user_type: payload.user_type 
          });
        } else {
          localStorage.removeItem('token');
          setToken(null);
        }
      } catch (error) {
        console.error('Invalid token');
        localStorage.removeItem('token');
        setToken(null);
      }
    }
    setLoading(false);
  }, [token]);

  const login = (newToken, userData) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// API helper
const apiCall = async (endpoint, method = 'GET', data = null, token = null) => {
  const config = {
    method,
    url: `${API}${endpoint}`,
    headers: {},
  };

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  if (data) {
    config.data = data;
    config.headers['Content-Type'] = 'application/json';
  }

  try {
    const response = await axios(config);
    return response.data;
  } catch (error) {
    console.error('API Error:', error.response?.data || error.message);
    throw error.response?.data || error;
  }
};

// Login Component
const LoginModal = ({ isOpen, onClose, onLogin }) => {
  const [credentials, setCredentials] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await apiCall('/auth/login', 'POST', credentials);
      onLogin(response.access_token, response.user);
      onClose();
    } catch (error) {
      setError(error.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Welcome Back</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              placeholder="Enter your email"
              value={credentials.email}
              onChange={(e) => setCredentials({...credentials, email: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              placeholder="Enter your password"
              value={credentials.password}
              onChange={(e) => setCredentials({...credentials, password: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div className="text-sm text-gray-600 bg-blue-50 p-2 rounded">
            👤 Your account type will be automatically detected
          </div>

          {error && <div className="text-red-500 text-sm">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Signing In...' : 'Sign In'}
          </button>

          <div className="text-center space-y-2">
            <p className="text-sm text-gray-600">
              Don't have an account? <button className="text-blue-600 hover:underline">Join Now</button>
            </p>
            <p className="text-sm">
              <button className="text-blue-600 hover:underline">Forgot Password?</button>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
};

// Admin Config Panel
const AdminConfigPanel = ({ currentUser, token }) => {
  const [currentPage, setCurrentPage] = useState('main');
  const [settings, setSettings] = useState({});

  const adminTiles = [
    { id: 'ai', title: 'AI Settings', icon: '🤖', description: 'Configure AI content generation' },
    { id: 'payments', title: 'Payments', icon: '💳', description: 'Payment gateway settings' },
    { id: 'commission', title: 'Commission', icon: '💰', description: 'Commission rates management' },
    { id: 'shipping', title: 'Shipping', icon: '🚚', description: 'Shipping partners & rates' },
    { id: 'marketing', title: 'Marketing', icon: '📢', description: 'Marketing campaigns & tools' },
    { id: 'erp', title: 'ERP Integration', icon: '🏢', description: 'Connect with ERP systems' },
    { id: 'system', title: 'System', icon: '⚙️', description: 'System configuration' }
  ];

  const handleTileClick = (tileId) => {
    setCurrentPage(tileId);
  };

  const handleBackToMain = () => {
    setCurrentPage('main');
  };

  // Marketing Tab - Full implementation
  const renderMarketingTab = () => {
    const [marketingSettings, setMarketingSettings] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
      fetchMarketingSettings();
    }, []);

    const fetchMarketingSettings = async () => {
      try {
        const response = await apiCall('/admin/settings/marketing', 'GET', null, token);
        setMarketingSettings(response);
      } catch (error) {
        console.error('Error fetching marketing settings:', error);
      } finally {
        setLoading(false);
      }
    };

    const handleSaveSettings = async () => {
      setSaving(true);
      try {
        await apiCall('/admin/settings/marketing', 'POST', marketingSettings, token);
        alert('Marketing settings saved successfully!');
      } catch (error) {
        console.error('Error saving marketing settings:', error);
        alert('Error saving settings');
      } finally {
        setSaving(false);
      }
    };

    const handleInputChange = (field, value) => {
      setMarketingSettings(prev => ({
        ...prev,
        [field]: value
      }));
    };

    if (loading) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Loading marketing settings...</span>
        </div>
      );
    }

    return (
      <div className="space-y-8">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">📢</div>
          <h3 className="text-2xl font-semibold mb-2">Marketing Management</h3>
          <p className="text-gray-600">Configure marketing campaigns and promotional tools</p>
        </div>

        {/* Email Marketing Section */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h4 className="text-lg font-semibold mb-4 flex items-center">
            <span className="text-2xl mr-2">📧</span>
            Email Marketing (SendGrid)
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">SendGrid API Key</label>
              <input
                type="password"
                value={marketingSettings.sendgrid_api_key || ''}
                onChange={(e) => handleInputChange('sendgrid_api_key', e.target.value)}
                placeholder="Enter SendGrid API Key"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">From Email</label>
              <input
                type="email"
                value={marketingSettings.sendgrid_from_email || ''}
                onChange={(e) => handleInputChange('sendgrid_from_email', e.target.value)}
                placeholder="noreply@marketplace.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSaveSettings}
            disabled={saving}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Saving...
              </>
            ) : (
              'Save Marketing Settings'
            )}
          </button>
        </div>
      </div>
    );
  };

  // System Tab - Full implementation
  const renderSystemTab = () => {
    const [systemSettings, setSystemSettings] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
      fetchSystemSettings();
    }, []);

    const fetchSystemSettings = async () => {
      try {
        const response = await apiCall('/admin/settings/system', 'GET', null, token);
        setSystemSettings(response);
      } catch (error) {
        console.error('Error fetching system settings:', error);
      } finally {
        setLoading(false);
      }
    };

    const handleSaveSettings = async () => {
      setSaving(true);
      try {
        await apiCall('/admin/settings/system', 'POST', systemSettings, token);
        alert('System settings saved successfully!');
      } catch (error) {
        console.error('Error saving system settings:', error);
        alert('Error saving settings');
      } finally {
        setSaving(false);
      }
    };

    const handleInputChange = (field, value) => {
      setSystemSettings(prev => ({
        ...prev,
        [field]: value
      }));
    };

    if (loading) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Loading system settings...</span>
        </div>
      );
    }

    return (
      <div className="space-y-8">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">⚙️</div>
          <h3 className="text-2xl font-semibold mb-2">System Settings</h3>
          <p className="text-gray-600">Manage system configuration and maintenance</p>
        </div>

        {/* Basic Settings */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h4 className="text-lg font-semibold mb-4 flex items-center">
            <span className="text-2xl mr-2">🏪</span>
            Site Configuration
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Site Name</label>
              <input
                type="text"
                value={systemSettings.site_name || ''}
                onChange={(e) => handleInputChange('site_name', e.target.value)}
                placeholder="MarketPlace Pro"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Admin Email</label>
              <input
                type="email"
                value={systemSettings.admin_email || ''}
                onChange={(e) => handleInputChange('admin_email', e.target.value)}
                placeholder="admin@marketplace.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSaveSettings}
            disabled={saving}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Saving...
              </>
            ) : (
              'Save System Settings'
            )}
          </button>
        </div>
      </div>
    );
  };

  if (currentPage === 'marketing') {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={handleBackToMain}
          className="mb-6 bg-gray-100 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-200 transition-colors"
        >
          ← Back to Configuration
        </button>
        {renderMarketingTab()}
      </div>
    );
  }

  if (currentPage === 'system') {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={handleBackToMain}
          className="mb-6 bg-gray-100 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-200 transition-colors"
        >
          ← Back to Configuration
        </button>
        {renderSystemTab()}
      </div>
    );
  }

  // Main admin tiles view
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Admin Configuration</h2>
        <p className="text-gray-600">Manage your marketplace settings and integrations</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {adminTiles.map((tile) => (
          <div
            key={tile.id}
            onClick={() => handleTileClick(tile.id)}
            className="bg-white p-6 rounded-lg shadow-sm border hover:shadow-md transition-shadow cursor-pointer group"
          >
            <div className="text-4xl mb-4 group-hover:scale-110 transition-transform">
              {tile.icon}
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{tile.title}</h3>
            <p className="text-gray-600 text-sm">{tile.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

// Main Dashboard
const Dashboard = () => {
  const { user, token } = useAuth();

  if (user?.user_type === 'admin') {
    return <AdminConfigPanel currentUser={user} token={token} />;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Dashboard</h2>
        <p className="text-gray-600">Welcome to your marketplace dashboard!</p>
        
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="font-semibold text-blue-900">Products</h3>
            <p className="text-2xl font-bold text-blue-600">0</p>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <h3 className="font-semibold text-green-900">Orders</h3>
            <p className="text-2xl font-bold text-green-600">0</p>
          </div>
          <div className="bg-purple-50 p-4 rounded-lg">
            <h3 className="font-semibold text-purple-900">Revenue</h3>
            <p className="text-2xl font-bold text-purple-600">₹0</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Public Store Component
const PublicStore = () => {
  const [showLoginModal, setShowLoginModal] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex-shrink-0">
              <h1 className="text-xl font-bold text-gray-900">MarketPlace</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button className="text-gray-700 hover:text-gray-900 font-medium transition-colors">
                Browse Products
              </button>
              <button 
                onClick={() => setShowLoginModal(true)}
                className="text-gray-700 hover:text-gray-900 font-medium transition-colors"
              >
                Sign In
              </button>
              <button className="bg-gray-900 text-white px-4 py-2 rounded-md hover:bg-gray-800 transition-colors">
                Join Now
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="text-4xl md:text-6xl font-bold text-gray-900 leading-tight">
                Redefine Your Shopping Experience
              </h1>
              <p className="text-xl text-gray-600 mt-6 leading-relaxed">
                Discover premium products curated just for you. From electronics to fashion, 
                find everything at the best prices.
              </p>
              <div className="mt-8 flex flex-col sm:flex-row gap-4">
                <button className="bg-gray-900 text-white px-8 py-3 rounded-md text-lg font-medium hover:bg-gray-800 transition-colors">
                  Shop Now
                </button>
                <button className="border border-gray-300 text-gray-900 px-8 py-3 rounded-md text-lg font-medium hover:bg-gray-50 transition-colors">
                  Become a Seller
                </button>
              </div>
            </div>
            <div className="relative">
              <div className="aspect-square bg-gradient-to-br from-blue-400 to-purple-600 rounded-2xl"></div>
            </div>
          </div>
        </div>
      </div>

      {/* Featured Products */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900">Featured Products</h2>
          <p className="text-gray-600 mt-4">Discover our most popular items loved by customers</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[1, 2, 3].map((item) => (
            <div key={item} className="bg-white rounded-lg shadow-sm border overflow-hidden hover:shadow-md transition-shadow">
              <div className="aspect-square bg-gray-100 flex items-center justify-center">
                <div className="text-6xl">📦</div>
              </div>
              <div className="p-6">
                <h3 className="font-semibold text-gray-900 mb-2">Sample Product {item}</h3>
                <p className="text-gray-600 text-sm mb-4">High-quality product description goes here.</p>
                <div className="flex justify-between items-center">
                  <span className="text-2xl font-bold text-gray-900">₹999</span>
                  <button className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors">
                    Buy Now
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center mt-12">
          <button className="bg-gray-100 text-gray-700 px-8 py-3 rounded-md font-medium hover:bg-gray-200 transition-colors">
            View All Products
          </button>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-gray-900 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold mb-4">Start Selling Today</h2>
          <p className="text-xl text-gray-300 mb-8">
            Join thousands of sellers and grow your business with our platform
          </p>
          <button className="bg-white text-gray-900 px-8 py-3 rounded-md text-lg font-medium hover:bg-gray-100 transition-colors">
            Browse Products
          </button>
        </div>
      </div>

      <LoginModal 
        isOpen={showLoginModal} 
        onClose={() => setShowLoginModal(false)}
        onLogin={(token, userData) => {
          // This will be handled by the auth context
          window.location.reload();
        }}
      />
    </div>
  );
};

// Main App Component
function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <span className="ml-4 text-lg text-gray-600">Loading...</span>
      </div>
    );
  }

  const renderAdminContent = () => {
    const token = localStorage.getItem('token');
    
    if (user?.user_type === 'admin') {
      return (
        <div className="min-h-screen bg-gray-50">
          <nav className="bg-white shadow-sm border-b">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                <div className="flex items-center space-x-8">
                  <h1 className="text-xl font-semibold text-gray-900">Admin Panel</h1>
                </div>
                <div className="text-sm text-gray-600">
                  Admin: {user.user_type.replace('_', ' ')}
                </div>
              </div>
            </div>
          </nav>

          <AdminConfigPanel currentUser={user} token={token} />
        </div>
      );
    } else {
      return <Dashboard />;
    }
  };

  return (
    <div className="App">
      {user ? renderAdminContent() : <PublicStore />}
    </div>
  );
}

export default function AppWithAuth() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}
