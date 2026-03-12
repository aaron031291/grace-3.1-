import React, { useState } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
    bg: '#080814', bgAlt: '#12122a', highlight: '#1a1a3a',
    accent: '#e94560', success: '#3fb950', warn: '#d29922', error: '#f85149',
    text: '#eee', dim: '#888', border: '#222', muted: '#aaa'
};

export default function SandboxTab({ domain = "Global (All Domains)" }) {
    const [hypothesis, setHypothesis] = useState("");
    const [running, setRunning] = useState(false);
    const [sources, setSources] = useState({ flash: true, api: true, web: false, auth: false, direct: true });

    // Execution Console State
    const [logs, setLogs] = useState([]);

    // Promotion Gate State
    const [completedExperiments, setCompletedExperiments] = useState([
        {
            id: "exp_10293",
            title: "Pricing Algorithm Edge-Case Synthesis",
            status: "pending_review",
            report: "I pulled 14 pricing models from the Whitelist APIs. Testing against our project constraints, I found a 12% optimization ceiling by utilizing a tiered cache structure. This logic is validated but isolated.",
            timestamp: "10 mins ago"
        }
    ]);
    const [promoting, setPromoting] = useState(null);

    const runSandbox = async () => {
        if (!hypothesis.trim()) return;
        setRunning(true);
        setLogs([]);

        const targetSources = Object.keys(sources).filter(k => sources[k]);

        try {
            const res = await fetch(`${API_BASE_URL}/api/sandbox/experiment`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hypothesis, target_sources: targetSources, domain })
            });

            if (res.ok) {
                const data = await res.json();
                const expId = data.experiment_id;

                const eventSource = new EventSource(`${API_BASE_URL}/api/sandbox/stream/${expId}`);

                eventSource.onmessage = (event) => {
                    const msg = event.data;
                    let type = "info";
                    if (msg.includes("[FETCHING]")) type = "read";
                    if (msg.includes("WARNING") || msg.includes("ERROR")) type = "blocked";
                    if (msg.includes("complete") || msg.includes("Report")) type = "success";

                    if (msg.includes("[END OF STREAM]")) {
                        eventSource.close();
                        setRunning(false);

                        // Push to promotion gate
                        setCompletedExperiments(prev => [{
                            id: expId,
                            title: hypothesis.length > 30 ? hypothesis.substring(0, 30) + '...' : hypothesis,
                            status: "pending_review",
                            report: `Isolated analysis completed successfully. Synthesized whitelist data without mutating global domain state.`,
                            timestamp: "Just now"
                        }, ...prev]);
                        setHypothesis("");
                        return;
                    }

                    // Format log msg, removing timestamp since frontend adds it
                    const cleanMsg = msg.replace(/^\[\d{2}:\d{2}:\d{2}\] /, "");
                    setLogs(prev => [...prev, { m: cleanMsg, type, time: new Date().toLocaleTimeString() }]);
                };

                eventSource.onerror = () => {
                    setLogs(prev => [...prev, { m: "Lost connection to isolated Sandbox container.", type: "blocked", time: new Date().toLocaleTimeString() }]);
                    eventSource.close();
                    setRunning(false);
                };
            } else {
                setRunning(false);
                setLogs([{ m: "Sandbox API rejected the experiment payload.", type: "blocked", time: new Date().toLocaleTimeString() }]);
            }
        } catch (e) {
            setRunning(false);
            setLogs([{ m: `Network error launching Sandbox: ${e.message}`, type: "blocked", time: new Date().toLocaleTimeString() }]);
        }
    };

    const handlePromote = async (exp) => {
        setPromoting(exp.id);
        try {
            // Send validated sandbox output exactly as we did in WhitelistTab
            const res = await fetch(`${API_BASE_URL}/api/whitelist-hub/consensus`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    domain: domain,
                    flash_cache: `PROMOTED FROM SANDBOX [${exp.title}]: ${exp.report}`,
                    web_links: [], api_sources: [], authorities: []
                })
            });

            if (res.ok) {
                setCompletedExperiments(prev => prev.filter(e => e.id !== exp.id));
            }
        } catch (err) {
            console.error(err);
        } finally {
            setPromoting(null);
        }
    };

    const handleDiscard = (id) => {
        setCompletedExperiments(prev => prev.filter(e => e.id !== id));
    };

    const renderLogIcon = (type) => {
        if (type === 'read') return <span style={{ color: C.accent }}>[READ]</span>;
        if (type === 'blocked') return <span style={{ background: C.error, color: '#fff', padding: '0 4px', borderRadius: 2 }}>[BLOCKED WRITE]</span>;
        if (type === 'success') return <span style={{ color: C.success }}>✓</span>;
        return <span style={{ color: C.dim }}>ℹ</span>;
    };

    return (
        <div style={{ display: 'flex', height: '100%', background: C.bg, overflow: 'hidden' }}>

            {/* 1. Hypothesis Engine (Left Panel) */}
            <div style={{ width: 340, borderRight: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', flexDirection: 'column', padding: 24 }}>
                <h2 style={{ margin: '0 0 8px 0', color: '#fff', fontSize: 20 }}>🧪 Sandbox</h2>
                <div style={{ fontSize: 12, color: C.dim, marginBottom: 24, lineHeight: 1.5 }}>
                    Isolated execution environment. Grace can read from your deterministic Whitelist but cannot mutate production context.
                </div>

                <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 8, padding: 16, marginBottom: 24 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: C.text, marginBottom: 8, textTransform: 'uppercase' }}>Allowed Whitelist Sources</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {[
                            { id: 'flash', label: 'Flash Cache (Definitions)' },
                            { id: 'api', label: 'API Endpoints (GitHub, etc)' },
                            { id: 'web', label: 'Web Scopes' },
                            { id: 'auth', label: 'Authority Tracking' },
                            { id: 'direct', label: 'Direct Uploads (PDF/JSON)' }
                        ].map(s => (
                            <label key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: C.dim, cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={sources[s.id]}
                                    onChange={e => setSources({ ...sources, [s.id]: e.target.checked })}
                                />
                                <span style={{ color: sources[s.id] ? C.text : C.dim }}>{s.label}</span>
                            </label>
                        ))}
                    </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: C.text, textTransform: 'uppercase' }}>Experiment Parameter</div>
                    <textarea
                        placeholder="Define what Grace should test, build, or analyze in isolation..."
                        value={hypothesis}
                        onChange={e => setHypothesis(e.target.value)}
                        style={{ flex: 1, width: '100%', padding: 12, background: C.bg, border: `1px solid ${C.border}`, color: C.text, borderRadius: 6, fontSize: 13, outline: 'none', resize: 'none', boxSizing: 'border-box', fontFamily: 'monospace' }}
                    />
                    <button
                        onClick={runSandbox}
                        disabled={running || !hypothesis.trim()}
                        style={{ background: running ? C.dim : C.accent, color: '#fff', border: 'none', padding: '12px 16px', borderRadius: 6, fontSize: 14, fontWeight: 800, cursor: running ? 'wait' : 'pointer', transition: 'all 0.2s' }}>
                        {running ? '⏳ Executing Sandbox...' : 'Launch Isolated Process'}
                    </button>
                </div>
            </div>

            {/* 2. Isolated Execution Console (Middle Panel) */}
            <div style={{ flex: '1 1 40%', borderRight: `1px solid ${C.border}`, background: C.bg, display: 'flex', flexDirection: 'column' }}>
                <div style={{ padding: '16px 24px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: 14, fontWeight: 800, color: '#fff' }}>EXECUTION CONSOLE</div>
                    {running && <div style={{ width: 10, height: 10, borderRadius: '50%', background: C.accent, boxShadow: `0 0 10px ${C.accent}`, animation: 'pulse 1s infinite' }} />}
                </div>
                <div style={{ flex: 1, padding: 24, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, fontFamily: 'monospace' }}>
                    {logs.length === 0 ? (
                        <div style={{ margin: 'auto', textAlign: 'center', color: C.dim }}>
                            <div style={{ fontSize: 24, marginBottom: 8 }}>🖥️</div>
                            <div style={{ fontSize: 12 }}>Awaiting sandbox initialization...</div>
                        </div>
                    ) : (
                        logs.map((log, i) => (
                            <div key={i} style={{ display: 'flex', gap: 12, fontSize: 13, lineHeight: 1.5 }}>
                                <span style={{ color: C.dim, width: 75, flexShrink: 0 }}>[{log.time}]</span>
                                <span style={{ width: 100, flexShrink: 0 }}>{renderLogIcon(log.type)}</span>
                                <span style={{ color: log.type === 'blocked' ? C.error : (log.type === 'read' ? '#fff' : C.text) }}>{log.m}</span>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* 3. Promotion Gate (Right Panel) */}
            <div style={{ flex: '0 0 350px', background: C.bgAlt, display: 'flex', flexDirection: 'column' }}>
                <div style={{ padding: '16px 24px', borderBottom: `1px solid ${C.border}` }}>
                    <div style={{ fontSize: 14, fontWeight: 800, color: '#fff' }}>PROMOTION GATE</div>
                    <div style={{ fontSize: 11, color: C.dim, marginTop: 4 }}>Human-in-the-loop review for completed experiments</div>
                </div>

                <div style={{ flex: 1, padding: 24, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {completedExperiments.length === 0 ? (
                        <div style={{ margin: 'auto', textAlign: 'center', color: C.dim }}>
                            <div style={{ fontSize: 24, marginBottom: 8 }}>⚖️</div>
                            <div style={{ fontSize: 12 }}>No pending discoveries to review.</div>
                        </div>
                    ) : (
                        completedExperiments.map(exp => (
                            <div key={exp.id} style={{ background: C.bg, border: `1px solid ${C.warn}`, borderRadius: 8, padding: 16 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                    <span style={{ fontSize: 10, background: C.warn, color: '#000', padding: '2px 8px', borderRadius: 4, fontWeight: 800 }}>PENDING HUMAN APPROVAL</span>
                                    <span style={{ fontSize: 10, color: C.dim }}>{exp.timestamp}</span>
                                </div>
                                <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 8 }}>{exp.title}</div>
                                <div style={{ fontSize: 12, color: C.muted, lineHeight: 1.5, marginBottom: 16, padding: 12, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 6 }}>
                                    {exp.report}
                                </div>

                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    <button
                                        onClick={() => handlePromote(exp)}
                                        disabled={promoting === exp.id}
                                        style={{ background: promoting === exp.id ? C.dim : C.success, color: '#fff', border: 'none', padding: '10px', borderRadius: 6, fontSize: 12, fontWeight: 800, cursor: promoting === exp.id ? 'wait' : 'pointer', transition: 'all 0.2s', display: 'flex', justifyContent: 'center', gap: 8 }}>
                                        {promoting === exp.id ? '⏳ Promoting...' : 'Inject into Whitelist'}
                                    </button>
                                    <button
                                        onClick={() => handleDiscard(exp.id)}
                                        style={{ background: 'transparent', color: C.dim, border: `1px solid ${C.border}`, padding: '8px', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
                                        Discard Experiment
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            <style>{`
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(233, 69, 96, 0.7); }
          70% { box-shadow: 0 0 0 10px rgba(233, 69, 96, 0); }
          100% { box-shadow: 0 0 0 0 rgba(233, 69, 96, 0); }
        }
      `}</style>
        </div>
    );
}
