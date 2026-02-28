import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../config/api';
import FlashCachePanel from './FlashCachePanel';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', accentAlt: '#533483',
  text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  success: '#4caf50', warn: '#ff9800', error: '#f44336', info: '#2196f3',
};

const btn = (bg = C.accentAlt) => ({
  padding: '6px 14px', border: 'none', borderRadius: 4, cursor: 'pointer',
  fontSize: 12, fontWeight: 600, color: '#fff', background: bg,
});

const input = {
  padding: '7px 10px', border: `1px solid ${C.border}`, borderRadius: 4,
  background: C.bg, color: C.text, fontSize: 12, outline: 'none', width: '100%', boxSizing: 'border-box',
};

function TypeIcon({ type }) {
  const icons = { website: '🌐', youtube: '📺', podcast: '🎙️', blog: '📝', person: '👤', github: '🐙' };
  return <span style={{ fontSize: 16 }}>{icons[type] || '🔗'}</span>;
}

// ── Source Row ────────────────────────────────────────────────────────
function SourceRow({ source, selected, onSelect, onDelete, onRun, running }) {
  return (
    <div
      onClick={() => onSelect(source)}
      style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
        cursor: 'pointer', borderBottom: `1px solid ${C.border}`,
        background: selected ? C.bgDark : 'transparent',
        borderLeft: selected ? `3px solid ${C.accent}` : '3px solid transparent',
        transition: 'background .1s',
      }}
      onMouseEnter={e => { if (!selected) e.currentTarget.style.background = C.bgAlt; }}
      onMouseLeave={e => { if (!selected) e.currentTarget.style.background = selected ? C.bgDark : 'transparent'; }}
    >
      <TypeIcon type={source.source_type || 'api'} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{source.name}</div>
        <div style={{ fontSize: 10, color: C.dim, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{source.url}</div>
      </div>
      <div style={{ display: 'flex', gap: 4, flexShrink: 0, alignItems: 'center' }}>
        {source.run_count > 0 && <span style={{ fontSize: 9, color: C.dim }}>{source.run_count} runs</span>}
        <button onClick={e => { e.stopPropagation(); onRun(source.id); }} disabled={running === source.id}
          style={{ ...btn(C.success), fontSize: 10, padding: '3px 8px', opacity: running === source.id ? 0.5 : 1 }}>
          {running === source.id ? '⏳' : '▶'}
        </button>
        <button onClick={e => { e.stopPropagation(); onDelete(source.id); }}
          style={{ ...btn(C.border), fontSize: 10, padding: '3px 6px' }}>🗑</button>
      </div>
    </div>
  );
}

