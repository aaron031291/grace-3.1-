import { useState, useEffect } from "react";
import "./CognitiveTab.css";

function CognitiveTab() {
  const [activeSubTab, setActiveSubTab] = useState("ooda");
  const [decisions, setDecisions] = useState([]);
  const [selectedDecision, setSelectedDecision] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchRecentDecisions();
    const interval = setInterval(fetchRecentDecisions, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchRecentDecisions = async () => {
    try {
      const response = await fetch("http://localhost:8000/cognitive/decisions/recent");
      if (response.ok) {
        const data = await response.json();
        setDecisions(data.decisions || []);
      }
    } catch (error) {
      console.error("Failed to fetch decisions:", error);
    }
  };

  const fetchDecisionDetails = async (decisionId) => {
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/cognitive/decisions/${decisionId}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedDecision(data);
      }
    } catch (error) {
      console.error("Failed to fetch decision details:", error);
    } finally {
      setLoading(false);
    }
  };

  const renderOODAView = () => {
    return (
      <div className="ooda-view">
        <div className="section-header">
          <h2>OODA Loop Decisions</h2>
          <p className="section-description">
            Every query goes through: Observe → Orient → Decide → Act
          </p>
        </div>

        <div className="decisions-grid">
          {/* Recent Decisions List */}
          <div className="decisions-list">
            <h3>Recent Decisions ({decisions.length})</h3>
            {decisions.length === 0 ? (
              <div className="empty-state">
                <p>No decisions yet. Make a query to see OODA loop in action.</p>
              </div>
            ) : (
              <div className="decision-items">
                {decisions.map((decision) => (
                  <div
                    key={decision.decision_id}
                    className={`decision-card ${
                      selectedDecision?.decision_id === decision.decision_id ? "selected" : ""
                    }`}
                    onClick={() => fetchDecisionDetails(decision.decision_id)}
                  >
                    <div className="decision-header">
                      <span className="decision-id">{decision.decision_id.slice(0, 8)}</span>
                      <span className={`decision-status ${decision.status}`}>
                        {decision.status}
                      </span>
                    </div>
                    <div className="decision-query">{decision.problem_statement}</div>
                    <div className="decision-meta">
                      <span className="decision-time">
                        {new Date(decision.created_at).toLocaleTimeString()}
                      </span>
                      {decision.strategy && (
                        <span className="decision-strategy">{decision.strategy}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Decision Details */}
          <div className="decision-details">
            {loading ? (
              <div className="loading-state">
                <div className="spinner"></div>
                <p>Loading decision details...</p>
              </div>
            ) : selectedDecision ? (
              <>
                <div className="details-header">
                  <h3>Decision: {selectedDecision.decision_id.slice(0, 8)}</h3>
                  <span className={`status-badge ${selectedDecision.status}`}>
                    {selectedDecision.status}
                  </span>
                </div>

                <div className="ooda-phases">
                  {/* Observe Phase */}
                  <div className="phase-card">
                    <div className="phase-header">
                      <div className="phase-number">1</div>
                      <h4>Observe</h4>
                    </div>
                    <div className="phase-content">
                      <div className="observation-item">
                        <strong>Query:</strong>
                        <p>{selectedDecision.observations?.query || "N/A"}</p>
                      </div>
                      <div className="observation-item">
                        <strong>Query Type:</strong>
                        <span className="badge">{selectedDecision.observations?.query_type || "unknown"}</span>
                      </div>
                      <div className="observation-item">
                        <strong>Ambiguity Level:</strong>
                        <span className={`ambiguity-badge ${selectedDecision.observations?.ambiguity_level || "low"}`}>
                          {selectedDecision.observations?.ambiguity_level || "low"}
                        </span>
                      </div>
                      <div className="observation-item">
                        <strong>Has Keywords:</strong>
                        <span>{selectedDecision.observations?.has_keywords ? "Yes" : "No"}</span>
                      </div>
                    </div>
                  </div>

                  {/* Orient Phase */}
                  <div className="phase-card">
                    <div className="phase-header">
                      <div className="phase-number">2</div>
                      <h4>Orient</h4>
                    </div>
                    <div className="phase-content">
                      <div className="observation-item">
                        <strong>Available Strategies:</strong>
                        <div className="strategies-list">
                          {(selectedDecision.context_info?.available_strategies || []).map((strategy) => (
                            <span key={strategy} className="strategy-badge">{strategy}</span>
                          ))}
                        </div>
                      </div>
                      <div className="observation-item">
                        <strong>Constraints:</strong>
                        <ul>
                          <li>Safety Critical: {selectedDecision.constraints?.safety_critical ? "Yes" : "No"}</li>
                          <li>Impact Scope: {selectedDecision.constraints?.impact_scope || "local"}</li>
                          <li>Requires High Confidence: {selectedDecision.constraints?.requires_high_confidence ? "Yes" : "No"}</li>
                        </ul>
                      </div>
                    </div>
                  </div>

                  {/* Decide Phase */}
                  <div className="phase-card">
                    <div className="phase-header">
                      <div className="phase-number">3</div>
                      <h4>Decide</h4>
                    </div>
                    <div className="phase-content">
                      <div className="observation-item">
                        <strong>Strategy Selected:</strong>
                        <span className="selected-strategy">{selectedDecision.strategy_selected || "N/A"}</span>
                      </div>
                      <div className="observation-item">
                        <strong>Alternatives Considered:</strong>
                        <div className="alternatives-list">
                          {(selectedDecision.alternative_paths || []).map((alt, idx) => (
                            <div key={idx} className="alternative-card">
                              <div className="alt-name">{alt.strategy}</div>
                              <div className="alt-scores">
                                <span>Value: {alt.immediate_value?.toFixed(2)}</span>
                                <span>Options: {alt.future_options?.toFixed(2)}</span>
                                <span>Simple: {alt.simplicity?.toFixed(2)}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Act Phase */}
                  <div className="phase-card">
                    <div className="phase-header">
                      <div className="phase-number">4</div>
                      <h4>Act</h4>
                    </div>
                    <div className="phase-content">
                      <div className="observation-item">
                        <strong>Execution Status:</strong>
                        <span className={`status-badge ${selectedDecision.action_status || "pending"}`}>
                          {selectedDecision.action_status || "pending"}
                        </span>
                      </div>
                      <div className="observation-item">
                        <strong>Quality Score:</strong>
                        <div className="quality-meter">
                          <div
                            className="quality-fill"
                            style={{width: `${(selectedDecision.quality_score || 0) * 100}%`}}
                          ></div>
                          <span className="quality-label">
                            {((selectedDecision.quality_score || 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <div className="observation-item">
                        <strong>Elapsed Time:</strong>
                        <span>{selectedDecision.elapsed_ms?.toFixed(0) || 0}ms</span>
                      </div>
                      <div className="observation-item">
                        <strong>Chunks Retrieved:</strong>
                        <span>{selectedDecision.chunks_returned || 0}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p>Select a decision from the list to see details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderAmbiguityView = () => {
    return (
      <div className="ambiguity-view">
        <div className="section-header">
          <h2>Ambiguity Tracking</h2>
          <p className="section-description">
            Known, Unknown, and Inferred information across all decisions
          </p>
        </div>

        {selectedDecision ? (
          <div className="ambiguity-ledger">
            <div className="ledger-section">
              <h3 className="ledger-title known">Known Information</h3>
              <div className="ledger-items">
                {(selectedDecision.ambiguity_ledger?.known || []).map((item, idx) => (
                  <div key={idx} className="ledger-item">
                    <span className="item-key">{item.key}</span>
                    <span className="item-value">{JSON.stringify(item.value)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="ledger-section">
              <h3 className="ledger-title unknown">Unknown Information</h3>
              <div className="ledger-items">
                {(selectedDecision.ambiguity_ledger?.unknowns || []).map((item, idx) => (
                  <div key={idx} className="ledger-item warning">
                    <span className="item-key">{item.key}</span>
                    {item.blocking && <span className="blocking-badge">BLOCKING</span>}
                  </div>
                ))}
              </div>
            </div>

            <div className="ledger-section">
              <h3 className="ledger-title inferred">Inferred Information</h3>
              <div className="ledger-items">
                {(selectedDecision.ambiguity_ledger?.inferred || []).map((item, idx) => (
                  <div key={idx} className="ledger-item">
                    <span className="item-key">{item.key}</span>
                    <span className="item-value">{JSON.stringify(item.value)}</span>
                    <span className="confidence-badge">
                      {(item.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-state">
            <p>Select a decision to view ambiguity tracking</p>
          </div>
        )}
      </div>
    );
  };

  const renderInvariantsView = () => {
    return (
      <div className="invariants-view">
        <div className="section-header">
          <h2>Invariant Validation</h2>
          <p className="section-description">
            Grace's 12 core invariants enforced on every decision
          </p>
        </div>

        {selectedDecision ? (
          <div className="invariants-grid">
            {(selectedDecision.invariant_validation || []).map((validation, idx) => (
              <div key={idx} className={`invariant-card ${validation.passed ? "passed" : "failed"}`}>
                <div className="invariant-header">
                  <span className="invariant-number">#{validation.number}</span>
                  <span className={`validation-status ${validation.passed ? "passed" : "failed"}`}>
                    {validation.passed ? "✓" : "✗"}
                  </span>
                </div>
                <h4 className="invariant-name">{validation.name}</h4>
                <p className="invariant-description">{validation.description}</p>
                {validation.message && (
                  <div className="invariant-message">{validation.message}</div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p>Select a decision to view invariant validation</p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="cognitive-tab">
      <div className="tab-header">
        <h1>Cognitive Blueprint</h1>
        <p>Real-time view into Grace's decision-making process</p>
      </div>

      <div className="sub-tabs">
        <button
          className={`sub-tab ${activeSubTab === "ooda" ? "active" : ""}`}
          onClick={() => setActiveSubTab("ooda")}
        >
          OODA Loop
        </button>
        <button
          className={`sub-tab ${activeSubTab === "ambiguity" ? "active" : ""}`}
          onClick={() => setActiveSubTab("ambiguity")}
        >
          Ambiguity Tracking
        </button>
        <button
          className={`sub-tab ${activeSubTab === "invariants" ? "active" : ""}`}
          onClick={() => setActiveSubTab("invariants")}
        >
          Invariants
        </button>
      </div>

      <div className="tab-content">
        {activeSubTab === "ooda" && renderOODAView()}
        {activeSubTab === "ambiguity" && renderAmbiguityView()}
        {activeSubTab === "invariants" && renderInvariantsView()}
      </div>
    </div>
  );
}

export default CognitiveTab;
