import React, { useState } from 'react';
import './OrchestrationConsolidatedTab.css';
import OrchestrationTab from './OrchestrationTab';
import ConnectorsTab from './ConnectorsTab';
import ExperimentTab from './ExperimentTab';

/**
 * Consolidated Orchestration Tab
 * Combines: Orchestration, Connectors, and Experiments
 * Groups integration and orchestration functions together
 */
const OrchestrationConsolidatedTab = () => {
  const [activeView, setActiveView] = useState('orchestration'); // orchestration, connectors, experiments

  return (
    <div className="orchestration-consolidated-tab">
      <div className="orchestration-header">
        <div className="header-left">
          <h2>Orchestration & Integration</h2>
          <p>Orchestration, Connectors, and Experiments - Manage integrations and workflows</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="orchestration-nav">
        <button
          className={`nav-button ${activeView === 'orchestration' ? 'active' : ''}`}
          onClick={() => setActiveView('orchestration')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="5" r="3"></circle>
            <circle cx="5" cy="19" r="3"></circle>
            <circle cx="19" cy="19" r="3"></circle>
            <line x1="12" y1="8" x2="5" y2="16"></line>
            <line x1="12" y1="8" x2="19" y2="16"></line>
          </svg>
          Orchestration
        </button>
        <button
          className={`nav-button ${activeView === 'connectors' ? 'active' : ''}`}
          onClick={() => setActiveView('connectors')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
          </svg>
          Connectors
        </button>
        <button
          className={`nav-button ${activeView === 'experiments' ? 'active' : ''}`}
          onClick={() => setActiveView('experiments')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 3h6v2H9z"></path>
            <path d="M10 5v4l-4 8h12l-4-8V5"></path>
            <circle cx="12" cy="15" r="1"></circle>
          </svg>
          Experiments
        </button>
      </div>

      {/* Content Views */}
      <div className="orchestration-content">
        {activeView === 'orchestration' && <OrchestrationTab />}
        {activeView === 'connectors' && <ConnectorsTab />}
        {activeView === 'experiments' && <ExperimentTab />}
      </div>
    </div>
  );
};

export default OrchestrationConsolidatedTab;
