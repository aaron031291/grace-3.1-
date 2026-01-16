import React, { useState } from 'react';
import './MonitoringConsolidatedTab.css';
import MonitoringTab from './MonitoringTab';
import TelemetryTab from './TelemetryTab';

/**
 * Consolidated Monitoring Tab
 * Combines: Monitoring and Telemetry
 * Groups system health and metrics together
 */
const MonitoringConsolidatedTab = () => {
  const [activeView, setActiveView] = useState('monitoring'); // monitoring, telemetry

  return (
    <div className="monitoring-consolidated-tab">
      <div className="monitoring-header">
        <div className="header-left">
          <h2>System Monitoring</h2>
          <p>System Health, Organs Progress, and Telemetry - Complete system observability</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="monitoring-nav">
        <button
          className={`nav-button ${activeView === 'monitoring' ? 'active' : ''}`}
          onClick={() => setActiveView('monitoring')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="12 3 20 7.5 20 16.5 12 21 4 16.5 4 7.5 12 3"></polyline>
            <line x1="12" y1="12" x2="20" y2="7.5"></line>
            <line x1="12" y1="12" x2="12" y2="21"></line>
            <line x1="12" y1="12" x2="4" y2="7.5"></line>
          </svg>
          System Health
        </button>
        <button
          className={`nav-button ${activeView === 'telemetry' ? 'active' : ''}`}
          onClick={() => setActiveView('telemetry')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
          </svg>
          Telemetry
        </button>
      </div>

      {/* Content Views */}
      <div className="monitoring-content">
        {activeView === 'monitoring' && <MonitoringTab />}
        {activeView === 'telemetry' && <TelemetryTab />}
      </div>
    </div>
  );
};

export default MonitoringConsolidatedTab;
