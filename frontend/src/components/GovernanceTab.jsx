import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#080814',
  bgAlt: '#12122a',
  accent: '#e94560',
  success: '#3fb950',
  text: '#eee',
  dim: '#888',
  border: '#222',
  highlight: '#2a2a4a',
  warn: '#d29922',
  error: '#f85149'
};

export default function GovernanceTab({ domain = "Global (All Domains)" }) {
  const [activeView, setActiveView] = useState("genesis");

  // Inline Styles
  const navBtnStyle = (active) => ({
    background: active ? C.highlight : 'transparent',
    color: active ? '#fff' : C.dim,
    border: 'none',
    padding: '12px 16px',
    textAlign: 'left',
    width: '100%',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: active ? 700 : 500,
    borderLeft: active ? `3px solid ${C.accent}` : '3px solid transparent',
    transition: 'all 0.2s'
  });

  return (
    <div style={{ display: 'flex', height: '100%', background: C.bg, overflow: 'hidden' }}>

      {/* Left Navigation */}
      <div style={{ width: 280, borderRight: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '24px 16px', borderBottom: `1px solid ${C.border}` }}>
          <h2 style={{ margin: 0, fontSize: 18, color: C.text, display: 'flex', alignItems: 'center', gap: 8 }}>
            🏛️ Governance
          </h2>
          <div style={{ fontSize: 12, color: C.dim, marginTop: 4 }}>System Oversight & Accountability</div>
        </div>

        <div style={{ flex: 1, padding: '16px 0', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <button onClick={() => setActiveView("genesis")} style={navBtnStyle(activeView === "genesis")}>
            ⧗ Genesis Decisions Hub
          </button>
          <button onClick={() => setActiveView("rules")} style={navBtnStyle(activeView === "rules")}>
            ⚖️ Rules Architect
          </button>
          <button onClick={() => setActiveView("persona")} style={navBtnStyle(activeView === "persona")}>
            🎭 Persona Manager
          </button>
          <button onClick={() => setActiveView("kpi")} style={navBtnStyle(activeView === "kpi")}>
            📊 KPI & Trust Dashboard
          </button>
          <button onClick={() => setActiveView("adaptive")} style={navBtnStyle(activeView === "adaptive")}>
            🧬 Adaptive Overrides (Meta)
          </button>
          <button onClick={() => setActiveView("schema")} style={navBtnStyle(activeView === "schema")}>
            🗄️ Schema Evolution
          </button>
        </div>

        <div style={{ padding: 16, borderTop: `1px solid ${C.border}`, fontSize: 11, color: C.dim }}>
          Active Target: <span style={{ color: C.accent, fontWeight: 700 }}>{domain}</span>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 32 }}>
        {activeView === "genesis" && <GenesisDecisionsHub domain={domain} />}
        {activeView === "rules" && <RulesArchitect domain={domain} />}
        {activeView === "persona" && <PersonaManager domain={domain} />}
        {activeView === "kpi" && <KpiTrustDashboard domain={domain} />}
        {activeView === "adaptive" && <AdaptiveOverrides domain={domain} />}
        {activeView === "schema" && <SchemaEvolution domain={domain} />}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// 1. Genesis Decisions Hub
// ────────────────────────────────────────────────────────────────────────
function GenesisDecisionsHub() {
  const [selectedKey, setSelectedKey] = useState(null);
  const [keys, setKeys] = useState([]);

  const fetchApprovals = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v2/govern/approvals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.ok && data.data?.approvals) {
        setKeys(data.data.approvals.map(a => ({
          id: a.id,
          type: a.action_type || a.pillar_type || "Anomaly",
          status: a.status === 'pending' ? 'Blocked (Human needed)' : 'Resolved',
          title: a.title,
          timestamp: new Date(a.created_at || Date.now()).toLocaleString(),
          description: a.description
        })));
      }
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchApprovals();
  }, [fetchApprovals]);

  const handleAction = async (action) => {
    if (!selectedKey) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/v2/govern/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: selectedKey.id, action })
      });
      if (res.ok) {
        setSelectedKey(null);
        fetchApprovals();
      }
    } catch (e) { console.error(e); }
  };

  return (
    <div style={{ display: 'flex', height: '100%', gap: 24 }}>
      {/* List */}
      <div style={{ flex: '0 0 300px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h3 style={{ margin: 0, color: C.text, fontSize: 16 }}>Flagged Decisions</h3>
        {keys.map(k => (
          <div
            key={k.id}
            onClick={() => setSelectedKey(k)}
            style={{
              background: selectedKey?.id === k.id ? C.highlight : C.bgAlt,
              border: `1px solid ${selectedKey?.id === k.id ? C.accent : C.border}`,
              padding: 16, borderRadius: 8, cursor: 'pointer', transition: 'all 0.2s'
            }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 800, color: k.status.includes('Blocked') ? C.error : C.success }}>{k.status}</span>
              <span style={{ fontSize: 11, color: C.dim }}>{k.timestamp}</span>
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 4 }}>{k.title}</div>
            <div style={{ fontSize: 12, color: C.dim, fontFamily: 'monospace' }}>{k.id}</div>
          </div>
        ))}
      </div>

      {/* Detail Area */}
      <div style={{ flex: 1, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 24, display: 'flex', flexDirection: 'column' }}>
        {!selectedKey ? (
          <div style={{ margin: 'auto', textAlign: 'center', color: C.dim }}>
            <div style={{ fontSize: 32, marginBottom: 16 }}>⧗</div>
            <div>Select a Genesis Key to view lineage and resolve blockers.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
            <div style={{ borderBottom: `1px solid ${C.border}`, paddingBottom: 16, marginBottom: 16 }}>
              <h2 style={{ margin: '0 0 8px 0', color: '#fff' }}>{selectedKey.title}</h2>
              <div style={{ display: 'flex', gap: 16, fontSize: 12, color: C.dim }}>
                <span>ID: <strong style={{ color: C.accent }}>{selectedKey.id}</strong></span>
                <span>Type: <strong>{selectedKey.type}</strong></span>
              </div>
            </div>

            <div style={{ display: 'flex', flex: 1, gap: 24, overflow: 'hidden' }}>
              {/* Left Column: Lineage & Report */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16, overflowY: 'auto', paddingRight: 8 }}>
                <div style={{ background: C.bg, padding: 16, borderRadius: 6, border: `1px solid ${C.border}` }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: C.text, marginBottom: 12 }}>BRANCH LINEAGE (DECISION TREE)</div>
                  <div style={{ fontSize: 12, color: C.dim, paddingLeft: 12, borderLeft: `2px solid ${C.border}` }}>
                    <div style={{ marginBottom: 8 }}>⚬ 14:02 - Automated Agent requested schema drop</div>
                    <div style={{ marginBottom: 8 }}>⚬ 14:02 - Global Rule "Protect Prod DB" intercepted</div>
                    <div style={{ color: C.error, fontWeight: 700 }}>⚬ 14:03 - Execution Halted. Human approval required.</div>
                  </div>
                </div>

                <div style={{ background: C.bg, padding: 16, borderRadius: 6, border: `1px solid ${C.warn}`, position: 'relative' }}>
                  <div style={{ fontSize: 10, background: C.warn, color: '#000', padding: '2px 8px', borderRadius: 4, position: 'absolute', top: -10, left: 16, fontWeight: 800 }}>LLM REPORT</div>
                  <div style={{ fontSize: 13, color: '#ccc', lineHeight: 1.5, marginTop: 8 }}>
                    {selectedKey.description}
                  </div>
                </div>
              </div>

              {/* Right Column: Scoped Chat */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, overflow: 'hidden' }}>
                <div style={{ padding: '8px 12px', background: C.highlight, fontSize: 11, fontWeight: 800, color: '#fff', borderBottom: `1px solid ${C.border}` }}>
                  SCOPED RESOLUTION CHAT
                </div>
                <div style={{ flex: 1, padding: 16, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ alignSelf: 'flex-start', background: C.bgAlt, padding: '8px 12px', borderRadius: 8, fontSize: 13, border: `1px solid ${C.border}`, maxWidth: '85%' }}>
                    How would you like to handle {selectedKey.id}? The agent is waiting for your decision.
                  </div>
                </div>
                <div style={{ padding: 12, borderTop: `1px solid ${C.border}`, background: C.bgAlt }}>
                  <input type="text" placeholder="Discuss the decision here..." style={{ width: '100%', padding: '10px 12px', background: C.bg, border: `1px solid ${C.border}`, color: C.text, borderRadius: 4, fontSize: 13, outline: 'none', boxSizing: 'border-box' }} />
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
                    <button onClick={() => handleAction('rejected')} style={{ background: C.error, color: '#fff', border: 'none', padding: '6px 12px', borderRadius: 4, fontSize: 12, cursor: 'pointer', fontWeight: 700 }}>Reject Agent Action</button>
                    <button onClick={() => handleAction('approved')} style={{ background: C.success, color: '#fff', border: 'none', padding: '6px 12px', borderRadius: 4, fontSize: 12, cursor: 'pointer', fontWeight: 700 }}>Override & Approve</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// 2. Rules Architect
