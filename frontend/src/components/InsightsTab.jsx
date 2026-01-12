import { useEffect, useState, useCallback } from "react";
import "./InsightsTab.css";

const API_BASE = "http://localhost:8000";

// Learning Insight Card
function InsightCard({ insight }) {
  const [expanded, setExpanded] = useState(false);

  const getTypeIcon = (type) => {
    switch (type) {
      case "pattern": return "P";
      case "rule": return "R";
      case "optimization": return "O";
      case "correction": return "C";
      case "discovery": return "D";
      default: return "I";
    }
  };

  const getImpactColor = (impact) => {
    if (impact >= 0.8) return "#10b981";
    if (impact >= 0.5) return "#3b82f6";
    if (impact >= 0.3) return "#f59e0b";
    return "#6b7280";
  };

  return (
    <div className={`insight-card type-${insight.type}`}>
      <div className="insight-header" onClick={() => setExpanded(!expanded)}>
        <span className={`insight-type-icon type-${insight.type}`}>
          {getTypeIcon(insight.type)}
        </span>
        <div className="insight-title-section">
          <h4>{insight.title}</h4>
          <span className="insight-category">{insight.category}</span>
        </div>
        <div className="insight-impact">
          <span
            className="impact-badge"
            style={{ backgroundColor: getImpactColor(insight.impact) }}
          >
            {Math.round(insight.impact * 100)}% Impact
          </span>
        </div>
        <span className="expand-icon">{expanded ? "-" : "+"}</span>
      </div>

      <p className="insight-summary">{insight.summary}</p>

      {expanded && (
        <div className="insight-details">
          {insight.details && (
            <div className="detail-section">
              <h5>Details</h5>
              <p>{insight.details}</p>
            </div>
          )}

          {insight.evidence && insight.evidence.length > 0 && (
            <div className="detail-section">
              <h5>Evidence</h5>
              <ul>
                {insight.evidence.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}

          {insight.improvements && insight.improvements.length > 0 && (
            <div className="detail-section">
              <h5>Improvements Made</h5>
              <div className="improvements-list">
                {insight.improvements.map((imp, i) => (
                  <div key={i} className="improvement-item">
                    <span className="improvement-metric">{imp.metric}</span>
                    <span className="improvement-change">
                      {imp.before} → {imp.after}
                    </span>
                    <span className={`improvement-delta ${imp.delta > 0 ? "positive" : "negative"}`}>
                      {imp.delta > 0 ? "+" : ""}{imp.delta}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="insight-meta">
            <span>Learned: {new Date(insight.learned_at).toLocaleString()}</span>
            {insight.confidence && (
              <span>Confidence: {Math.round(insight.confidence * 100)}%</span>
            )}
            {insight.genesis_key && (
              <span className="genesis-key">Key: {insight.genesis_key.slice(0, 12)}...</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Learning Metrics Panel
function LearningMetrics({ metrics }) {
  if (!metrics) return null;

  return (
    <div className="learning-metrics">
      <h4>Learning Progress</h4>
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-value">{metrics.patterns_discovered || 0}</span>
          <span className="metric-label">Patterns Discovered</span>
          <div className="metric-trend positive">+{metrics.patterns_trend || 0} this week</div>
        </div>
        <div className="metric-card">
          <span className="metric-value">{metrics.rules_generated || 0}</span>
          <span className="metric-label">Rules Generated</span>
          <div className="metric-trend positive">+{metrics.rules_trend || 0} this week</div>
        </div>
        <div className="metric-card">
          <span className="metric-value">{metrics.corrections_applied || 0}</span>
          <span className="metric-label">Self-Corrections</span>
          <div className="metric-trend">{metrics.corrections_trend || 0} this week</div>
        </div>
        <div className="metric-card">
          <span className="metric-value">{Math.round((metrics.accuracy || 0) * 100)}%</span>
          <span className="metric-label">Accuracy</span>
          <div className={`metric-trend ${metrics.accuracy_trend > 0 ? "positive" : ""}`}>
            {metrics.accuracy_trend > 0 ? "+" : ""}{metrics.accuracy_trend || 0}%
          </div>
        </div>
      </div>
    </div>
  );
}

// Active Learning Goals
function LearningGoals({ goals }) {
  if (!goals || goals.length === 0) return null;

  return (
    <div className="learning-goals">
      <h4>Current Learning Goals</h4>
      <div className="goals-list">
        {goals.map((goal, i) => (
          <div key={i} className="goal-card">
            <div className="goal-header">
              <span className="goal-name">{goal.name}</span>
              <span className={`goal-status status-${goal.status}`}>
                {goal.status}
              </span>
            </div>
            <p className="goal-description">{goal.description}</p>
            <div className="goal-progress">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${goal.progress}%` }}
                />
              </div>
              <span className="progress-text">{goal.progress}%</span>
            </div>
            <div className="goal-meta">
              {goal.target_date && (
                <span>Target: {new Date(goal.target_date).toLocaleDateString()}</span>
              )}
              {goal.milestones_completed !== undefined && (
                <span>{goal.milestones_completed}/{goal.total_milestones} milestones</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Knowledge Growth Chart (simplified)
function KnowledgeGrowth({ data }) {
  if (!data || data.length === 0) return null;

  const maxValue = Math.max(...data.map(d => d.value));

  return (
    <div className="knowledge-growth">
      <h4>Knowledge Growth (Last 30 Days)</h4>
      <div className="growth-chart">
        {data.map((point, i) => (
          <div key={i} className="chart-bar-container">
            <div
              className="chart-bar"
              style={{ height: `${(point.value / maxValue) * 100}%` }}
              title={`${point.date}: ${point.value} items`}
            />
            {i % 5 === 0 && (
              <span className="chart-label">{point.date.slice(5)}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Main Insights Tab
export default function InsightsTab() {
  const [insights, setInsights] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [goals, setGoals] = useState([]);
  const [growthData, setGrowthData] = useState([]);
  const [filterType, setFilterType] = useState("all");
  const [loading, setLoading] = useState(true);

  // Fetch insights
  const fetchInsights = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/cognitive/insights`);
      if (response.ok) {
        const data = await response.json();
        setInsights(data.insights || []);
      } else {
        // Demo data
        setInsights([
          {
            id: 1,
            type: "pattern",
            title: "Document Clustering Optimization",
            category: "RAG Performance",
            summary: "Identified that technical documents cluster more effectively when pre-processed with code extraction.",
            impact: 0.75,
            confidence: 0.89,
            learned_at: new Date(Date.now() - 86400000).toISOString(),
            details: "Analysis of 1,247 document ingestions revealed that documents containing code snippets achieve 34% better retrieval accuracy when code blocks are extracted and embedded separately.",
            evidence: [
              "34% improvement in retrieval precision",
              "Tested across 500 query samples",
              "Consistent results over 7-day period"
            ],
            improvements: [
              { metric: "Retrieval Precision", before: "72%", after: "89%", delta: 23 },
              { metric: "Query Latency", before: "245ms", after: "198ms", delta: -19 }
            ],
            genesis_key: "gk-insight-001"
          },
          {
            id: 2,
            type: "rule",
            title: "Auto-Tagging Confidence Threshold",
            category: "Librarian System",
            summary: "Learned optimal confidence threshold for automatic tag assignment based on user feedback patterns.",
            impact: 0.62,
            confidence: 0.94,
            learned_at: new Date(Date.now() - 172800000).toISOString(),
            details: "User approval rates increase significantly when auto-tagging confidence exceeds 0.85. Below this threshold, manual review is recommended.",
            evidence: [
              "Analyzed 2,340 auto-tag decisions",
              "92% user approval rate at 0.85+ confidence",
              "Only 67% approval rate below 0.7 confidence"
            ],
            genesis_key: "gk-insight-002"
          },
          {
            id: 3,
            type: "optimization",
            title: "Embedding Cache Strategy",
            category: "Performance",
            summary: "Discovered optimal cache invalidation strategy for frequently updated documents.",
            impact: 0.58,
            confidence: 0.82,
            learned_at: new Date(Date.now() - 259200000).toISOString(),
            genesis_key: "gk-insight-003"
          },
          {
            id: 4,
            type: "correction",
            title: "Relationship Detection Refinement",
            category: "Knowledge Graph",
            summary: "Self-corrected relationship detection to reduce false positives in citation links.",
            impact: 0.45,
            confidence: 0.91,
            learned_at: new Date(Date.now() - 345600000).toISOString(),
            improvements: [
              { metric: "False Positive Rate", before: "12%", after: "4%", delta: -67 }
            ],
            genesis_key: "gk-insight-004"
          },
          {
            id: 5,
            type: "discovery",
            title: "Cross-Domain Knowledge Transfer",
            category: "Learning",
            summary: "Discovered patterns enabling knowledge transfer between ML and systems programming domains.",
            impact: 0.82,
            confidence: 0.76,
            learned_at: new Date(Date.now() - 432000000).toISOString(),
            genesis_key: "gk-insight-005"
          }
        ]);
      }
    } catch (err) {
      console.error("Error fetching insights:", err);
    }
  }, []);

  // Fetch metrics
  const fetchMetrics = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/cognitive/learning-metrics`);
      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
      } else {
        // Demo data
        setMetrics({
          patterns_discovered: 47,
          patterns_trend: 12,
          rules_generated: 23,
          rules_trend: 5,
          corrections_applied: 8,
          corrections_trend: 2,
          accuracy: 0.89,
          accuracy_trend: 3
        });
      }
    } catch (err) {
      console.error("Error fetching metrics:", err);
    }
  }, []);

  // Fetch goals
  const fetchGoals = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/cognitive/learning-goals`);
      if (response.ok) {
        const data = await response.json();
        setGoals(data.goals || []);
      } else {
        // Demo data
        setGoals([
          {
            name: "Improve Code Understanding",
            description: "Enhance ability to understand and analyze complex codebases",
            status: "in_progress",
            progress: 67,
            milestones_completed: 4,
            total_milestones: 6
          },
          {
            name: "Domain Knowledge Expansion",
            description: "Expand knowledge in AI/ML research papers and implementations",
            status: "in_progress",
            progress: 45,
            milestones_completed: 2,
            total_milestones: 5
          }
        ]);
      }
    } catch (err) {
      console.error("Error fetching goals:", err);
    }
  }, []);

  // Fetch growth data
  const fetchGrowthData = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/cognitive/knowledge-growth`);
      if (response.ok) {
        const data = await response.json();
        setGrowthData(data.data || []);
      } else {
        // Generate demo data
        const demoData = [];
        for (let i = 29; i >= 0; i--) {
          const date = new Date(Date.now() - i * 86400000);
          demoData.push({
            date: date.toISOString().split("T")[0],
            value: Math.floor(50 + Math.random() * 100 + (30 - i) * 3)
          });
        }
        setGrowthData(demoData);
      }
    } catch (err) {
      console.error("Error fetching growth data:", err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchInsights(),
        fetchMetrics(),
        fetchGoals(),
        fetchGrowthData()
      ]);
      setLoading(false);
    };
    loadData();
  }, [fetchInsights, fetchMetrics, fetchGoals, fetchGrowthData]);

  // Filter insights
  const filteredInsights = filterType === "all"
    ? insights
    : insights.filter(i => i.type === filterType);

  if (loading) {
    return (
      <div className="insights-tab">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading Insights...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="insights-tab">
      <div className="insights-header">
        <div className="header-left">
          <h2>Insights</h2>
          <p>What Grace has learned and how it's improving</p>
        </div>
        <div className="header-stats">
          <div className="stat-item">
            <span className="stat-value">{insights.length}</span>
            <span className="stat-label">Total Insights</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{goals.filter(g => g.status === "in_progress").length}</span>
            <span className="stat-label">Active Goals</span>
          </div>
        </div>
      </div>

      <div className="insights-content">
        <div className="main-panel">
          <LearningMetrics metrics={metrics} />
          <KnowledgeGrowth data={growthData} />

          <div className="insights-section">
            <div className="section-header">
              <h4>Learning Insights</h4>
              <div className="filter-tabs">
                {["all", "pattern", "rule", "optimization", "correction", "discovery"].map(type => (
                  <button
                    key={type}
                    className={filterType === type ? "active" : ""}
                    onClick={() => setFilterType(type)}
                  >
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div className="insights-list">
              {filteredInsights.length === 0 ? (
                <div className="empty-state">
                  <p>No insights found for this filter</p>
                </div>
              ) : (
                filteredInsights.map(insight => (
                  <InsightCard key={insight.id} insight={insight} />
                ))
              )}
            </div>
          </div>
        </div>

        <div className="side-panel">
          <LearningGoals goals={goals} />
        </div>
      </div>
    </div>
  );
}
