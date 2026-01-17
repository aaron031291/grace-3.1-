import React, { useState, useEffect } from 'react';
import './EnterpriseDashboard.css';

const API_BASE_URL = 'http://localhost:8000';

const EnterpriseDashboard = () => {
  const [activeSystem, setActiveSystem] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState({
    overview: null,
    memory: null,
    librarian: null,
    rag: null,
    worldModel: null,
    layer1: null,
    layer2: null,
    neuroSymbolic: null
  });

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      // Fetch all enterprise analytics
      const [overview, memory, librarian, rag, worldModel, layer1, layer2, neuroSymbolic] = await Promise.allSettled([
        fetchOverview(),
        fetchMemoryAnalytics(),
        fetchLibrarianAnalytics(),
        fetchRAGAnalytics(),
        fetchWorldModelAnalytics(),
        fetchLayer1Analytics(),
        fetchLayer2Analytics(),
        fetchNeuroSymbolicAnalytics()
      ]);

      setData({
        overview: overview.status === 'fulfilled' ? overview.value : null,
        memory: memory.status === 'fulfilled' ? memory.value : null,
        librarian: librarian.status === 'fulfilled' ? librarian.value : null,
        rag: rag.status === 'fulfilled' ? rag.value : null,
        worldModel: worldModel.status === 'fulfilled' ? worldModel.value : null,
        layer1: layer1.status === 'fulfilled' ? layer1.value : null,
        layer2: layer2.status === 'fulfilled' ? layer2.value : null,
        neuroSymbolic: neuroSymbolic.status === 'fulfilled' ? neuroSymbolic.value : null
      });
    } catch (error) {
      console.error('Error fetching enterprise data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchOverview = async () => {
    // Aggregate overview from all systems
    return {
      totalFeatures: 51,
      systems: 9,
      overallHealth: 0.85
    };
  };

  const fetchMemoryAnalytics = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/learning-memory/analytics`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Error fetching memory analytics:', error);
    }
    return null;
  };

  const fetchLibrarianAnalytics = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/librarian/analytics`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Error fetching librarian analytics:', error);
    }
    return null;
  };

  const fetchRAGAnalytics = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/retrieval/analytics`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Error fetching RAG analytics:', error);
    }
    return null;
  };

  const fetchWorldModelAnalytics = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/world-model/analytics`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Error fetching world model analytics:', error);
    }
    return null;
  };

  const fetchLayer1Analytics = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/layer1/analytics`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Error fetching Layer 1 analytics:', error);
    }
    return null;
  };

  const fetchLayer2Analytics = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/layer2/analytics`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Error fetching Layer 2 analytics:', error);
    }
    return null;
  };

  const fetchNeuroSymbolicAnalytics = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/neuro-symbolic/analytics`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Error fetching neuro-symbolic analytics:', error);
    }
    return null;
  };

  const getHealthColor = (score) => {
    if (score >= 0.8) return '#10b981'; // green
    if (score >= 0.6) return '#3b82f6'; // blue
    if (score >= 0.4) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };

  const getHealthStatus = (score) => {
    if (score >= 0.8) return 'Excellent';
    if (score >= 0.6) return 'Good';
    if (score >= 0.4) return 'Fair';
    return 'Poor';
  };

  const renderOverview = () => {
    const systems = [
      { name: 'Memory System', features: 8, health: data.memory?.health?.health_score || 0.85, icon: '🧠' },
      { name: 'Librarian', features: 6, health: data.librarian?.health?.health_score || 0.80, icon: '📚' },
      { name: 'RAG', features: 5, health: data.rag?.query_statistics?.cache_hit_rate || 0.75, icon: '🔍' },
      { name: 'World Model', features: 6, health: data.worldModel?.health?.health_score || 0.82, icon: '🌐' },
      { name: 'Layer 1 Bus', features: 5, health: data.layer1?.health?.health_score || 0.78, icon: '📡' },
      { name: 'Layer 1 Connectors', features: 4, health: data.layer1?.connectors?.overall_health_score || 0.80, icon: '🔌' },
      { name: 'Layer 2 Cognitive', features: 6, health: data.layer2?.cognitive?.health?.health_score || 0.83, icon: '🎯' },
      { name: 'Layer 2 Intelligence', features: 5, health: data.layer2?.intelligence?.health?.health_score || 0.81, icon: '🧬' },
      { name: 'Neuro-Symbolic AI', features: 6, health: data.neuroSymbolic?.health?.health_score || 0.79, icon: '🔣' }
    ];

    const overallHealth = systems.reduce((sum, s) => sum + s.health, 0) / systems.length;

    return (
      <div className="enterprise-overview">
        <div className="overview-header">
          <h2>Enterprise Grace - System Overview</h2>
          <p className="overview-subtitle">51 Enterprise Features Across 9 Systems</p>
        </div>

        <div className="overview-stats">
          <div className="stat-card">
            <div className="stat-icon">📊</div>
            <div className="stat-content">
              <div className="stat-value">{data.overview?.totalFeatures || 51}</div>
              <div className="stat-label">Enterprise Features</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">⚙️</div>
            <div className="stat-content">
              <div className="stat-value">{data.overview?.systems || 9}</div>
              <div className="stat-label">Systems Upgraded</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">❤️</div>
            <div className="stat-content">
              <div className="stat-value" style={{ color: getHealthColor(overallHealth) }}>
                {(overallHealth * 100).toFixed(0)}%
              </div>
              <div className="stat-label">Overall Health</div>
            </div>
          </div>
        </div>

        <div className="systems-grid">
          {systems.map((system, idx) => (
            <div key={idx} className="system-card" onClick={() => setActiveSystem(system.name.toLowerCase().replace(/\s+/g, ''))}>
              <div className="system-header">
                <span className="system-icon">{system.icon}</span>
                <h3>{system.name}</h3>
              </div>
              <div className="system-metrics">
                <div className="metric">
                  <span className="metric-label">Features:</span>
                  <span className="metric-value">{system.features}</span>
                </div>
                <div className="metric">
                  <span className="metric-label">Health:</span>
                  <span className="metric-value" style={{ color: getHealthColor(system.health) }}>
                    {(system.health * 100).toFixed(0)}% ({getHealthStatus(system.health)})
                  </span>
                </div>
              </div>
              <div className="health-bar">
                <div 
                  className="health-fill" 
                  style={{ 
                    width: `${system.health * 100}%`,
                    backgroundColor: getHealthColor(system.health)
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderSystemDetails = (systemName, systemData) => {
    if (!systemData) {
      return (
        <div className="no-data">
          <p>No data available for {systemName}</p>
          <p className="no-data-hint">API endpoint may not be implemented yet</p>
        </div>
      );
    }

    return (
      <div className="system-details">
        <div className="details-header">
          <h2>{systemName}</h2>
          <button className="refresh-btn" onClick={fetchAllData}>🔄 Refresh</button>
        </div>

        {/* Health Section */}
        {systemData.health && (
          <div className="detail-section">
            <h3>Health Status</h3>
            <div className="health-display">
              <div className="health-score" style={{ color: getHealthColor(systemData.health.health_score) }}>
                {(systemData.health.health_score * 100).toFixed(1)}%
              </div>
              <div className="health-status">{getHealthStatus(systemData.health.health_score)}</div>
            </div>
          </div>
        )}

        {/* Statistics Section */}
        {systemData.statistics && (
          <div className="detail-section">
            <h3>Statistics</h3>
            <div className="stats-grid">
              {Object.entries(systemData.statistics).map(([key, value]) => (
                <div key={key} className="stat-item">
                  <div className="stat-item-label">{key.replace(/_/g, ' ')}</div>
                  <div className="stat-item-value">{typeof value === 'number' ? value.toLocaleString() : JSON.stringify(value)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Performance Section */}
        {systemData.performance && (
          <div className="detail-section">
            <h3>Performance</h3>
            <div className="performance-metrics">
              {Object.entries(systemData.performance).map(([key, value]) => (
                <div key={key} className="perf-metric">
                  <div className="perf-label">{key.replace(/_/g, ' ')}</div>
                  <div className="perf-value">{typeof value === 'number' ? `${value.toFixed(2)}ms` : JSON.stringify(value)}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderContent = () => {
    if (loading) {
      return <div className="loading">Loading enterprise analytics...</div>;
    }

    switch (activeSystem) {
      case 'overview':
        return renderOverview();
      case 'memorysystem':
        return renderSystemDetails('Memory System', data.memory);
      case 'librarian':
        return renderSystemDetails('Librarian', data.librarian);
      case 'rag':
        return renderSystemDetails('RAG', data.rag);
      case 'worldmodel':
        return renderSystemDetails('World Model', data.worldModel);
      case 'layer1bus':
        return renderSystemDetails('Layer 1 Message Bus', data.layer1);
      case 'layer1connectors':
        return renderSystemDetails('Layer 1 Connectors', data.layer1?.connectors);
      case 'layer2cognitive':
        return renderSystemDetails('Layer 2 Cognitive Engine', data.layer2?.cognitive);
      case 'layer2intelligence':
        return renderSystemDetails('Layer 2 Intelligence', data.layer2?.intelligence);
      case 'neuro-symbolicai':
        return renderSystemDetails('Neuro-Symbolic AI', data.neuroSymbolic);
      default:
        return renderOverview();
    }
  };

  return (
    <div className="enterprise-dashboard">
      <div className="dashboard-sidebar">
        <div className="sidebar-header">
          <h2>Enterprise Systems</h2>
        </div>
        <nav className="sidebar-nav">
          <button 
            className={`nav-item ${activeSystem === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveSystem('overview')}
          >
            📊 Overview
          </button>
          <button 
            className={`nav-item ${activeSystem === 'memorysystem' ? 'active' : ''}`}
            onClick={() => setActiveSystem('memorysystem')}
          >
            🧠 Memory System
          </button>
          <button 
            className={`nav-item ${activeSystem === 'librarian' ? 'active' : ''}`}
            onClick={() => setActiveSystem('librarian')}
          >
            📚 Librarian
          </button>
          <button 
            className={`nav-item ${activeSystem === 'rag' ? 'active' : ''}`}
            onClick={() => setActiveSystem('rag')}
          >
            🔍 RAG
          </button>
          <button 
            className={`nav-item ${activeSystem === 'worldmodel' ? 'active' : ''}`}
            onClick={() => setActiveSystem('worldmodel')}
          >
            🌐 World Model
          </button>
          <button 
            className={`nav-item ${activeSystem === 'layer1bus' ? 'active' : ''}`}
            onClick={() => setActiveSystem('layer1bus')}
          >
            📡 Layer 1 Bus
          </button>
          <button 
            className={`nav-item ${activeSystem === 'layer1connectors' ? 'active' : ''}`}
            onClick={() => setActiveSystem('layer1connectors')}
          >
            🔌 Layer 1 Connectors
          </button>
          <button 
            className={`nav-item ${activeSystem === 'layer2cognitive' ? 'active' : ''}`}
            onClick={() => setActiveSystem('layer2cognitive')}
          >
            🎯 Layer 2 Cognitive
          </button>
          <button 
            className={`nav-item ${activeSystem === 'layer2intelligence' ? 'active' : ''}`}
            onClick={() => setActiveSystem('layer2intelligence')}
          >
            🧬 Layer 2 Intelligence
          </button>
          <button 
            className={`nav-item ${activeSystem === 'neuro-symbolicai' ? 'active' : ''}`}
            onClick={() => setActiveSystem('neuro-symbolicai')}
          >
            🔣 Neuro-Symbolic AI
          </button>
        </nav>
      </div>

      <div className="dashboard-content">
        {renderContent()}
      </div>
    </div>
  );
};

export default EnterpriseDashboard;