// ────────────────────────────────────────────────────────────────────────
function RulesArchitect({ domain }) {
  const isGlobal = domain.includes("Global");



  const fetchRules = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v2/govern/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.ok && data.data?.documents) {
        const docs = data.data.documents;
        const _globals = docs.filter(d => d.category === 'global');
        const _locals = docs.filter(d => d.category !== 'global');
      }
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules, domain]);

  return (
    <div style={{ display: 'flex', height: '100%', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', gap: 24, flex: 1 }}>

        {/* Global Rules */}
        <div style={{ flex: 1, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 24, display: 'flex', flexDirection: 'column' }}>
          <div style={{ borderBottom: `1px solid ${C.border}`, paddingBottom: 16, marginBottom: 16 }}>
            <h2 style={{ margin: 0, color: '#fff', fontSize: 18 }}>🌐 Global Laws</h2>
            <div style={{ fontSize: 12, color: C.dim, marginTop: 4 }}>Universal constraints that apply to the entire Grace system. Cannot be overridden lightly.</div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <ul style={{ color: C.text, fontSize: 13, lineHeight: 1.6, paddingLeft: 20 }}>
              <li><strong>Do no harm:</strong> Operations must not execute deletion on active production environments without cryptographic approval.</li>
              <li><strong>Uptime Constraint:</strong> APIs must maintain a 99.9% uptime response threshold; aggressive tasks should spawn to background workers.</li>
            </ul>
          </div>
          <div style={{ border: `2px dashed ${C.border}`, borderRadius: 8, padding: 20, textAlign: 'center', background: C.bg, cursor: 'pointer', marginTop: 16 }}>
            <div style={{ fontSize: 20, marginBottom: 4 }}>📄</div>
            <div style={{ fontSize: 13, color: C.text, fontWeight: 600 }}>Drag & Drop Global Policy Documents</div>
            <div style={{ fontSize: 11, color: C.dim }}>PDFs or Text. These become foundational laws.</div>
          </div>
        </div>

        {/* Localized Rules */}
        <div style={{ flex: 1, background: C.bgAlt, border: `1px solid ${isGlobal ? C.border : C.accent}`, borderRadius: 8, padding: 24, display: 'flex', flexDirection: 'column' }}>
          <div style={{ borderBottom: `1px solid ${C.border}`, paddingBottom: 16, marginBottom: 16 }}>
            <h2 style={{ margin: 0, color: '#fff', fontSize: 18 }}>📁 Localized Laws ({domain})</h2>
            <div style={{ fontSize: 12, color: C.dim, marginTop: 4 }}>Contextual project constraints bound strictly by the Global Laws above.</div>
          </div>

          {isGlobal ? (
            <div style={{ margin: 'auto', textAlign: 'center', color: C.dim }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>🔒</div>
              <div>Select a specific Domain from the top navigation to set localized rules.</div>
            </div>
          ) : (
            <>
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <ul style={{ color: C.text, fontSize: 13, lineHeight: 1.6, paddingLeft: 20 }}>
                  <li><strong>Styling:</strong> Use TailwindCSS for all frontend components in this project.</li>
                  <li><strong>Deploy Target:</strong> All code in this folder pushes to the Staging AWS environment ONLY.</li>
                </ul>
              </div>
              <div style={{ border: `2px dashed ${C.accent}`, borderRadius: 8, padding: 20, textAlign: 'center', background: C.bg, cursor: 'pointer', marginTop: 16 }}>
                <div style={{ fontSize: 20, marginBottom: 4 }}>📄</div>
                <div style={{ fontSize: 13, color: C.text, fontWeight: 600 }}>Drag & Drop Local Docs</div>
                <div style={{ fontSize: 11, color: C.dim }}>Anchors constraints specifically to this domain.</div>
              </div>
            </>
          )}
        </div>

      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// 3. Persona Manager
// ────────────────────────────────────────────────────────────────────────
function PersonaManager() {
  const [personal, setPersonal] = useState("Loading...");
  const [professional, setProfessional] = useState("Loading...");


  const fetchPersona = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v2/govern/persona`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.ok) {
        setPersonal(data.data.personal || "");
        setProfessional(data.data.professional || "");
      }
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchPersona();
  }, [fetchPersona]);

  const handleSave = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v2/govern/update_persona`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ personal, professional })
      });
      if (res.ok) alert("Persona saved successfully.");
    } catch (e) { console.error(e); }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 24 }}>
        <h2 style={{ margin: '0 0 8px 0', color: '#fff', fontSize: 18 }}>🎭 Personal Persona</h2>
        <div style={{ fontSize: 12, color: C.dim, marginBottom: 16 }}>Defines how Grace interacts with you privately during pair-programming, brainstorming, and system management.</div>
        <textarea
          value={personal}
          onChange={(e) => setPersonal(e.target.value)}
          style={{ width: '100%', height: 120, background: C.bg, border: `1px solid ${C.border}`, color: C.text, padding: 12, borderRadius: 6, fontSize: 13, fontFamily: 'monospace', outline: 'none', resize: 'vertical', boxSizing: 'border-box' }}
        />
      </div>

      <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 24 }}>
        <h2 style={{ margin: '0 0 8px 0', color: '#fff', fontSize: 18 }}>👔 Professional Persona</h2>
        <div style={{ fontSize: 12, color: C.dim, marginBottom: 16 }}>Defines outbound communications: emails, external document generation, polished client-facing code summaries.</div>
        <textarea
          value={professional}
          onChange={(e) => setProfessional(e.target.value)}
          style={{ width: '100%', height: 120, background: C.bg, border: `1px solid ${C.border}`, color: C.text, padding: 12, borderRadius: 6, fontSize: 13, fontFamily: 'monospace', outline: 'none', resize: 'vertical', boxSizing: 'border-box' }}
        />
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button onClick={handleSave} style={{ background: C.success, color: '#fff', border: 'none', padding: '10px 24px', borderRadius: 6, fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>
          Save Persona Configurations
        </button>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// 4. KPI & Trust Score Dashboard
// ────────────────────────────────────────────────────────────────────────
function KpiTrustDashboard({ domain }) {
  const [_score, setScore] = useState("94.2%");
  const [kpis, setKpis] = useState([
    { name: "Global Trust Score", val: "94.2%", status: "healthy", desc: "Cumulative system confidence" },
    { name: "Code Quality Index", val: "98.1%", status: "healthy", desc: "Test coverage & strict typing adherence" },
    { name: "Retrieval Accuracy", val: "91.5%", status: "healthy", desc: "RAG query relevance in chats" },
    { name: "Dev Agent Efficiency", val: "76.4%", status: "degrading", desc: "Speed of resolving multi-file tickets" }
  ]);


  const fetchScores = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v2/govern/scores`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.ok && data.data?.trust_score !== undefined) {
        const trust = (data.data.trust_score * 100).toFixed(1) + "%";
        setScore(trust);
        setKpis(prev => {
          const newKpis = [...prev];
          newKpis[0].val = trust;
          return newKpis;
        });
      }
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchScores();
  }, [fetchScores, domain]);

  return (
    <div style={{ padding: 40, flex: 1, overflowY: 'auto' }}>
      <h2 style={{ margin: '0 0 8px 0', color: '#fff', fontSize: 24 }}>KPI & Trust Score Dashboard</h2>
      <div style={{ fontSize: 13, color: C.dim, marginBottom: 32 }}>Real-time telemetry measuring system efficiency and adherence to constraints in the {domain} scope.</div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 24 }}>
        {kpis.map((k, i) => (
          <div key={i} style={{ background: C.bgAlt, border: `1px solid ${k.status === 'degrading' ? C.warn : C.border}`, padding: 24, borderRadius: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>{k.name}</div>
              <div style={{ fontSize: 10, background: k.status === 'degrading' ? C.warn : C.success, color: k.status === 'degrading' ? '#000' : '#fff', padding: '2px 8px', borderRadius: 12, fontWeight: 800, textTransform: 'uppercase' }}>
                {k.status}
              </div>
            </div>
            <div style={{ fontSize: 36, fontWeight: 800, color: k.status === 'degrading' ? C.warn : C.accent, marginBottom: 8 }}>{k.val}</div>
            <div style={{ fontSize: 12, color: C.dim, lineHeight: 1.4 }}>{k.desc}</div>

            {k.status === 'degrading' && (
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: `1px solid ${C.border}`, display: 'flex', gap: 8 }}>
                <button style={{ flex: 1, background: C.accent, color: '#fff', border: 'none', padding: '8px', borderRadius: 4, fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Trigger Self-Healing</button>
                <button style={{ flex: 1, background: 'transparent', color: C.text, border: `1px solid ${C.border}`, padding: '8px', borderRadius: 4, fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>Trigger Self-Learning</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// 5. Adaptive Overrides (Meta-Learning)
// ────────────────────────────────────────────────────────────────────────
function AdaptiveOverrides({ domain }) {
  const [selectedLog, setSelectedLog] = useState(null);
  const [logs, setLogs] = useState([]);

  const fetchOverrides = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v2/govern/adaptive_overrides`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.ok && data.data?.overrides) {
        setLogs(data.data.overrides.map(o => ({
          ...o,
          id: o.override_id,
          timestamp: new Date(o.created_at || Date.now()).toLocaleString()
        })));
      }
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchOverrides();
  }, [fetchOverrides, domain]);

  const handleApprove = async (action) => {
    if (!selectedLog) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/v2/govern/approve_override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ override_id: selectedLog.id, action })
      });
      if (res.ok) {
        alert(action === "approved" ? "Rule globally applied and anchored." : "Logged as exception.");
        fetchOverrides();
        setSelectedLog(null);
      }
    } catch (e) { console.error(e); }
  };

  return (
    <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

      {/* Inbox / Log List */}
      <div style={{ width: 320, borderRight: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '16px 24px', borderBottom: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: '#fff' }}>OVERRIDE HISTORY</div>
          <div style={{ fontSize: 11, color: C.dim, marginTop: 4 }}>Manual user rule-breaks</div>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {logs.map(log => (
            <div
              key={log.id}
              onClick={() => setSelectedLog(log)}
              style={{
                background: selectedLog?.id === log.id ? C.highlight : C.bg,
                border: `1px solid ${selectedLog?.id === log.id ? C.accent : C.border}`,
                padding: 16, borderRadius: 8, cursor: 'pointer', transition: 'all 0.1s'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: C.accent, fontWeight: 800, fontFamily: 'monospace' }}>{log.id}</span>
                <span style={{ fontSize: 10, color: C.dim }}>{log.timestamp}</span>
              </div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#fff', marginBottom: 4 }}>{log.context}</div>
              <div style={{ fontSize: 11, color: C.muted }}>Override: {log.user_action}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Analysis & Proposal Engine */}
      <div style={{ flex: 1, padding: 32, background: C.bg, overflowY: 'auto' }}>
        {!selectedLog ? (
          <div style={{ margin: 'auto', textAlign: 'center', color: C.dim, marginTop: 100 }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🧬</div>
            <div style={{ fontSize: 14 }}>Select an override log to analyze Grace's rule evolution proposals.</div>
          </div>
        ) : (
          <div style={{ maxWidth: 700 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
              <h2 style={{ margin: 0, color: '#fff', fontSize: 24 }}>Anomaly Analysis: {selectedLog.context}</h2>
              <div style={{ fontSize: 11, color: C.dim, fontFamily: 'monospace', padding: '4px 8px', background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 4 }}>{selectedLog.genesis_key}</div>
            </div>

            {/* The Override Facts */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
              <div style={{ flex: 1, background: C.bgAlt, border: `1px solid ${C.border}`, padding: 16, borderRadius: 8 }}>
                <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', fontWeight: 800, marginBottom: 4 }}>System Rule Broken</div>
                <div style={{ fontSize: 13, color: '#fff' }}>{selectedLog.rule_broken}</div>
                <div style={{ fontSize: 12, color: C.error, marginTop: 4 }}>Actual: {selectedLog.actual_metric}</div>
              </div>
              <div style={{ flex: 1, background: C.highlight, border: `1px solid ${C.accent}`, padding: 16, borderRadius: 8 }}>
                <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', fontWeight: 800, marginBottom: 4 }}>User Action (Override)</div>
                <div style={{ fontSize: 13, color: '#fff', fontWeight: 700 }}>{selectedLog.user_action}</div>
              </div>
            </div>

            {/* AI Synthesis */}
            <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 24, marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                <span style={{ fontSize: 18 }}>🧠</span>
                <span style={{ fontSize: 12, fontWeight: 800, color: C.text, textTransform: 'uppercase' }}>Grace's Meta-Learning Synthesis</span>
              </div>
              <div style={{ fontSize: 14, color: C.muted, lineHeight: 1.6, fontStyle: 'italic' }}>
                "{selectedLog.llm_analysis}"
              </div>
            </div>

            {/* Proposed Rule Evolution */}
            <div style={{ background: '#1c1c14', border: `1px solid ${C.warn}`, borderRadius: 8, padding: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 800, color: C.warn, textTransform: 'uppercase' }}>Rule Evolution Proposal</div>
              </div>
              <textarea
                defaultValue={selectedLog.proposed_rule}
                style={{ width: '100%', background: '#0a0a07', color: '#ffebc2', border: `1px solid ${C.warn}`, borderRadius: 6, padding: 16, fontSize: 14, fontFamily: 'monospace', resize: 'vertical', minHeight: 80, outline: 'none', lineHeight: 1.5, boxSizing: 'border-box' }}
              />

              <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
                <button onClick={() => handleApprove('approved')} style={{ background: C.success, color: '#fff', border: 'none', padding: '10px 20px', borderRadius: 4, fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
                  ✓ Approve as Standing Rule
                </button>
                <button onClick={() => handleApprove('exception')} style={{ background: C.bgAlt, color: C.text, border: `1px solid ${C.border}`, padding: '10px 20px', borderRadius: 4, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                  Keep as One-Time Exception
                </button>
              </div>
            </div>

          </div>
        )}
      </div>

    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// 6. Schema Evolution
// ────────────────────────────────────────────────────────────────────────
function SchemaEvolution({ domain }) {
  const [selectedProposal, setSelectedProposal] = useState(null);
  const [proposals, setProposals] = useState([]);

  const fetchProposals = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/schema-evolution/proposals`);
      const data = await res.json();
      if (data.proposals) {
        setProposals(data.proposals.map(p => ({
          ...p,
          id: p.proposal_id,
          timestamp: new Date(p.created_at || Date.now()).toLocaleString()
        })));
      }
    } catch (e) {
      console.error("Failed to fetch proposals", e);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchProposals();
  }, [fetchProposals, domain]);

  const handleAction = async (action) => {
    if (!selectedProposal) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/schema-evolution/proposals/${selectedProposal.id}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (res.ok) {
        alert(action === "approve" ? "Schema Migrated Live." : "Proposal Rejected.");
        fetchProposals();
        setSelectedProposal(null);
      } else {
        alert("Failed: " + data.detail);
      }
    } catch (e) {
      alert("Error executing action.");
      console.error(e);
    }
  };

  const statusColor = (status) => {
    if (status === 'pending') return C.warn;
    if (status === 'approved') return C.success;
    if (status === 'rejected') return C.dim;
    return C.error;
  };

  return (
    <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

      {/* Inbox / Log List */}
      <div style={{ width: 320, borderRight: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '16px 24px', borderBottom: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: '#fff' }}>SCHEMA PROPOSALS</div>
          <div style={{ fontSize: 11, color: C.dim, marginTop: 4 }}>Autonomous Database Migrations</div>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {proposals.map(prop => (
            <div
              key={prop.id}
              onClick={() => setSelectedProposal(prop)}
              style={{
                background: selectedProposal?.id === prop.id ? C.highlight : C.bg,
                border: `1px solid ${selectedProposal?.id === prop.id ? C.accent : C.border}`,
                padding: 16, borderRadius: 8, cursor: 'pointer', transition: 'all 0.1s'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: statusColor(prop.status), fontWeight: 800, textTransform: 'uppercase' }}>{prop.status}</span>
                <span style={{ fontSize: 10, color: C.dim }}>{prop.timestamp}</span>
              </div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#fff', marginBottom: 4 }} title={prop.trigger_reason}>
                {prop.trigger_reason.substring(0, 40) + "..."}
              </div>
              <div style={{ fontSize: 11, color: C.muted, fontFamily: 'monospace' }}>{prop.id}</div>
            </div>
          ))}
          {proposals.length === 0 && (
            <div style={{ fontSize: 12, color: C.dim, textAlign: 'center', marginTop: 32 }}>No schema proposals logged.</div>
          )}
        </div>
      </div>

      {/* Analysis & execution view */}
      <div style={{ flex: 1, padding: 32, background: C.bg, overflowY: 'auto' }}>
        {!selectedProposal ? (
          <div style={{ margin: 'auto', textAlign: 'center', color: C.dim, marginTop: 100 }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🗄️</div>
            <div style={{ fontSize: 14 }}>Select a schema evolution proposal to review AST constraints.</div>
          </div>
        ) : (
          <div style={{ maxWidth: 800 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
              <div>
                <h2 style={{ margin: 0, color: '#fff', fontSize: 24 }}>Evolve Database Schema</h2>
                <div style={{ fontSize: 13, color: statusColor(selectedProposal.status), fontWeight: 800, marginTop: 8, textTransform: 'uppercase' }}>
                  Status: {selectedProposal.status}
                </div>
              </div>
              <div style={{ fontSize: 11, color: C.dim, fontFamily: 'monospace', padding: '4px 8px', background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 4 }}>{selectedProposal.id}</div>
            </div>

            <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, padding: 20, borderRadius: 8, marginBottom: 24 }}>
              <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', fontWeight: 800, marginBottom: 8 }}>Trigger Reason / Analysis</div>
              <div style={{ fontSize: 14, color: '#fff', lineHeight: 1.5 }}>{selectedProposal.trigger_reason}</div>
            </div>

            <div style={{ background: '#1c1c14', border: `1px solid ${C.warn}`, borderRadius: 8, padding: 24, marginBottom: 24 }}>
              <div style={{ fontSize: 12, fontWeight: 800, color: C.warn, textTransform: 'uppercase', marginBottom: 16 }}>Proposed SQLAlchemy Core Expansion</div>

              <div style={{ background: '#0a0a07', padding: 16, borderRadius: 6, border: `1px solid ${C.border}`, overflowX: 'auto' }}>
                <pre style={{ margin: 0, fontSize: 13, color: '#ffebc2', fontFamily: 'monospace', lineHeight: 1.5 }}>
                  {selectedProposal.proposed_code}
                </pre>
              </div>

              {selectedProposal.status === 'pending' && (
                <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
                  <button onClick={() => handleAction('approve')} style={{ background: C.success, color: '#fff', border: 'none', padding: '10px 20px', borderRadius: 4, fontSize: 13, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span>✓</span> Approve & Execute Migration
                  </button>
                  <button onClick={() => handleAction('reject')} style={{ background: C.bgAlt, color: C.text, border: `1px solid ${C.border}`, padding: '10px 20px', borderRadius: 4, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                    Reject Proposal
                  </button>
                </div>
              )}
            </div>

            {selectedProposal.execution_logs && (
              <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 20 }}>
                <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', fontWeight: 800, marginBottom: 8 }}>Migration Execution Trace</div>
                <div style={{ fontSize: 12, color: '#ccc', fontFamily: 'monospace', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                  {selectedProposal.execution_logs}
                </div>
              </div>
            )}

          </div>
        )}
      </div>
    </div>
  );
}
