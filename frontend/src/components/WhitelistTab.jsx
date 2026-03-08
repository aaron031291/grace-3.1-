import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#080814',
  bgAlt: '#12122a',
  accent: '#e94560',
  success: '#3fb950',
  text: '#eee',
  dim: '#888',
  border: '#222',
  highlight: '#2a2a4a'
};

export default function WhitelistTab({ domain = "Global" }) {
  const [flashQuery, setFlashQuery] = useState("");
  const [webLinks, setWebLinks] = useState([]);
  const [apiSources, setApiSources] = useState([]);
  const [authorities, setAuthorities] = useState([]);
  const [consensusRunning, setConsensusRunning] = useState(false);
  const [validatedKnowledge, setValidatedKnowledge] = useState([]);

  const fetchSources = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/whitelist-hub/sources?domain=${domain}`);
      if (res.ok) {
        const data = await res.json();
        const sources = data.sources || [];
        setWebLinks(sources.filter(s => s.type === 'web').map(s => ({ ...s, scope: 'site' })));
        setApiSources(sources.filter(s => s.type === 'api').map(s => ({ ...s, endpoint: s.url })));
        setAuthorities(sources.filter(s => s.type === 'authority').map(s => ({ ...s, web: s.url, video: "" })));
      }
    } catch (e) { console.error("Error fetching whitelist sources:", e); }
  };

  useEffect(() => {
    fetchSources();
  }, [domain]);

  const addSourceToBackend = async (type, name, url) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/whitelist-hub/sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, url, type, active: true, domain })
      });
      if (res.ok) fetchSources();
    } catch (e) { console.error(e); }
  };

  const addWebLink = () => {
    const defaultUrl = "https://newsite.com";
    addSourceToBackend('web', 'New Web Source', defaultUrl);
  };

  const addApiSource = () => {
    const defaultUrl = "https://api.newservice.com";
    addSourceToBackend('api', 'New API', defaultUrl);
  };

  const addAuthority = () => {
    const defaultUrl = "https://newguru.com";
    addSourceToBackend('authority', 'New Expert', defaultUrl);
  };

  const handleConsensus = async () => {
    setConsensusRunning(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/whitelist-hub/consensus`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          domain: domain,
          flash_cache: flashQuery,
          web_links: webLinks,
          api_sources: apiSources,
          authorities: authorities
        })
      });

      if (res.ok) {
        const data = await res.json();
        setValidatedKnowledge(data.validated_knowledge || []);
      } else {
        console.error('Failed to run consensus');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setConsensusRunning(false);
    }
  };

  // Inline Styles
  const layerStyle = { background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 20 };
  const headerStyle = { fontSize: 16, fontWeight: 800, color: C.text, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 };
  const inputStyle = { flex: 1, background: C.bg, border: `1px solid ${C.border}`, color: C.text, padding: '8px 12px', borderRadius: 4, fontSize: 13, outline: 'none' };
  const actionBtnStyle = { background: C.accent, color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, fontSize: 13, fontWeight: 700, cursor: 'pointer' };
  const ghostBtnStyle = { background: 'transparent', color: C.dim, border: `1px solid ${C.border}`, padding: '4px 12px', borderRadius: 4, fontSize: 11, fontWeight: 600, cursor: 'pointer' };
  const tableStyle = { width: '100%', borderCollapse: 'collapse', background: C.bg, borderRadius: 4, overflow: 'hidden', border: `1px solid ${C.border}` };
  const thStyle = { textAlign: 'left', padding: '8px 12px', borderBottom: `1px solid ${C.border}`, color: C.dim, fontSize: 11, fontWeight: 600, background: '#16162a' };
  const tdStyle = { padding: '4px 8px', borderBottom: `1px solid ${C.border}`, color: C.text, fontSize: 13 };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: C.bg, overflow: 'hidden' }}>
      {/* Top Bar: LLM Consensus Layer */}
      <div style={{ padding: '16px 24px', background: C.bgAlt, borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, color: C.text, display: 'flex', alignItems: 'center', gap: 8 }}>
            🛡️ Whitelist Knowledge Foundation
            <span style={{ fontSize: 11, background: C.bg, padding: '4px 8px', borderRadius: 4, color: C.accent, fontWeight: 700, border: `1px solid ${C.border}` }}>
              Domain: {domain}
            </span>
          </h2>
          <div style={{ fontSize: 12, color: C.dim, marginTop: 4 }}>
            Deterministic primary sources synthesized through multi-model consensus.
          </div>
        </div>

        <button
          onClick={handleConsensus}
          disabled={consensusRunning}
          style={{
            background: consensusRunning ? C.dim : C.success, color: '#fff', border: 'none',
            padding: '10px 20px', borderRadius: 6, fontWeight: 800, cursor: consensusRunning ? 'wait' : 'pointer',
            display: 'flex', alignItems: 'center', gap: 8, transition: 'all 0.2s', boxShadow: `0 0 15px ${consensusRunning ? 'transparent' : C.success + '44'}`
          }}>
          {consensusRunning ? '⏳ Running Consensus...' : '⚖️ Run LLM Consensus (Opus + Kimi + Qwen)'}
        </button>
      </div>

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left Column: Deterministic Input Layers */}
        <div style={{ flex: '0 0 60%', borderRight: `1px solid ${C.border}`, display: 'flex', flexDirection: 'column', overflowY: 'auto', padding: 24, gap: 24 }}>

          {/* Layer 1: Flash Cache */}
          <div style={layerStyle}>
            <div style={headerStyle}><span style={{ fontSize: 16 }}>⚡</span> Layer 1: Flash Cache</div>
            <div style={{ fontSize: 12, color: C.dim, marginBottom: 12 }}>Quick keyword audit targeting internal system terminology.</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                value={flashQuery}
                onChange={e => setFlashQuery(e.target.value)}
                placeholder="Enter terminology or keywords to flash cache..."
                style={inputStyle}
              />
              <button style={actionBtnStyle}>Audit Cache</button>
            </div>
          </div>

          {/* Layer 2: Web Search */}
          <div style={layerStyle}>
            <div style={headerStyle}><span style={{ fontSize: 16 }}>🌐</span> Layer 2: Web Search Scopes</div>
            <div style={{ fontSize: 12, color: C.dim, marginBottom: 12 }}>Monitored domains and search links. Feed back into cache layer.</div>
            <table style={tableStyle}>
              <thead>
                <tr><th style={thStyle}>URL / Link</th><th style={thStyle} width="100">Scope</th><th style={thStyle} width="60">Active</th></tr>
              </thead>
              <tbody>
                {webLinks.map((k, i) => (
                  <tr key={i}>
                    <td style={tdStyle}><input type="text" value={k.url} onChange={e => { const nw = [...webLinks]; nw[i].url = e.target.value; setWebLinks(nw); }} style={{ ...inputStyle, background: 'transparent', border: 'none' }} placeholder="https://..." /></td>
                    <td style={tdStyle}>
                      <select value={k.scope} onChange={e => { const nw = [...webLinks]; nw[i].scope = e.target.value; setWebLinks(nw); }} style={{ ...inputStyle, background: 'transparent', border: 'none', padding: 0, color: C.text }}>
                        <option value="site">Site</option><option value="page">Page</option>
                      </select>
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      <input type="checkbox" checked={k.active} onChange={e => { const nw = [...webLinks]; nw[i].active = e.target.checked; setWebLinks(nw); }} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
              <button onClick={addWebLink} style={ghostBtnStyle}>+ Add Link</button>
              <button style={{ ...actionBtnStyle, background: C.highlight, border: `1px solid ${C.border}`, padding: '4px 12px', fontSize: 11 }}>Global Search Go</button>
            </div>
          </div>

          {/* Layer 3: API Sources */}
          <div style={layerStyle}>
            <div style={headerStyle}><span style={{ fontSize: 16 }}>🔌</span> Layer 3: API Sources</div>
            <div style={{ fontSize: 12, color: C.dim, marginBottom: 12 }}>Structured deterministic data from GitHub, Stack Overflow, Semantic Scholar, etc.</div>
            <table style={tableStyle}>
              <thead>
                <tr><th style={thStyle}>Source Name</th><th style={thStyle}>Endpoint / Config</th><th style={thStyle} width="60">Global</th></tr>
              </thead>
              <tbody>
                {apiSources.map((k, i) => (
                  <tr key={i}>
                    <td style={tdStyle}><input type="text" value={k.name} onChange={e => { const nw = [...apiSources]; nw[i].name = e.target.value; setApiSources(nw); }} style={{ ...inputStyle, background: 'transparent', border: 'none' }} placeholder="Name" /></td>
                    <td style={tdStyle}><input type="text" value={k.endpoint} onChange={e => { const nw = [...apiSources]; nw[i].endpoint = e.target.value; setApiSources(nw); }} style={{ ...inputStyle, background: 'transparent', border: 'none' }} placeholder="Endpoint URL" /></td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      <input type="checkbox" checked={k.active} onChange={e => { const nw = [...apiSources]; nw[i].active = e.target.checked; setApiSources(nw); }} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
              <button onClick={addApiSource} style={{ ...ghostBtnStyle }}>+ Add API Source</button>
            </div>
          </div>

          {/* Layer 4: Authority Layer */}
          <div style={layerStyle}>
            <div style={headerStyle}><span style={{ fontSize: 16 }}>🎓</span> Layer 4: Authority Tracking</div>
            <div style={{ fontSize: 12, color: C.dim, marginBottom: 12 }}>Monitor influencers, podcasters, and gurus for deep context mapping without downloading videos.</div>
            <table style={tableStyle}>
              <thead>
                <tr><th style={thStyle}>Name</th><th style={thStyle}>Web URL</th><th style={thStyle}>Video URL</th></tr>
              </thead>
              <tbody>
                {authorities.map((k, i) => (
                  <tr key={i}>
                    <td style={tdStyle}><input type="text" value={k.name} onChange={e => { const nw = [...authorities]; nw[i].name = e.target.value; setAuthorities(nw); }} style={{ ...inputStyle, background: 'transparent', border: 'none' }} placeholder="Expert Name" /></td>
                    <td style={tdStyle}><input type="text" value={k.web} onChange={e => { const nw = [...authorities]; nw[i].web = e.target.value; setAuthorities(nw); }} style={{ ...inputStyle, background: 'transparent', border: 'none' }} placeholder="Web Link" /></td>
                    <td style={tdStyle}><input type="text" value={k.video} onChange={e => { const nw = [...authorities]; nw[i].video = e.target.value; setAuthorities(nw); }} style={{ ...inputStyle, background: 'transparent', border: 'none' }} placeholder="Video Link" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button onClick={addAuthority} style={{ ...ghostBtnStyle, marginTop: 8 }}>+ Add Authority</button>
          </div>

          {/* Layer 5: Direct Uploads */}
          <div style={layerStyle}>
            <div style={headerStyle}><span style={{ fontSize: 16 }}>⬆️</span> Layer 5: Direct Uploads</div>
            <div style={{ fontSize: 12, color: C.dim, marginBottom: 12 }}>Hard-anchor PDFs, Docs, or text files directly into the whitelist context of the active domain.</div>
            <div style={{ border: `2px dashed ${C.border}`, borderRadius: 8, padding: 30, textAlign: 'center', background: C.bgAlt, cursor: 'pointer', transition: 'all 0.2s' }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>📥</div>
              <div style={{ fontSize: 14, color: C.text, fontWeight: 600 }}>Drag & Drop Files Here</div>
              <div style={{ fontSize: 12, color: C.dim, marginTop: 4 }}>PDF, JSON, CSV, TXT, DOCX files supported</div>
            </div>
          </div>

        </div>

        {/* Right Column: Synthesized Output / Validation DB */}
        <div style={{ flex: '0 0 40%', padding: 24, background: '#0a0a18', overflowY: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <span style={{ fontSize: 24 }}>🧠</span>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, color: C.text }}>Synthesized LLM Data</div>
              <div style={{ fontSize: 11, color: C.dim }}>Validated knowledge fed into local folders</div>
            </div>
          </div>

          {validatedKnowledge.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 60, color: C.dim, border: `1px solid ${C.border}`, borderRadius: 8, background: C.bgAlt }}>
              <div style={{ fontSize: 32, marginBottom: 16 }}>⚖️</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: C.text, marginBottom: 8 }}>No Validated Knowledge Yet</div>
              <div style={{ fontSize: 12 }}>Run the Consensus Engine to synthesize the inputs from the 5 left layers.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {validatedKnowledge.map(k => (
                <div key={k.id} style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 16, borderLeft: `3px solid ${C.success}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: C.text }}>{k.title}</div>
                    <span style={{ fontSize: 10, background: '#4caf5022', color: C.success, padding: '2px 6px', borderRadius: 4, fontWeight: 800 }}>✓ VALIDATED</span>
                  </div>
                  <div style={{ fontSize: 13, color: '#ccc', lineHeight: 1.5, marginBottom: 12 }}>
                    {k.content}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, color: C.dim, paddingTop: 12, borderTop: `1px solid ${C.border}` }}>
                    <div style={{ display: 'flex', gap: 4 }}>
                      Models: {k.models.map(m => (
                        <span key={m} style={{ background: C.bg, padding: '2px 6px', borderRadius: 4, color: C.text }}>{m}</span>
                      ))}
                    </div>
                    <span>{new Date(k.timestamp).toLocaleTimeString()}</span>
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
