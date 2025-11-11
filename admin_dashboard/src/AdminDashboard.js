import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import './AdminDashboard.css';

// API Configuration
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function AdminDashboard() {
  // Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');

  // Dashboard state
  const [stats, setStats] = useState({
    total_feedback: 0,
    positive_count: 0,
    negative_count: 0,
    positive_percentage: 0
  });
  const [feedbackData, setFeedbackData] = useState([]);
  const [dailyData, setDailyData] = useState([]);
  const [loading, setLoading] = useState(false);

  // Filter state
  const [ratingFilter, setRatingFilter] = useState('All');
  const [daysFilter, setDaysFilter] = useState(7);
  const [searchQuery, setSearchQuery] = useState('');

  // Check if already authenticated
  useEffect(() => {
    const token = localStorage.getItem('admin_authenticated');
    if (token === 'true') {
      setIsAuthenticated(true);
      fetchDashboardData();
    }
  }, []);

  // Handle login
  const handleLogin = (e) => {
    e.preventDefault();
    const correctPassword = process.env.REACT_APP_DASHBOARD_PASSWORD || 'ironlady2024';
    
    if (password === correctPassword) {
      localStorage.setItem('admin_authenticated', 'true');
      setIsAuthenticated(true);
      setAuthError('');
      fetchDashboardData();
    } else {
      setAuthError('Incorrect password');
    }
  };

  // Handle logout
  const handleLogout = () => {
    localStorage.removeItem('admin_authenticated');
    setIsAuthenticated(false);
    setPassword('');
  };

  // Fetch all dashboard data
  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // Fetch stats
      const statsRes = await fetch(`${API_URL}/api/feedback/stats`);
      const statsData = await statsRes.json();
      setStats(statsData);

      // Fetch recent feedback
      const feedbackRes = await fetch(`${API_URL}/api/feedback/recent?limit=50`);
      const feedbackJson = await feedbackRes.json();
      setFeedbackData(feedbackJson.feedback || []);

      // Process daily data for chart
      processDailyData(feedbackJson.feedback || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    }
    setLoading(false);
  };

  // Process data for daily chart
  const processDailyData = (feedback) => {
    const grouped = {};
    
    feedback.forEach(item => {
      const date = new Date(item.timestamp).toLocaleDateString();
      if (!grouped[date]) {
        grouped[date] = { date, count: 0 };
      }
      grouped[date].count++;
    });

    const chartData = Object.values(grouped).sort((a, b) => 
      new Date(a.date) - new Date(b.date)
    );
    
    setDailyData(chartData);
  };

  // Filter feedback data
  const getFilteredFeedback = () => {
    let filtered = [...feedbackData];

    // Filter by rating
    if (ratingFilter !== 'All') {
      filtered = filtered.filter(f => f.rating === ratingFilter.toLowerCase());
    }

    // Filter by days
    const daysAgo = new Date();
    daysAgo.setDate(daysAgo.getDate() - daysFilter);
    filtered = filtered.filter(f => new Date(f.timestamp) >= daysAgo);

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter(f =>
        f.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.answer.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    return filtered;
  };

  // Export to CSV
  const exportToCSV = () => {
    const filtered = getFilteredFeedback();
    const headers = ['Timestamp', 'Session ID', 'Question', 'Answer', 'Rating'];
    const rows = filtered.map(f => [
      new Date(f.timestamp).toISOString(),
      f.session_id,
      `"${f.question.replace(/"/g, '""')}"`,
      `"${f.answer.replace(/"/g, '""')}"`,
      f.rating
    ]);

    const csv = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `feedback_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  // Login screen
  if (!isAuthenticated) {
    return (
      <div className="login-container">
        <div className="login-box">
          <div className="login-header">
            <h1>🔐 Admin Dashboard Login</h1>
            <p>100BM AI Assistant - Feedback Analytics</p>
          </div>
          <form onSubmit={handleLogin}>
            <input
              type="password"
              placeholder="Enter password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="login-input"
            />
            {authError && <p className="error-message">{authError}</p>}
            <button type="submit" className="login-button">
              Login
            </button>
            <p className="login-hint">Default password: ironlady2024</p>
          </form>
        </div>
      </div>
    );
  }

  // Dashboard screen
  const filteredData = getFilteredFeedback();
  const pieData = [
    { name: 'Positive 👍', value: stats.positive_count, color: '#4CAF50' },
    { name: 'Negative 👎', value: stats.negative_count, color: '#f44336' }
  ];

  return (
    <div className="admin-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h1>📊 100BM AI Assistant - Feedback Dashboard</h1>
          <p>Monitor and analyze chatbot performance through user feedback</p>
        </div>
        <button onClick={handleLogout} className="logout-button">
          🚪 Logout
        </button>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">📈 Total Feedback</div>
          <div className="stat-value">{stats.total_feedback}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">👍 Positive</div>
          <div className="stat-value">{stats.positive_count}</div>
          <div className="stat-delta positive">{stats.positive_percentage.toFixed(1)}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">👎 Negative</div>
          <div className="stat-value">{stats.negative_count}</div>
          <div className="stat-delta negative">{(100 - stats.positive_percentage).toFixed(1)}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">✅ Satisfaction Rate</div>
          <div className="stat-value">{stats.positive_percentage.toFixed(1)}%</div>
        </div>
      </div>

      {/* Charts */}
      <div className="charts-grid">
        <div className="chart-container">
          <h3>📊 Feedback Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h3>📅 Feedback Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="count" 
                stroke="#C41E3A" 
                strokeWidth={2}
                name="Feedback Count"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-section">
        <h3>🔍 Filter Feedback</h3>
        <div className="filters-grid">
          <div className="filter-item">
            <label>Rating</label>
            <select 
              value={ratingFilter} 
              onChange={(e) => setRatingFilter(e.target.value)}
              className="filter-select"
            >
              <option>All</option>
              <option>Positive</option>
              <option>Negative</option>
            </select>
          </div>
          <div className="filter-item">
            <label>Last N Days</label>
            <input
              type="range"
              min="1"
              max="30"
              value={daysFilter}
              onChange={(e) => setDaysFilter(parseInt(e.target.value))}
              className="filter-slider"
            />
            <span>{daysFilter} days</span>
          </div>
          <div className="filter-item">
            <label>Search</label>
            <input
              type="text"
              placeholder="Search questions/answers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="filter-input"
            />
          </div>
        </div>
      </div>

      {/* Feedback Table */}
      <div className="feedback-section">
        <div className="section-header">
          <h3>📋 Recent Feedback ({filteredData.length} items)</h3>
          <div className="action-buttons">
            <button onClick={fetchDashboardData} className="refresh-button">
              🔄 Refresh
            </button>
            <button onClick={exportToCSV} className="export-button">
              📥 Export CSV
            </button>
          </div>
        </div>

        {loading ? (
          <div className="loading">Loading...</div>
        ) : filteredData.length === 0 ? (
          <div className="no-data">
            📭 No feedback data available. Try adjusting your filters.
          </div>
        ) : (
          <div className="feedback-list">
            {filteredData.map((feedback, index) => (
              <div key={index} className="feedback-item">
                <div className="feedback-header">
                  <span className={`rating-badge ${feedback.rating}`}>
                    {feedback.rating === 'positive' ? '👍 Positive' : '👎 Negative'}
                  </span>
                  <span className="feedback-time">
                    {new Date(feedback.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="feedback-content">
                  <div className="feedback-question">
                    <strong>Question:</strong>
                    <p>{feedback.question}</p>
                  </div>
                  <div className="feedback-answer">
                    <strong>Answer:</strong>
                    <p>{feedback.answer.substring(0, 300)}{feedback.answer.length > 300 ? '...' : ''}</p>
                  </div>
                </div>
                <div className="feedback-meta">
                  <span>Session: {feedback.session_id.substring(0, 20)}...</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="dashboard-footer">
        <p>100BM AI Assistant - Admin Dashboard | Iron Lady Leadership Program</p>
        <p>Last updated: {new Date().toLocaleString()}</p>
      </div>
    </div>
  );
}

export default AdminDashboard;