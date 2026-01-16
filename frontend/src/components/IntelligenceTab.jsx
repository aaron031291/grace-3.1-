import React, { useState, useEffect } from 'react';
import './IntelligenceTab.css';
import MLIntelligenceTab from './MLIntelligenceTab';
import InsightsTab from './InsightsTab';
import LearningTab from './LearningTab';
import CognitiveTab from './CognitiveTab';

/**
 * Consolidated Intelligence Tab
 * Combines: ML Intelligence, Insights, Learning, and Cognitive (with real-time decisions)
 * This reduces tab clutter by grouping similar AI/ML functions together
 */
const IntelligenceTab = () => {
  const [activeView, setActiveView] = useState('decisions'); // decisions, ml, insights, learning, cognitive
  const [realTimeDecisions, setRealTimeDecisions] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    // Start real-time decision streaming
    startDecisionStream();
    return () => {
      setIsStreaming(false);
    };
  }, []);

  const startDecisionStream = async () => {
    setIsStreaming(true);
    
    // Poll for new decisions every 2 seconds for real-time updates
    const interval = setInterval(async () => {
      try {
        const response = await fetch('http://localhost:8000/cognitive/decisions/recent?limit=10');
        if (response.ok) {
          const data = await response.json();
          const newDecisions = data.decisions || [];
          
          // Check if we have new decisions (compare by decision_id)
          if (newDecisions.length > 0) {
            setRealTimeDecisions(newDecisions);
          }
        }
      } catch (error) {
        console.error('Error fetching real-time decisions:', error);
        // Don't stop streaming on error, just log it
      }
    }, 2000);

    // Initial fetch
    try {
      const response = await fetch('http://localhost:8000/cognitive/decisions/recent?limit=10');
      if (response.ok) {
        const data = await response.json();
        setRealTimeDecisions(data.decisions || []);
      }
    } catch (error) {
      console.error('Error fetching initial decisions:', error);
    }

    return () => clearInterval(interval);
  };

  return (
    <div className="intelligence-tab">
      <div className="intelligence-header">
        <div className="header-left">
          <h2>Intelligence & Learning</h2>
          <p>ML Intelligence, Insights, Learning, and Real-Time Decisions</p>
        </div>
        <div className="header-right">
          {isStreaming && (
            <div className="streaming-indicator">
              <span className="streaming-dot"></span>
              <span>Live Decisions</span>
              {realTimeDecisions.length > 0 && (
                <span className="decision-count">({realTimeDecisions.length} recent)</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Navigation Tabs */}
      <div className="intelligence-nav">
        <button
          className={`nav-button ${activeView === 'decisions' ? 'active' : ''}`}
          onClick={() => setActiveView('decisions')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v6m0 6v6m5-9l-4 4m-2 2l-4 4m10-12l-4 4m-2 2l-4 4M1 12h6m6 0h6"></path>
          </svg>
          Real-Time Decisions
          {realTimeDecisions.length > 0 && (
            <span className="badge">{realTimeDecisions.length}</span>
          )}
        </button>
        <button
          className={`nav-button ${activeView === 'ml' ? 'active' : ''}`}
          onClick={() => setActiveView('ml')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
            <path d="M12 17h.01"></path>
          </svg>
          ML Intelligence
        </button>
        <button
          className={`nav-button ${activeView === 'insights' ? 'active' : ''}`}
          onClick={() => setActiveView('insights')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M12 16v-4"></path>
            <path d="M12 8h.01"></path>
          </svg>
          Insights
        </button>
        <button
          className={`nav-button ${activeView === 'learning' ? 'active' : ''}`}
          onClick={() => setActiveView('learning')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 10v6M2 10l10-5 10 5-10 5z"></path>
            <path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"></path>
          </svg>
          Learning
        </button>
        <button
          className={`nav-button ${activeView === 'cognitive' ? 'active' : ''}`}
          onClick={() => setActiveView('cognitive')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v6m0 6v6m5-9l-4 4m-2 2l-4 4m10-12l-4 4m-2 2l-4 4M1 12h6m6 0h6"></path>
          </svg>
          Cognitive Blueprint
        </button>
      </div>

      {/* Real-Time Decisions View (Default) */}
      {activeView === 'decisions' && (
        <div className="decisions-live-view">
          <div className="live-header">
            <h3>Grace's Decisions in Real-Time</h3>
            <p>Watch as Grace makes decisions through the OODA loop (Observe → Orient → Decide → Act)</p>
          </div>
          
          <div className="decisions-stream">
            {realTimeDecisions.length === 0 ? (
              <div className="empty-state">
                <p>No recent decisions. Make a query to see Grace's decision-making process.</p>
              </div>
            ) : (
              <div className="decisions-timeline">
                {realTimeDecisions.map((decision) => (
                  <div key={decision.decision_id} className="decision-stream-item">
                    <div className="stream-time">
                      {new Date(decision.created_at).toLocaleTimeString()}
                    </div>
                    <div className="stream-content">
                      <div className="stream-header">
                        <span className="stream-id">{decision.decision_id.slice(0, 8)}</span>
                        <span className={`stream-status ${decision.status}`}>
                          {decision.status}
                        </span>
                      </div>
                      <div className="stream-query">{decision.problem_statement}</div>
                      <div className="stream-phases">
                        <div className={`phase-indicator ${decision.observations ? 'complete' : 'pending'}`}>
                          <span>Observe</span>
                        </div>
                        <div className={`phase-indicator ${decision.context_info ? 'complete' : 'pending'}`}>
                          <span>Orient</span>
                        </div>
                        <div className={`phase-indicator ${decision.strategy_selected ? 'complete' : 'pending'}`}>
                          <span>Decide</span>
                        </div>
                        <div className={`phase-indicator ${decision.action_status === 'completed' ? 'complete' : 'pending'}`}>
                          <span>Act</span>
                        </div>
                      </div>
                      {decision.strategy && (
                        <div className="stream-strategy">
                          Strategy: <strong>{decision.strategy}</strong>
                        </div>
                      )}
                      {decision.quality_score !== undefined && (
                        <div className="stream-quality">
                          Quality: <strong>{((decision.quality_score || 0) * 100).toFixed(0)}%</strong>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Link to full Cognitive view */}
          <div className="cognitive-link">
            <button 
              className="view-full-cognitive"
              onClick={() => setActiveView('cognitive')}
            >
              View Full Cognitive Blueprint →
            </button>
          </div>
        </div>
      )}

      {/* ML Intelligence View */}
      {activeView === 'ml' && <MLIntelligenceTab />}

      {/* Insights View */}
      {activeView === 'insights' && <InsightsTab />}

      {/* Learning View */}
      {activeView === 'learning' && <LearningTab />}

      {/* Cognitive Blueprint View */}
      {activeView === 'cognitive' && <CognitiveTab />}
    </div>
  );
};

export default IntelligenceTab;