// ── API Sources Sub-tab ───────────────────────────────────────────────
function APISourcesPanel() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [desc, setDesc] = useState('');
  const [running, setRunning] = useState(null);
  const [runResult, setRunResult] = useState(null);
  const [runQuery, setRunQuery] = useState('');

  // Doc state
  const [docs, setDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [docContent, setDocContent] = useState('');
  const [docEdit, setDocEdit] = useState('');
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/whitelist-hub/api-sources`);
      if (res.ok) setSources((await res.json()).sources || []);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    if (selected) {
      fetch(`${API_BASE_URL}/api/whitelist-hub/sources/${selected.id}/documents`)
        .then(r => r.ok ? r.json() : { documents: [] })
        .then(d => setDocs(d.documents || []))
        .catch(() => setDocs([]));
    }
  }, [selected]);

  const addSource = async () => {
    if (!name.trim() || !url.trim()) return;
    await fetch(`${API_BASE_URL}/api/whitelist-hub/api-sources`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, url, api_key: apiKey, description: desc }),
    });
    setShowAdd(false); setName(''); setUrl(''); setApiKey(''); setDesc('');
    refresh();
  };

  const deleteSource = async (id) => {
    if (!window.confirm('Delete this API source?')) return;
    await fetch(`${API_BASE_URL}/api/whitelist-hub/api-sources/${id}`, { method: 'DELETE' });
    if (selected?.id === id) setSelected(null);
    refresh();
  };

  const runSource = async (id) => {
    setRunning(id); setRunResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/whitelist-hub/api-sources/${id}/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: id, query: runQuery || null, use_kimi: true }),
      });
      if (res.ok) setRunResult(await res.json());
    } catch { /* silent */ }
    finally { setRunning(null); refresh(); }
  };

  const uploadDoc = async (e) => {
    if (!e.target.files?.length || !selected) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('file', e.target.files[0]);
    await fetch(`${API_BASE_URL}/api/whitelist-hub/sources/${selected.id}/upload`, { method: 'POST', body: fd });
    setUploading(false);
    if (fileRef.current) fileRef.current.value = '';
    fetch(`${API_BASE_URL}/api/whitelist-hub/sources/${selected.id}/documents`).then(r => r.ok ? r.json() : { documents: [] }).then(d => setDocs(d.documents || []));
  };

  const openDoc = async (doc) => {
    setSelectedDoc(doc); setEditing(false);
    const res = await fetch(`${API_BASE_URL}/api/whitelist-hub/sources/${selected.id}/documents/${encodeURIComponent(doc.filename)}/content`);
    if (res.ok) { const d = await res.json(); setDocContent(d.content || ''); setDocEdit(d.content || ''); }
  };

  const saveDoc = async () => {
    setSaving(true);
    await fetch(`${API_BASE_URL}/api/whitelist-hub/sources/${selected.id}/documents/${encodeURIComponent(selectedDoc.filename)}/content`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: docEdit }),
    });
    setDocContent(docEdit); setSaving(false); setEditing(false);
  };

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* Source list */}
      <div style={{ flex: '0 0 320px', borderRight: `1px solid ${C.border}`, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', gap: 6, background: C.bgAlt }}>
          <button onClick={() => setShowAdd(!showAdd)} style={{ ...btn(C.accent), flex: 1, fontSize: 11 }}>+ Add API Source</button>
          <button onClick={refresh} style={{ ...btn(C.bgDark), fontSize: 11 }}>↻</button>
        </div>
        {showAdd && (
          <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <input placeholder="Name (e.g. GitHub)" value={name} onChange={e => setName(e.target.value)} style={input} />
            <input placeholder="API URL (paste endpoint)" value={url} onChange={e => setUrl(e.target.value)} style={input} />
            <input placeholder="API Key (optional)" value={apiKey} onChange={e => setApiKey(e.target.value)} style={input} type="password" />
            <input placeholder="Description" value={desc} onChange={e => setDesc(e.target.value)} style={input} />
            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={addSource} style={{ ...btn(C.success), flex: 1 }}>Add</button>
              <button onClick={() => setShowAdd(false)} style={{ ...btn(C.border), flex: 1 }}>Cancel</button>
            </div>
          </div>
        )}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading ? <div style={{ padding: 20, textAlign: 'center', color: C.dim }}>Loading...</div>
           : sources.length === 0 ? <div style={{ padding: 30, textAlign: 'center', color: C.dim }}><div style={{ fontSize: 32 }}>🔌</div><div style={{ fontSize: 12, marginTop: 8 }}>No API sources yet</div></div>
           : sources.map(s => <SourceRow key={s.id} source={{...s, source_type: 'api'}} selected={selected?.id === s.id} onSelect={setSelected} onDelete={deleteSource} onRun={runSource} running={running} />)}
        </div>
      </div>

      {/* Detail panel */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {selected ? (
          <>
            <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 16 }}>🔌</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 14 }}>{selected.name}</div>
                <div style={{ fontSize: 10, color: C.dim }}>{selected.url}</div>
              </div>
              <input placeholder="Query (optional)" value={runQuery} onChange={e => setRunQuery(e.target.value)} style={{ ...input, width: 160, fontSize: 11 }} />
              <button onClick={() => runSource(selected.id)} disabled={running === selected.id} style={{ ...btn(C.success), fontSize: 11 }}>▶ Run</button>
            </div>

            <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
              {/* Run result */}
              {runResult && (
                <div style={{ marginBottom: 16, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 6, padding: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: C.success, marginBottom: 8 }}>Run Result</div>
                  {runResult.kimi_analysis && (
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ fontSize: 10, fontWeight: 600, color: C.accent, marginBottom: 4 }}>🧠 Kimi Analysis</div>
                      <pre style={{ margin: 0, fontSize: 11, color: C.text, whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{runResult.kimi_analysis}</pre>
                    </div>
                  )}
                  <details>
                    <summary style={{ fontSize: 10, color: C.muted, cursor: 'pointer' }}>Raw data</summary>
                    <pre style={{ margin: '8px 0 0', fontSize: 10, color: C.muted, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto' }}>
                      {typeof runResult.data === 'string' ? runResult.data : JSON.stringify(runResult.data, null, 2)}
                    </pre>
                  </details>
                </div>
              )}

              {/* Source documents */}
              <div style={{ fontSize: 12, fontWeight: 700, color: C.muted, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                📎 Documents ({docs.length})
                <input type="file" ref={fileRef} onChange={uploadDoc} style={{ display: 'none' }} />
                <button onClick={() => fileRef.current?.click()} disabled={uploading} style={{ ...btn(C.accentAlt), fontSize: 10, padding: '2px 8px', marginLeft: 'auto' }}>
                  {uploading ? '⏳' : '📤 Upload'}
                </button>
              </div>
              {docs.map(d => (
                <div key={d.filename} onClick={() => openDoc(d)} style={{
                  padding: '6px 10px', marginBottom: 3, borderRadius: 4, cursor: 'pointer', fontSize: 12,
                  background: selectedDoc?.filename === d.filename ? C.bgDark : C.bgAlt,
                  border: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 8,
                }}>
                  <span>📄</span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.filename}</span>
                  <span style={{ fontSize: 10, color: C.dim }}>{d.size ? (d.size / 1024).toFixed(1) + ' KB' : ''}</span>
                </div>
              ))}

              {/* Doc viewer/editor */}
              {selectedDoc && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{selectedDoc.filename}</span>
                    {editing ? (
                      <>
                        <button onClick={saveDoc} disabled={saving} style={{ ...btn(C.success), fontSize: 10, marginLeft: 'auto' }}>💾 Save</button>
                        <button onClick={() => { setEditing(false); setDocEdit(docContent); }} style={{ ...btn(C.border), fontSize: 10 }}>Cancel</button>
                      </>
                    ) : (
                      <button onClick={() => { setEditing(true); setDocEdit(docContent); }} style={{ ...btn(C.accentAlt), fontSize: 10, marginLeft: 'auto' }}>✏️ Edit</button>
                    )}
                  </div>
                  {editing ? (
                    <textarea value={docEdit} onChange={e => setDocEdit(e.target.value)}
                      onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); saveDoc(); } }}
                      style={{ width: '100%', height: 200, resize: 'vertical', background: '#0d1117', color: '#e6edf3', border: 'none', padding: 12, fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6, borderRadius: 4, outline: 'none', boxSizing: 'border-box' }} />
                  ) : (
                    <pre style={{ margin: 0, padding: 12, background: '#0d1117', color: '#e6edf3', borderRadius: 4, fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap', maxHeight: 300, overflow: 'auto' }}>{docContent || '(empty)'}</pre>
                  )}
                </div>
              )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.dim }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 48, opacity: 0.5 }}>🔌</div>
              <div style={{ fontSize: 14, fontWeight: 500, color: C.muted, marginTop: 8 }}>Select an API source</div>
              <div style={{ fontSize: 12, marginTop: 4 }}>Paste an API endpoint and Grace auto-connects</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Web Sources Sub-tab ───────────────────────────────────────────────
function WebSourcesPanel() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [sourceType, setSourceType] = useState('website');
  const [desc, setDesc] = useState('');
  const [running, setRunning] = useState(null);
  const [runResult, setRunResult] = useState(null);
  const [runQuery, setRunQuery] = useState('');

  const [docs, setDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [docContent, setDocContent] = useState('');
  const [docEdit, setDocEdit] = useState('');
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/whitelist-hub/web-sources`);
      if (res.ok) setSources((await res.json()).sources || []);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    if (selected) {
      fetch(`${API_BASE_URL}/api/whitelist-hub/sources/${selected.id}/documents`)
        .then(r => r.ok ? r.json() : { documents: [] })
        .then(d => setDocs(d.documents || [])).catch(() => setDocs([]));
    }
  }, [selected]);

  const addSource = async () => {
    if (!name.trim() || !url.trim()) return;
    await fetch(`${API_BASE_URL}/api/whitelist-hub/web-sources`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, url, source_type: sourceType, description: desc }),
    });
    setShowAdd(false); setName(''); setUrl(''); setDesc('');
    refresh();
  };

  const deleteSource = async (id) => {
    if (!window.confirm('Delete this web source?')) return;
    await fetch(`${API_BASE_URL}/api/whitelist-hub/web-sources/${id}`, { method: 'DELETE' });
    if (selected?.id === id) setSelected(null);
    refresh();
  };

  const runSource = async (id) => {
    setRunning(id); setRunResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/whitelist-hub/web-sources/${id}/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: id, query: runQuery || null, use_kimi: true }),
      });
      if (res.ok) setRunResult(await res.json());
    } catch { /* silent */ }
    finally { setRunning(null); refresh(); }
  };

  const uploadDoc = async (e) => {
    if (!e.target.files?.length || !selected) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('file', e.target.files[0]);
    await fetch(`${API_BASE_URL}/api/whitelist-hub/sources/${selected.id}/upload`, { method: 'POST', body: fd });
    setUploading(false);
    if (fileRef.current) fileRef.current.value = '';
    fetch(`${API_BASE_URL}/api/whitelist-hub/sources/${selected.id}/documents`).then(r => r.ok ? r.json() : { documents: [] }).then(d => setDocs(d.documents || []));
  };

  const openDoc = async (doc) => {
    setSelectedDoc(doc); setEditing(false);
    const res = await fetch(`${API_BASE_URL}/api/whitelist-hub/sources/${selected.id}/documents/${encodeURIComponent(doc.filename)}/content`);
    if (res.ok) { const d = await res.json(); setDocContent(d.content || ''); setDocEdit(d.content || ''); }
  };

  const saveDoc = async () => {
    setSaving(true);
    await fetch(`${API_BASE_URL}/api/whitelist-hub/sources/${selected.id}/documents/${encodeURIComponent(selectedDoc.filename)}/content`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: docEdit }),
    });
    setDocContent(docEdit); setSaving(false); setEditing(false);
  };

  const typeOptions = [
    { id: 'website', label: '🌐 Website' }, { id: 'youtube', label: '📺 YouTube' },
    { id: 'podcast', label: '🎙️ Podcast' }, { id: 'blog', label: '📝 Blog' },
    { id: 'person', label: '👤 Person' }, { id: 'github', label: '🐙 GitHub' },
  ];

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      <div style={{ flex: '0 0 320px', borderRight: `1px solid ${C.border}`, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', gap: 6, background: C.bgAlt }}>
          <button onClick={() => setShowAdd(!showAdd)} style={{ ...btn(C.accent), flex: 1, fontSize: 11 }}>+ Add Web Source</button>
          <button onClick={refresh} style={{ ...btn(C.bgDark), fontSize: 11 }}>↻</button>
        </div>
        {showAdd && (
          <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <input placeholder="Name" value={name} onChange={e => setName(e.target.value)} style={input} />
            <input placeholder="URL" value={url} onChange={e => setUrl(e.target.value)} style={input} />
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {typeOptions.map(t => (
                <button key={t.id} onClick={() => setSourceType(t.id)}
                  style={{ ...btn(sourceType === t.id ? C.accentAlt : C.bgDark), fontSize: 10, padding: '3px 8px' }}>{t.label}</button>
              ))}
            </div>
            <input placeholder="Description" value={desc} onChange={e => setDesc(e.target.value)} style={input} />
            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={addSource} style={{ ...btn(C.success), flex: 1 }}>Add</button>
              <button onClick={() => setShowAdd(false)} style={{ ...btn(C.border), flex: 1 }}>Cancel</button>
            </div>
          </div>
        )}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading ? <div style={{ padding: 20, textAlign: 'center', color: C.dim }}>Loading...</div>
           : sources.length === 0 ? <div style={{ padding: 30, textAlign: 'center', color: C.dim }}><div style={{ fontSize: 32 }}>🌐</div><div style={{ fontSize: 12, marginTop: 8 }}>No web sources yet</div></div>
           : sources.map(s => <SourceRow key={s.id} source={s} selected={selected?.id === s.id} onSelect={setSelected} onDelete={deleteSource} onRun={runSource} running={running} />)}
        </div>
      </div>

      {/* Detail — identical pattern to API sources */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {selected ? (
          <>
            <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', alignItems: 'center', gap: 8 }}>
              <TypeIcon type={selected.source_type} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 14 }}>{selected.name}</div>
                <div style={{ fontSize: 10, color: C.dim }}>{selected.url} · {selected.source_type}</div>
              </div>
              <input placeholder="Extra context..." value={runQuery} onChange={e => setRunQuery(e.target.value)} style={{ ...input, width: 160, fontSize: 11 }} />
              <button onClick={() => runSource(selected.id)} disabled={running === selected.id} style={{ ...btn(C.success), fontSize: 11 }}>▶ Run</button>
            </div>

            <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
              {runResult && (
                <div style={{ marginBottom: 16, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 6, padding: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: C.success, marginBottom: 8 }}>
                    {runResult.title && <span>{runResult.title}</span>}
                  </div>
                  {runResult.kimi_analysis && (
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ fontSize: 10, fontWeight: 600, color: C.accent, marginBottom: 4 }}>🧠 Kimi Analysis</div>
                      <pre style={{ margin: 0, fontSize: 11, color: C.text, whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{runResult.kimi_analysis}</pre>
                    </div>
                  )}
                  <details>
                    <summary style={{ fontSize: 10, color: C.muted, cursor: 'pointer' }}>Extracted text</summary>
                    <pre style={{ margin: '8px 0 0', fontSize: 10, color: C.muted, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto' }}>{runResult.text}</pre>
                  </details>
                </div>
              )}

              <div style={{ fontSize: 12, fontWeight: 700, color: C.muted, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                📎 Documents ({docs.length})
                <input type="file" ref={fileRef} onChange={uploadDoc} style={{ display: 'none' }} />
                <button onClick={() => fileRef.current?.click()} disabled={uploading} style={{ ...btn(C.accentAlt), fontSize: 10, padding: '2px 8px', marginLeft: 'auto' }}>
                  {uploading ? '⏳' : '📤 Upload'}
                </button>
              </div>
              {docs.map(d => (
                <div key={d.filename} onClick={() => openDoc(d)} style={{
                  padding: '6px 10px', marginBottom: 3, borderRadius: 4, cursor: 'pointer', fontSize: 12,
                  background: selectedDoc?.filename === d.filename ? C.bgDark : C.bgAlt,
                  border: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 8,
                }}>
                  <span>📄</span>
                  <span style={{ flex: 1 }}>{d.filename}</span>
                  <span style={{ fontSize: 10, color: C.dim }}>{d.size ? (d.size / 1024).toFixed(1) + ' KB' : ''}</span>
                </div>
              ))}

              {selectedDoc && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{selectedDoc.filename}</span>
                    {editing ? (
                      <>
                        <button onClick={saveDoc} disabled={saving} style={{ ...btn(C.success), fontSize: 10, marginLeft: 'auto' }}>💾 Save</button>
                        <button onClick={() => { setEditing(false); setDocEdit(docContent); }} style={{ ...btn(C.border), fontSize: 10 }}>Cancel</button>
                      </>
                    ) : (
                      <button onClick={() => { setEditing(true); setDocEdit(docContent); }} style={{ ...btn(C.accentAlt), fontSize: 10, marginLeft: 'auto' }}>✏️ Edit</button>
                    )}
                  </div>
                  {editing ? (
                    <textarea value={docEdit} onChange={e => setDocEdit(e.target.value)}
                      onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); saveDoc(); } }}
                      style={{ width: '100%', height: 200, resize: 'vertical', background: '#0d1117', color: '#e6edf3', border: 'none', padding: 12, fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6, borderRadius: 4, outline: 'none', boxSizing: 'border-box' }} />
                  ) : (
                    <pre style={{ margin: 0, padding: 12, background: '#0d1117', color: '#e6edf3', borderRadius: 4, fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap', maxHeight: 300, overflow: 'auto' }}>{docContent || '(empty)'}</pre>
                  )}
                </div>
              )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.dim }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 48, opacity: 0.5 }}>🌐</div>
              <div style={{ fontSize: 14, fontWeight: 500, color: C.muted, marginTop: 8 }}>Select a web source</div>
              <div style={{ fontSize: 12, marginTop: 4 }}>Add websites, YouTube, podcasts, blogs, people</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main WhitelistTab ─────────────────────────────────────────────────
export default function WhitelistTab() {
  const [activeTab, setActiveTab] = useState('api');
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/whitelist-hub/stats`)
      .then(r => r.ok ? r.json() : null).then(setStats).catch(() => {});
  }, []);

  const tabs = [
    { id: 'api', label: 'API Sources', icon: '🔌' },
    { id: 'web', label: 'Web Sources', icon: '🌐' },
    { id: 'cache', label: 'Flash Cache', icon: '⚡' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: C.text, background: C.bg }}>
      <div style={{ borderBottom: `1px solid ${C.border}`, background: C.bgAlt, padding: '0 16px', display: 'flex', alignItems: 'stretch' }}>
        <span style={{ fontSize: 15, fontWeight: 700, padding: '12px 16px 12px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
          🛡️ Whitelist
        </span>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            padding: '10px 16px', border: 'none', background: 'none', cursor: 'pointer',
            color: activeTab === t.id ? C.accent : C.muted,
            borderBottom: activeTab === t.id ? `2px solid ${C.accent}` : '2px solid transparent',
            fontSize: 13, fontWeight: activeTab === t.id ? 700 : 500,
            display: 'flex', alignItems: 'center', gap: 6, transition: 'all .15s',
          }}><span>{t.icon}</span> {t.label}</button>
        ))}
        {stats && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16, fontSize: 11, color: C.dim, paddingRight: 8 }}>
            <span>🔌 {stats.api_source_count} APIs</span>
            <span>🌐 {stats.web_source_count} web</span>
            <span>📎 {stats.total_documents} docs</span>
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'api' && <APISourcesPanel />}
        {activeTab === 'web' && <WebSourcesPanel />}
        {activeTab === 'cache' && <FlashCachePanel />}
      </div>
    </div>
  );
}
