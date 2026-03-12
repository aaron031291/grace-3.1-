import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
    bg: '#080814',
    bgAlt: '#12122a',
    accent: '#e94560',
    success: '#3fb950',
    text: '#eee',
    dim: '#888',
    border: '#222'
};

export default function GenesisTimeline({ domain, onClose }) {
    const [timeline, setTimeline] = useState([]);
    const [loading, setLoading] = useState(true);
    const [revertingTo, setRevertingTo] = useState(null);

    useEffect(() => {
        // Fetch timeline from backend
        fetch(`${API_BASE_URL}/api/genesis/timeline?domain=${encodeURIComponent(domain)}`)
            .then(r => r.ok ? r.json() : { timeline: [] }) // Fallback mock if backend not ready
            .then(d => {
                if (d.timeline && d.timeline.length > 0) {
                    setTimeline(d.timeline);
                } else {
                    // Mock data for UI demonstration until backend is hooked up
                    setTimeline([
                        { version: 'v1.2', genesis_key: 'gk_7f8a9b2', timestamp: new Date().toISOString(), trigger: 'Fix login button alignment', status: 'active', diff: '+12 lines, -4 lines' },
                        { version: 'v1.1', genesis_key: 'gk_3c4d5e6', timestamp: new Date(Date.now() - 3600000).toISOString(), trigger: 'Add social auth providers', status: 'superseded', diff: '+142 lines, -10 lines' },
                        { version: 'v1.0', genesis_key: 'gk_0a1b2c3', timestamp: new Date(Date.now() - 86400000).toISOString(), trigger: 'Initial Component Genesis', status: 'superseded', diff: 'Initial Creation' },
                    ]);
                }
                setLoading(false);
            })
            .catch(() => {
                setLoading(false);
            });
    }, [domain]);

    const handleRevert = async (version) => {
        if (!window.confirm(`Are you sure you want to revert to ${version.version} (${version.genesis_key})? This will create a new Genesis Block as a linear progression.`)) return;

        setRevertingTo(version.genesis_key);
        try {
            const res = await fetch(`${API_BASE_URL}/api/genesis/revert`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ domain, target_genesis_key: version.genesis_key })
            });
            if (res.ok) {
                alert(`Successfully mapped reversion to ${version.version}. Please wait for Grace to execute the reversion playbook.`);
                onClose();
            } else {
                alert('Revert backend endpoint not fully implemented yet for this domain. See Phase 13 backend tasks.');
            }
        } catch (e) {
            alert('Error connecting to backend.');
        } finally {
            setRevertingTo(null);
        }
    };

    return (
        <div style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', zIndex: 9999,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
            <div style={{
                background: C.bgAlt, width: 500, maxHeight: '80vh', borderRadius: 12, border: `1px solid ${C.border}`,
                display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
            }}>
                {/* Header */}
                <div style={{ padding: '16px 20px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: C.bg }}>
                    <div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: C.text }}>Genesis Version Control</div>
                        <div style={{ fontSize: 12, color: C.accent, marginTop: 4 }}>Immutable Linear Timeline: {domain}</div>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', color: C.dim, fontSize: 20, cursor: 'pointer' }}>✕</button>
                </div>

                {/* Timeline body */}
                <div style={{ padding: 20, overflowY: 'auto', flex: 1, position: 'relative' }}>
                    {loading ? (
                        <div style={{ color: C.dim, textAlign: 'center', padding: 40 }}>Loading timeline...</div>
                    ) : (
                        <div style={{ position: 'relative', paddingLeft: 24 }}>
                            {/* Vertical line */}
                            <div style={{ position: 'absolute', left: 7, top: 10, bottom: 10, width: 2, background: C.border }} />

                            {timeline.map((item, i) => (
                                <div key={item.genesis_key} style={{ position: 'relative', marginBottom: 24 }}>
                                    {/* Node dot */}
                                    <div style={{
                                        position: 'absolute', left: -22, top: 6, width: 10, height: 10, borderRadius: '50%',
                                        background: item.status === 'active' ? C.success : C.dim,
                                        border: `2px solid ${C.bgAlt}`, boxShadow: `0 0 0 2px ${item.status === 'active' ? C.success : C.border}`
                                    }} />

                                    <div style={{
                                        background: C.bg, padding: 12, borderRadius: 8, border: `1px solid ${item.status === 'active' ? C.success : C.border}`,
                                        opacity: item.status === 'active' ? 1 : 0.7
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                <span style={{ fontSize: 14, fontWeight: 800, color: item.status === 'active' ? C.success : C.text }}>{item.version}</span>
                                                <span style={{ fontSize: 10, fontFamily: 'monospace', padding: '2px 6px', background: C.bgAlt, borderRadius: 4, color: C.accent }}>{item.genesis_key}</span>
                                            </div>
                                            <span style={{ fontSize: 10, color: C.dim }}>{new Date(item.timestamp).toLocaleString()}</span>
                                        </div>

                                        <div style={{ fontSize: 12, color: C.text, marginBottom: 8 }}>
                                            <span style={{ color: C.dim }}>Trigger:</span> {item.trigger}
                                        </div>

                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span style={{ fontSize: 11, color: C.dim }}>Diff: {item.diff}</span>

                                            {item.status !== 'active' && (
                                                <button
                                                    onClick={() => handleRevert(item)}
                                                    disabled={revertingTo === item.genesis_key}
                                                    style={{
                                                        background: revertingTo === item.genesis_key ? C.dim : C.accent,
                                                        color: '#fff', border: 'none', padding: '4px 10px', borderRadius: 4,
                                                        fontSize: 10, fontWeight: 700, cursor: 'pointer', transition: 'background 0.2s'
                                                    }}
                                                >
                                                    {revertingTo === item.genesis_key ? 'Reverting...' : 'Revert'}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
