import { useEffect, useState, useCallback, useRef } from "react";
import "./GovernanceTab.css";

const API_BASE = "http://localhost:8000";

// Trust score visualization
const getTrustColor = (score) => {
  if (score >= 0.8) return "#10b981";
  if (score >= 0.6) return "#3b82f6";
  if (score >= 0.4) return "#f59e0b";
  return "#ef4444";
};

const getTrustLevel = (score) => {
  if (score >= 0.8) return "High";
  if (score >= 0.6) return "Medium";
  if (score >= 0.4) return "Low";
  return "Critical";
};

// Governance Pillar Icons
const PillarIcon = ({ type }) => {
  const icons = {
    operational: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
      </svg>
    ),
    behavioral: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="8" r="5"/>
        <path d="M20 21a8 8 0 0 0-16 0"/>
      </svg>
    ),
    immutable: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        <path d="M9 12l2 2 4-4"/>
      </svg>
    )
  };
  return icons[type] || null;
};

// Document Upload Component
function DocumentUpload({ pillarType, onUpload, existingDocs }) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      await uploadFiles(files);
    }
  };

  const handleFileSelect = async (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      await uploadFiles(files);
    }
  };

  const uploadFiles = async (files) => {
    setUploading(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("pillar_type", pillarType);
        formData.append("filename", file.name);

        await fetch(`${API_BASE}/governance/documents/upload`, {
          method: "POST",
          body: formData,
        });
      }
      onUpload();
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Failed to upload document: " + err.message);
    }
    setUploading(false);
  };

  return (
    <div className="document-upload-section">
      <div
        className={`upload-zone ${dragActive ? "drag-active" : ""} ${uploading ? "uploading" : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.txt,.md,.json"
          onChange={handleFileSelect}
          style={{ display: "none" }}
        />
        {uploading ? (
          <div className="upload-status">
            <div className="spinner small" />
            <span>Uploading...</span>
          </div>
        ) : (
          <>
            <div className="upload-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
              </svg>
            </div>
            <p>Drag & drop governance documents here</p>
            <span className="upload-hint">PDF, DOC, TXT, MD, JSON supported</span>
          </>
        )}
      </div>

      {existingDocs && existingDocs.length > 0 && (
        <div className="existing-docs">
          <h5>Uploaded Documents ({existingDocs.length})</h5>
          <ul>
            {existingDocs.map((doc, i) => (
              <li key={i} className="doc-item">
                <span className="doc-icon">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                    <polyline points="14,2 14,8 20,8"/>
                  </svg>
                </span>
                <span className="doc-name">{doc.filename}</span>
                <span className="doc-status" data-status={doc.status}>
                  {doc.status === "processed" ? "Active" : doc.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// Natural Language Rule Input Component
function NaturalLanguageRuleInput({ pillarType, onRuleAdded }) {
  const [ruleText, setRuleText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const placeholders = {
    operational: "e.g., \"Always follow HIPAA guidelines when handling medical data\" or \"Require approval for any action costing over $1000\"",
    behavioral: "e.g., \"Use a friendly, casual tone in responses\" or \"Always provide step-by-step explanations\""
  };

  const handleAddRule = async () => {
    if (!ruleText.trim()) return;

    setIsProcessing(true);
    setFeedback(null);

    try {
      // Parse natural language into a rule structure
      const parsedRule = parseNaturalLanguageRule(ruleText, pillarType);

      // Send to backend
      const response = await fetch(`${API_BASE}/governance/rules/new`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...parsedRule,
          pillar_type: pillarType,
          source: "User-defined (natural language)"
        })
      });

      if (response.ok) {
        setFeedback({ type: "success", message: "Rule added successfully!" });
        setRuleText("");
        onRuleAdded();
      } else {
        const error = await response.json();
        setFeedback({ type: "error", message: error.detail || "Failed to add rule" });
      }
    } catch (err) {
      console.error("Error adding rule:", err);
      setFeedback({ type: "error", message: "Failed to add rule. Please try again." });
    }

    setIsProcessing(false);

    // Clear feedback after 3 seconds
    setTimeout(() => setFeedback(null), 3000);
  };

  // Parse natural language into rule structure
  const parseNaturalLanguageRule = (text, pillar) => {
    const lowerText = text.toLowerCase();

    // Determine severity based on keywords
    let severity = pillar === "operational" ? 6 : 3;
    if (lowerText.includes("always") || lowerText.includes("must") || lowerText.includes("never")) {
      severity = pillar === "operational" ? 8 : 5;
    }
    if (lowerText.includes("critical") || lowerText.includes("required") || lowerText.includes("mandatory")) {
      severity = 9;
    }

    // Determine action based on keywords
    let action = "warn";
    if (lowerText.includes("block") || lowerText.includes("prevent") || lowerText.includes("never")) {
      action = "block";
    } else if (lowerText.includes("review") || lowerText.includes("approval") || lowerText.includes("approve")) {
      action = "flag";
    }

    // Extract a name from the text (first 50 chars or until first period/comma)
    let name = text.split(/[.,!?]/)[0].trim();
    if (name.length > 50) {
      name = name.substring(0, 47) + "...";
    }

    // Try to extract patterns for matching
    let pattern = null;
    const patternMatches = text.match(/["']([^"']+)["']/g);
    if (patternMatches) {
      pattern = patternMatches.map(p => p.replace(/["']/g, "")).join("|");
    }

    return {
      name: name,
      description: text,
      severity: severity,
      action: action,
      pattern: pattern,
      enabled: true
    };
  };

  return (
    <div className="natural-language-input">
      <div className="nl-input-header">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 20h9"/>
          <path d="M16.5 3.5a2.121 2.121 0 113 3L7 19l-4 1 1-4L16.5 3.5z"/>
        </svg>
        <span>Add Rule in Natural Language</span>
      </div>
      <div className="nl-input-container">
        <textarea
          value={ruleText}
          onChange={(e) => setRuleText(e.target.value)}
          placeholder={placeholders[pillarType]}
          rows={2}
          disabled={isProcessing}
        />
        <button
          className="btn-add-rule"
          onClick={handleAddRule}
          disabled={!ruleText.trim() || isProcessing}
        >
          {isProcessing ? (
            <>
              <div className="spinner small" />
              Processing...
            </>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              Add Rule
            </>
          )}
        </button>
      </div>
      {feedback && (
        <div className={`nl-feedback ${feedback.type}`}>
          {feedback.type === "success" ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
              <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          )}
          {feedback.message}
        </div>
      )}
      <div className="nl-hint">
        Write your rule in plain English. Grace will interpret and apply it automatically.
      </div>
    </div>
  );
}

// Governance Pillar Card
function GovernancePillar({ type, title, description, rules, documents, onUpload, onToggleRule, onEditRule, onRuleAdded }) {
  const [expanded, setExpanded] = useState(false);
  const [showUpload, setShowUpload] = useState(false);

  const pillarColors = {
    operational: { bg: "#dbeafe", border: "#3b82f6", icon: "#1e40af" },
    behavioral: { bg: "#fef3c7", border: "#f59e0b", icon: "#92400e" },
    immutable: { bg: "#fee2e2", border: "#ef4444", icon: "#991b1b" }
  };

  const colors = pillarColors[type];

  return (
    <div
      className={`governance-pillar pillar-${type}`}
      style={{ borderColor: colors.border }}
    >
      <div
        className="pillar-header"
        onClick={() => setExpanded(!expanded)}
        style={{ backgroundColor: colors.bg }}
      >
        <div className="pillar-icon" style={{ color: colors.icon }}>
          <PillarIcon type={type} />
        </div>
        <div className="pillar-info">
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        <div className="pillar-stats">
          <span className="rule-count">{rules?.length || 0} rules</span>
          <span className="doc-count">{documents?.length || 0} docs</span>
        </div>
        <span className={`expand-icon ${expanded ? "expanded" : ""}`}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="6,9 12,15 18,9"/>
          </svg>
        </span>
      </div>

      {expanded && (
        <div className="pillar-content">
          <div className="pillar-actions">
            <button
              className={`btn-upload ${showUpload ? "active" : ""}`}
              onClick={() => setShowUpload(!showUpload)}
            >
              {showUpload ? "Hide Upload" : "Upload Documents"}
            </button>
          </div>

          {showUpload && (
            <DocumentUpload
              pillarType={type}
              onUpload={onUpload}
              existingDocs={documents}
            />
          )}

          {/* Natural Language Rule Input - only for operational and behavioral */}
          {type !== "immutable" && (
            <NaturalLanguageRuleInput
              pillarType={type}
              onRuleAdded={onRuleAdded}
            />
          )}

          <div className="rules-section">
            <h4>Active Rules</h4>
            {rules && rules.length > 0 ? (
              <ul className="rules-list">
                {rules.map((rule, i) => (
                  <li key={i} className={`rule-item ${rule.enabled ? "enabled" : "disabled"}`}>
                    <div className="rule-toggle">
                      <input
                        type="checkbox"
                        checked={rule.enabled}
                        onChange={() => onToggleRule(rule.id, !rule.enabled)}
                        disabled={type === "immutable"}
                      />
                    </div>
                    <div className="rule-content">
                      <span className="rule-name">{rule.name}</span>
                      <span className="rule-description">{rule.description}</span>
                      {rule.source && (
                        <span className="rule-source">Source: {rule.source}</span>
                      )}
                    </div>
                    <div className="rule-severity" data-severity={rule.severity}>
                      {rule.severity}
                    </div>
                    {type !== "immutable" && (
                      <button
                        className="btn-edit-rule"
                        onClick={() => onEditRule(rule)}
                      >
                        Edit
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="no-rules">No rules configured. Upload governance documents to generate rules.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Human-in-the-Loop Decision Card
function DecisionCard({ decision, onAction }) {
  const [note, setNote] = useState("");
  const [showDiscuss, setShowDiscuss] = useState(false);

  const statusColors = {
    pending: "#f59e0b",
    confirmed: "#10b981",
    denied: "#ef4444",
    discussing: "#3b82f6"
  };

  const getSeverityLabel = (severity) => {
    if (severity >= 9) return "Critical";
    if (severity >= 7) return "High";
    if (severity >= 4) return "Medium";
    return "Low";
  };

  return (
    <div className={`decision-card status-${decision.status}`}>
      <div className="decision-header">
        <div className="decision-type">
          <span className={`pillar-badge pillar-${decision.pillar_type}`}>
            {decision.pillar_type}
          </span>
          <span className={`severity-badge severity-${getSeverityLabel(decision.severity).toLowerCase()}`}>
            {getSeverityLabel(decision.severity)}
          </span>
        </div>
        <span
          className="decision-status"
          style={{ color: statusColors[decision.status] }}
        >
          {decision.status.toUpperCase()}
        </span>
      </div>

      <div className="decision-content">
        <h4>{decision.title}</h4>
        <p>{decision.description}</p>

        {decision.context && (
          <div className="decision-context">
            <strong>Context:</strong>
            <pre>{JSON.stringify(decision.context, null, 2)}</pre>
          </div>
        )}

        {decision.rule_reference && (
          <div className="rule-reference">
            <span className="ref-label">Related Rule:</span>
            <span className="ref-value">{decision.rule_reference}</span>
          </div>
        )}
      </div>

      {decision.status === "pending" && (
        <div className="decision-actions">
          {showDiscuss ? (
            <div className="discuss-form">
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Add your thoughts or questions..."
                rows={3}
              />
              <div className="discuss-buttons">
                <button
                  className="btn-send-discuss"
                  onClick={() => {
                    onAction(decision.id, "discuss", note);
                    setNote("");
                    setShowDiscuss(false);
                  }}
                >
                  Send for Discussion
                </button>
                <button
                  className="btn-cancel"
                  onClick={() => setShowDiscuss(false)}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="action-buttons">
              <button
                className="btn-confirm"
                onClick={() => onAction(decision.id, "confirm")}
              >
                Confirm
              </button>
              <button
                className="btn-discuss"
                onClick={() => setShowDiscuss(true)}
              >
                Discuss
              </button>
              <button
                className="btn-deny"
                onClick={() => onAction(decision.id, "deny")}
              >
                Deny
              </button>
            </div>
          )}
        </div>
      )}

      {decision.status === "discussing" && decision.discussion && (
        <div className="discussion-thread">
          <h5>Discussion</h5>
          {decision.discussion.map((msg, i) => (
            <div key={i} className={`discussion-msg ${msg.from}`}>
              <span className="msg-author">{msg.from === "grace" ? "Grace" : "You"}</span>
              <span className="msg-content">{msg.content}</span>
              <span className="msg-time">{new Date(msg.timestamp).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}

      <div className="decision-meta">
        <span>Created: {new Date(decision.created_at).toLocaleString()}</span>
        {decision.resolved_at && (
          <span>Resolved: {new Date(decision.resolved_at).toLocaleString()}</span>
        )}
      </div>
    </div>
  );
}

// Rule Editor Modal
function RuleEditorModal({ rule, onSave, onClose }) {
  const [editedRule, setEditedRule] = useState(rule || {
    name: "",
    description: "",
    pattern: "",
    action: "warn",
    severity: 5,
    enabled: true
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h3>{rule ? "Edit Rule" : "Create Rule"}</h3>

        <div className="form-group">
          <label>Rule Name</label>
          <input
            type="text"
            value={editedRule.name}
            onChange={(e) => setEditedRule({ ...editedRule, name: e.target.value })}
            placeholder="e.g., No PII in Responses"
          />
        </div>

        <div className="form-group">
          <label>Description</label>
          <textarea
            value={editedRule.description}
            onChange={(e) => setEditedRule({ ...editedRule, description: e.target.value })}
            placeholder="What does this rule enforce?"
            rows={2}
          />
        </div>

        <div className="form-group">
          <label>Pattern (regex or keyword)</label>
          <input
            type="text"
            value={editedRule.pattern}
            onChange={(e) => setEditedRule({ ...editedRule, pattern: e.target.value })}
            placeholder="e.g., SSN|social security|\\d{3}-\\d{2}-\\d{4}"
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Action</label>
            <select
              value={editedRule.action}
              onChange={(e) => setEditedRule({ ...editedRule, action: e.target.value })}
            >
              <option value="warn">Warn</option>
              <option value="block">Block</option>
              <option value="flag">Flag for Review</option>
              <option value="redact">Redact</option>
            </select>
          </div>

          <div className="form-group">
            <label>Severity (1-10)</label>
            <input
              type="number"
              min="1"
              max="10"
              value={editedRule.severity}
              onChange={(e) => setEditedRule({ ...editedRule, severity: parseInt(e.target.value) })}
            />
          </div>
        </div>

        <div className="modal-actions">
          <button className="btn-save" onClick={() => onSave(editedRule)}>
            Save Rule
          </button>
          <button className="btn-cancel" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// Main Governance Tab
export default function GovernanceTab() {
  const [activeView, setActiveView] = useState("pillars");
  const [pillarsData, setPillarsData] = useState({
    operational: { rules: [], documents: [] },
    behavioral: { rules: [], documents: [] },
    immutable: { rules: [], documents: [] }
  });
  const [pendingDecisions, setPendingDecisions] = useState([]);
  const [decisionHistory, setDecisionHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editingRule, setEditingRule] = useState(null);
  const [showRuleEditor, setShowRuleEditor] = useState(false);

  // Fetch governance data
  const fetchGovernanceData = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/governance/pillars`);
      if (response.ok) {
        const data = await response.json();
        setPillarsData(data);
      } else {
        // Use default data if endpoint doesn't exist yet
        setPillarsData({
          operational: {
            rules: [
              { id: 1, name: "Industry Compliance", description: "Ensure outputs comply with industry standards", severity: 8, enabled: true, source: "ISO 27001" },
              { id: 2, name: "Data Classification", description: "Classify and handle data according to sensitivity", severity: 7, enabled: true, source: "GDPR" },
            ],
            documents: []
          },
          behavioral: {
            rules: [
              { id: 3, name: "Professional Tone", description: "Maintain professional communication style", severity: 3, enabled: true },
              { id: 4, name: "Response Length", description: "Keep responses concise and actionable", severity: 2, enabled: true },
            ],
            documents: []
          },
          immutable: {
            rules: [
              { id: 5, name: "No Harmful Content", description: "Never generate content that could cause harm", severity: 10, enabled: true },
              { id: 6, name: "No Illegal Activities", description: "Never assist with illegal activities", severity: 10, enabled: true },
              { id: 7, name: "No PII Exposure", description: "Never expose personally identifiable information", severity: 10, enabled: true },
              { id: 8, name: "Safety Override", description: "Safety cannot be bypassed by any prompt", severity: 10, enabled: true },
            ],
            documents: []
          }
        });
      }
    } catch (err) {
      console.error("Error fetching governance data:", err);
    }
  }, []);

  // Fetch pending decisions
  const fetchPendingDecisions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/governance/decisions/pending`);
      if (response.ok) {
        const data = await response.json();
        setPendingDecisions(data.decisions || []);
      } else {
        // Mock data for demonstration
        setPendingDecisions([
          {
            id: 1,
            title: "External API Integration Request",
            description: "Grace wants to integrate with a third-party analytics API to enhance response accuracy.",
            pillar_type: "operational",
            severity: 6,
            status: "pending",
            context: { api_name: "AnalyticsAPI", data_types: ["usage_metrics", "response_quality"] },
            rule_reference: "Data Classification",
            created_at: new Date().toISOString()
          },
          {
            id: 2,
            title: "Tone Adjustment Request",
            description: "User prefers more casual communication style. This change would affect all future interactions.",
            pillar_type: "behavioral",
            severity: 2,
            status: "pending",
            context: { current_tone: "professional", requested_tone: "casual" },
            created_at: new Date(Date.now() - 3600000).toISOString()
          }
        ]);
      }
    } catch (err) {
      console.error("Error fetching decisions:", err);
    }
  }, []);

  // Fetch stats
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/governance/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      } else {
        setStats({
          total_rules: 8,
          active_rules: 8,
          pending_decisions: 2,
          confirmed_today: 5,
          denied_today: 1,
          compliance_score: 0.94
        });
      }
    } catch (err) {
      console.error("Error fetching stats:", err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchGovernanceData(),
        fetchPendingDecisions(),
        fetchStats()
      ]);
      setLoading(false);
    };
    loadData();
  }, [fetchGovernanceData, fetchPendingDecisions, fetchStats]);

  // Handle decision action
  const handleDecisionAction = async (decisionId, action, note = "") => {
    try {
      await fetch(`${API_BASE}/governance/decisions/${decisionId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note, reviewed_by: "user" })
      });
      fetchPendingDecisions();
      fetchStats();
    } catch (err) {
      console.error("Error handling decision:", err);
      // Update locally for demo
      setPendingDecisions(prev =>
        prev.map(d => d.id === decisionId
          ? { ...d, status: action === "confirm" ? "confirmed" : action === "deny" ? "denied" : "discussing" }
          : d
        )
      );
    }
  };

  // Handle rule toggle
  const handleRuleToggle = async (ruleId, enabled) => {
    try {
      await fetch(`${API_BASE}/governance/rules/${ruleId}/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled })
      });
      fetchGovernanceData();
    } catch (err) {
      console.error("Error toggling rule:", err);
      // Update locally for demo
      setPillarsData(prev => {
        const newData = { ...prev };
        for (const pillar of Object.keys(newData)) {
          newData[pillar].rules = newData[pillar].rules.map(r =>
            r.id === ruleId ? { ...r, enabled } : r
          );
        }
        return newData;
      });
    }
  };

  // Handle rule edit
  const handleRuleEdit = (rule) => {
    setEditingRule(rule);
    setShowRuleEditor(true);
  };

  // Handle rule save
  const handleRuleSave = async (rule) => {
    try {
      await fetch(`${API_BASE}/governance/rules/${rule.id || "new"}`, {
        method: rule.id ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(rule)
      });
      fetchGovernanceData();
    } catch (err) {
      console.error("Error saving rule:", err);
    }
    setShowRuleEditor(false);
    setEditingRule(null);
  };

  if (loading) {
    return (
      <div className="governance-tab">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading Governance Framework...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="governance-tab">
      <div className="governance-header">
        <div className="header-left">
          <h2>Governance Framework</h2>
          <p>Three-pillar governance with human-in-the-loop decision making</p>
        </div>
        <div className="header-stats">
          {stats && (
            <>
              <div className="stat-item primary">
                <span className="stat-value">{Math.round(stats.compliance_score * 100)}%</span>
                <span className="stat-label">Compliance</span>
              </div>
              <div className="stat-item warning">
                <span className="stat-value">{stats.pending_decisions}</span>
                <span className="stat-label">Pending</span>
              </div>
              <div className="stat-item success">
                <span className="stat-value">{stats.confirmed_today}</span>
                <span className="stat-label">Confirmed</span>
              </div>
              <div className="stat-item info">
                <span className="stat-value">{stats.active_rules}</span>
                <span className="stat-label">Active Rules</span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="governance-toolbar">
        <div className="view-tabs">
          <button
            className={activeView === "pillars" ? "active" : ""}
            onClick={() => setActiveView("pillars")}
          >
            Governance Pillars
          </button>
          <button
            className={activeView === "decisions" ? "active" : ""}
            onClick={() => setActiveView("decisions")}
          >
            Decisions
            {pendingDecisions.length > 0 && (
              <span className="badge">{pendingDecisions.length}</span>
            )}
          </button>
          <button
            className={activeView === "history" ? "active" : ""}
            onClick={() => setActiveView("history")}
          >
            History
          </button>
          <button
            className={activeView === "analytics" ? "active" : ""}
            onClick={() => setActiveView("analytics")}
          >
            Analytics
          </button>
        </div>
        <div className="toolbar-spacer" />
        <button className="btn-refresh" onClick={() => {
          fetchGovernanceData();
          fetchPendingDecisions();
          fetchStats();
        }}>
          Refresh
        </button>
      </div>

      <div className="governance-content">
        {activeView === "pillars" && (
          <div className="pillars-view">
            <GovernancePillar
              type="operational"
              title="Operational Governance"
              description="Industry standards, compliance requirements, and professional protocols that guide Grace's decision-making in real-world scenarios."
              rules={pillarsData.operational.rules}
              documents={pillarsData.operational.documents}
              onUpload={fetchGovernanceData}
              onToggleRule={handleRuleToggle}
              onEditRule={handleRuleEdit}
              onRuleAdded={fetchGovernanceData}
            />

            <GovernancePillar
              type="behavioral"
              title="Behavioral Governance"
              description="Personal interaction preferences, communication style, and user-specific adaptations that shape Grace's personality."
              rules={pillarsData.behavioral.rules}
              documents={pillarsData.behavioral.documents}
              onUpload={fetchGovernanceData}
              onToggleRule={handleRuleToggle}
              onEditRule={handleRuleEdit}
              onRuleAdded={fetchGovernanceData}
            />

            {/* Immutable governance status indicator - rules are enforced internally */}
            <div className="immutable-status-card">
              <div className="immutable-header">
                <div className="immutable-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    <path d="M9 12l2 2 4-4"/>
                  </svg>
                </div>
                <div className="immutable-info">
                  <h3>Safety & Compliance</h3>
                  <p>Core safety rules are always active and enforced automatically behind the scenes.</p>
                </div>
                <div className="immutable-badge">
                  <span className="active-indicator"></span>
                  Always Active
                </div>
              </div>
            </div>
          </div>
        )}

        {activeView === "decisions" && (
          <div className="decisions-view">
            <div className="decisions-intro">
              <h3>Human-in-the-Loop Decisions</h3>
              <p>Review and approve decisions that require human judgment. You can confirm, discuss, or deny each request.</p>
            </div>

            {pendingDecisions.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M9 12l2 2 4-4"/>
                  </svg>
                </div>
                <p>No pending decisions require your review</p>
              </div>
            ) : (
              <div className="decisions-list">
                {pendingDecisions.map((decision) => (
                  <DecisionCard
                    key={decision.id}
                    decision={decision}
                    onAction={handleDecisionAction}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {activeView === "history" && (
          <div className="history-view">
            <h3>Decision History</h3>
            <p>View past governance decisions and their outcomes.</p>

            <div className="history-filters">
              <select defaultValue="all">
                <option value="all">All Pillars</option>
                <option value="operational">Operational</option>
                <option value="behavioral">Behavioral</option>
                <option value="immutable">Immutable</option>
              </select>
              <select defaultValue="7d">
                <option value="24h">Last 24 hours</option>
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
                <option value="all">All time</option>
              </select>
            </div>

            <div className="history-list">
              <div className="history-item confirmed">
                <span className="history-status">CONFIRMED</span>
                <span className="history-title">API Integration Request</span>
                <span className="history-pillar">operational</span>
                <span className="history-date">2 hours ago</span>
              </div>
              <div className="history-item denied">
                <span className="history-status">DENIED</span>
                <span className="history-title">Disable Logging Request</span>
                <span className="history-pillar">immutable</span>
                <span className="history-date">5 hours ago</span>
              </div>
              <div className="history-item confirmed">
                <span className="history-status">CONFIRMED</span>
                <span className="history-title">Tone Adjustment</span>
                <span className="history-pillar">behavioral</span>
                <span className="history-date">1 day ago</span>
              </div>
            </div>
          </div>
        )}

        {activeView === "analytics" && (
          <div className="analytics-view">
            <h3>Governance Analytics</h3>

            <div className="analytics-grid">
              <div className="analytics-card">
                <h4>Decision Distribution</h4>
                <div className="distribution-bars">
                  <div className="bar-item">
                    <span className="bar-label">Confirmed</span>
                    <div className="bar-track">
                      <div className="bar-fill confirmed" style={{ width: "75%" }} />
                    </div>
                    <span className="bar-value">75%</span>
                  </div>
                  <div className="bar-item">
                    <span className="bar-label">Denied</span>
                    <div className="bar-track">
                      <div className="bar-fill denied" style={{ width: "15%" }} />
                    </div>
                    <span className="bar-value">15%</span>
                  </div>
                  <div className="bar-item">
                    <span className="bar-label">Discussed</span>
                    <div className="bar-track">
                      <div className="bar-fill discussed" style={{ width: "10%" }} />
                    </div>
                    <span className="bar-value">10%</span>
                  </div>
                </div>
              </div>

              <div className="analytics-card">
                <h4>Pillar Activity</h4>
                <div className="pillar-stats">
                  <div className="pillar-stat operational">
                    <span className="pillar-name">Operational</span>
                    <span className="pillar-count">45 decisions</span>
                  </div>
                  <div className="pillar-stat behavioral">
                    <span className="pillar-name">Behavioral</span>
                    <span className="pillar-count">23 decisions</span>
                  </div>
                  <div className="pillar-stat immutable">
                    <span className="pillar-name">Immutable</span>
                    <span className="pillar-count">12 blocks</span>
                  </div>
                </div>
              </div>

              <div className="analytics-card">
                <h4>Compliance Trend</h4>
                <div className="trend-indicator positive">
                  <span className="trend-arrow">↑</span>
                  <span className="trend-value">+2.3%</span>
                  <span className="trend-period">vs last week</span>
                </div>
              </div>

              <div className="analytics-card">
                <h4>Response Time</h4>
                <div className="response-stats">
                  <div className="response-stat">
                    <span className="response-label">Avg. Review Time</span>
                    <span className="response-value">4.2 min</span>
                  </div>
                  <div className="response-stat">
                    <span className="response-label">Auto-resolved</span>
                    <span className="response-value">67%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {showRuleEditor && (
        <RuleEditorModal
          rule={editingRule}
          onSave={handleRuleSave}
          onClose={() => {
            setShowRuleEditor(false);
            setEditingRule(null);
          }}
        />
      )}
    </div>
  );
}
