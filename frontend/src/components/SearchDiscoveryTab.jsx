import React, { useState } from 'react';
import './SearchDiscoveryTab.css';
import RAGTab from './RAGTab';
import ResearchTab from './ResearchTab';
import CodeBaseTab from './CodeBaseTab';

/**
 * Consolidated Search & Discovery Tab
 * Combines: Documents (RAG), Research, and Code Base
 * Groups similar search/discovery functions together
 */
const SearchDiscoveryTab = () => {
  const [activeView, setActiveView] = useState('documents'); // documents, research, codebase

  return (
    <div className="search-discovery-tab">
      <div className="search-header">
        <div className="header-left">
          <h2>Search & Discovery</h2>
          <p>Documents, Research, and Code Base - All your search and discovery tools in one place</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="search-nav">
        <button
          className={`nav-button ${activeView === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveView('documents')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          Documents
        </button>
        <button
          className={`nav-button ${activeView === 'research' ? 'active' : ''}`}
          onClick={() => setActiveView('research')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
            />
          </svg>
          Research
        </button>
        <button
          className={`nav-button ${activeView === 'codebase' ? 'active' : ''}`}
          onClick={() => setActiveView('codebase')}
        >
          <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
            <path d="M10.478 1.647a.5.5 0 1 0-.956-.294l-4 13a.5.5 0 0 0 .956.294zM4.854 4.146a.5.5 0 0 1 0 .708L1.707 8l3.147 3.146a.5.5 0 0 1-.708.708l-3.5-3.5a.5.5 0 0 1 0-.708l3.5-3.5a.5.5 0 0 1 .708 0m6.292 0a.5.5 0 0 0 0 .708L14.293 8l-3.147 3.146a.5.5 0 0 0 .708.708l3.5-3.5a.5.5 0 0 0 0-.708l-3.5-3.5a.5.5 0 0 0-.708 0" />
          </svg>
          Code Base
        </button>
      </div>

      {/* Content Views */}
      <div className="search-content">
        {activeView === 'documents' && <RAGTab />}
        {activeView === 'research' && <ResearchTab />}
        {activeView === 'codebase' && <CodeBaseTab />}
      </div>
    </div>
  );
};

export default SearchDiscoveryTab;
