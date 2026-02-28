import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#0d1117', bgAlt: '#161b22', bgPanel: '#1a1a2e',
  accent: '#e94560', accentAlt: '#533483', blue: '#58a6ff',
  text: '#e6edf3', muted: '#8b949e', dim: '#484f58', border: '#30363d',
  success: '#3fb950', warn: '#d29922', error: '#f85149',
};
const btn = (bg = C.accentAlt) => ({
  padding: '5px 12px', border: 'none', borderRadius: 4, cursor: 'pointer',
  fontSize: 12, fontWeight: 600, color: '#fff', background: bg,
});
const inp = {
  padding: '6px 10px', border: `1px solid ${C.border}`, borderRadius: 4,
  background: C.bg, color: C.text, fontSize: 12, outline: 'none', width: '100%', boxSizing: 'border-box',
};

function langIcon(name) {
  const ext = (name || '').split('.').pop().toLowerCase();
  const m = { py: '🐍', js: '🟨', ts: '🔷', jsx: '⚛️', tsx: '⚛️', html: '🌐', css: '🎨', json: '📋', md: '📝', sh: '🖥️', sql: '🗄️', yaml: '⚙️', yml: '⚙️' };
  return m[ext] || '📄';
}

// ── Tree Node ─────────────────────────────────────────────────────────
function TreeNode({ node, depth, selectedPath, onSelect, expanded, toggleExpand }) {
  if (!node) return null;
  const isDir = node.type === 'directory';
  const isOpen = expanded.has(node.path);
  const isSel = selectedPath === node.path;
  const hasKids = isDir && node.children?.length > 0;

  return (
    <>
      <div
        onClick={() => { onSelect(node); if (isDir) toggleExpand(node.path); }}
        style={{
          display: 'flex', alignItems: 'center', padding: '3px 8px', paddingLeft: 8 + depth * 14,
          cursor: 'pointer', fontSize: 12, color: isSel ? C.text : C.muted,
          background: isSel ? C.bgAlt : 'transparent', userSelect: 'none',
          borderLeft: isSel ? `2px solid ${C.accent}` : '2px solid transparent',
        }}
        onMouseEnter={e => { if (!isSel) e.currentTarget.style.background = '#1c2128'; }}
        onMouseLeave={e => { if (!isSel) e.currentTarget.style.background = 'transparent'; }}
      >
        {isDir && <span style={{ fontSize: 9, width: 12, textAlign: 'center', marginRight: 4, color: C.dim }}>{hasKids ? (isOpen ? '▼' : '▶') : ' '}</span>}
        {!isDir && <span style={{ width: 16 }} />}
        <span style={{ marginRight: 5 }}>{isDir ? '📁' : langIcon(node.name)}</span>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{node.name}</span>
      </div>
      {isDir && isOpen && node.children?.map(c => (
        <TreeNode key={c.path} node={c} depth={depth + 1} selectedPath={selectedPath} onSelect={onSelect} expanded={expanded} toggleExpand={toggleExpand} />
      ))}
    </>
  );
}

// ── Main Component ────────────────────────────────────────────────────
export default function CodebaseTab() {
  // Projects
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [showNewProject, setShowNewProject] = useState(false);
  const [npName, setNpName] = useState('');
  const [npDomain, setNpDomain] = useState('');
  const [npType, setNpType] = useState('general');
  const [npDesc, setNpDesc] = useState('');

  // File tree
  const [tree, setTree] = useState(null);
  const [expanded, setExpanded] = useState(new Set());
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [fileLang, setFileLang] = useState('text');
  const [fileLoading, setFileLoading] = useState(false);

  // Editor
  const [editContent, setEditContent] = useState('');
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hasUnsaved, setHasUnsaved] = useState(false);

  // New file
  const [showNewFile, setShowNewFile] = useState(false);
  const [newFilePath, setNewFilePath] = useState('');

  // Coding agent
  const [agentPrompt, setAgentPrompt] = useState('');
  const [agentResponse, setAgentResponse] = useState('');
  const [agentLoading, setAgentLoading] = useState(false);
  const [useKimi, setUseKimi] = useState(false);
  const [agentCaps, setAgentCaps] = useState(null);
  const [agentRules, setAgentRules] = useState([]);
  const agentEndRef = useRef(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/coding-agent/capabilities`)
      .then(r => r.ok ? r.json() : null).then(setAgentCaps).catch(() => {});
    fetch(`${API_BASE_URL}/api/v1/agent/rules`)
      .then(r => r.ok ? r.json() : { rules: [] }).then(d => setAgentRules(d.rules || [])).catch(() => {});
  }, []);

  // Panel sizing
  const [fullscreenPanel, setFullscreenPanel] = useState(null); // null, 'tree', 'editor', 'agent'
  const [fullData, setFullData] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/tabs/codebase/full`).then(r => r.ok ? r.json() : null).then(setFullData).catch(() => {});
  }, []);

  // ── Fetch ───────────────────────────────────────────────────────────
  const fetchProjects = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/codebase-hub/projects`);
      if (res.ok) setProjects((await res.json()).projects || []);
    } catch { /* silent */ }
  }, []);

  const fetchTree = useCallback(async (folder) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/codebase-hub/tree/${encodeURIComponent(folder)}`);
      if (res.ok) setTree(await res.json());
    } catch { /* silent */ }
  }, []);

  const openFile = useCallback(async (path) => {
    setFileLoading(true); setEditing(false); setHasUnsaved(false);
    try {
      const res = await fetch(`${API_BASE_URL}/api/codebase-hub/file?path=${encodeURIComponent(path)}`);
      if (res.ok) {
        const d = await res.json();
        setFileContent(d.content || ''); setEditContent(d.content || '');
        setFileLang(d.language || 'text'); setSelectedFile({ path, name: d.name, language: d.language });
      }
    } catch { /* silent */ }
    finally { setFileLoading(false); }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  useEffect(() => {
    if (selectedProject) fetchTree(selectedProject.project_folder);
  }, [selectedProject, fetchTree]);

  // ── Handlers ────────────────────────────────────────────────────────
  const toggleExpand = useCallback((path) => {
    setExpanded(prev => { const n = new Set(prev); if (n.has(path)) n.delete(path); else n.add(path); return n; });
  }, []);

  const handleTreeSelect = useCallback((node) => {
    if (node.type === 'file') openFile(node.path);
  }, [openFile]);

  const handleSave = async () => {
    if (!selectedFile) return;
    setSaving(true);
    try {
      await fetch(`${API_BASE_URL}/api/codebase-hub/file`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile.path, content: editContent }),
      });
      setFileContent(editContent); setHasUnsaved(false);
    } catch { /* silent */ }
    finally { setSaving(false); }
  };

  const handleCreateProject = async () => {
    if (!npName.trim() || !npDomain.trim()) return;
    await fetch(`${API_BASE_URL}/api/codebase-hub/projects`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: npName, domain_folder: npDomain, project_type: npType, description: npDesc }),
    });
    setShowNewProject(false); setNpName(''); setNpDomain(''); setNpDesc('');
    fetchProjects();
  };

  const handleCreateFile = async () => {
    if (!newFilePath.trim() || !selectedProject) return;
    const fullPath = `${selectedProject.project_folder}/${newFilePath}`;
    await fetch(`${API_BASE_URL}/api/codebase-hub/file/create`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: fullPath, content: '' }),
    });
    setShowNewFile(false); setNewFilePath('');
    fetchTree(selectedProject.project_folder);
    openFile(fullPath);
    setEditing(true);
  };

  const handleDeleteFile = async () => {
    if (!selectedFile || !window.confirm(`Delete ${selectedFile.name}?`)) return;
    await fetch(`${API_BASE_URL}/api/codebase-hub/file?path=${encodeURIComponent(selectedFile.path)}`, { method: 'DELETE' });
    setSelectedFile(null); setFileContent('');
    if (selectedProject) fetchTree(selectedProject.project_folder);
  };

  // ── Coding Agent ────────────────────────────────────────────────────
  const handleAgentSend = async () => {
    if (!agentPrompt.trim() || !selectedProject || agentLoading) return;
    setAgentLoading(true);
    const prompt = agentPrompt; setAgentPrompt('');
    setAgentResponse(prev => prev + `\n\n>>> ${prompt}\n\nThinking...`);
    try {
      const res = await fetch(`${API_BASE_URL}/api/coding-agent/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt, project_folder: selectedProject.project_folder,
          current_file: selectedFile?.path || null,
          use_kimi: useKimi,
          include_codenet: true,
          include_memory: true,
          include_rag: true,
        }),
      });
      if (res.ok) {
        const d = await res.json();
        let footer = '';
        if (d.intelligence_score) footer += `\n\n─── Intelligence: ${d.intelligence_score.score}/10 (${d.intelligence_score.available}/${d.intelligence_score.total_systems} systems)`;
        if (d.verification?.verified != null) footer += ` · Verified: ${d.verification.verified ? '✅' : '⚠️'} (${((d.verification.confidence || 0) * 100).toFixed(0)}% confidence)`;
        if (d.verification?.invariants) footer += ` · Invariants: ${d.verification.invariants.violations === 0 ? '✅' : '⚠️ ' + d.verification.invariants.violations + ' violations'}`;
        if (d.trust?.system_trust) footer += ` · Trust: ${((d.trust.system_trust || 0) * 100).toFixed(0)}%`;
        if (d.genesis_key) footer += ` · GK: ${d.genesis_key}`;
        setAgentResponse(prev => prev.replace('Thinking...', (d.response || '(no response)') + footer));
      }
    } catch { setAgentResponse(prev => prev.replace('Thinking...', '(error)')); }
    finally { setAgentLoading(false); setTimeout(() => agentEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100); }
  };

  // ── Panel visibility ────────────────────────────────────────────────
  const showTree = fullscreenPanel === null || fullscreenPanel === 'tree';
  const showEditor = fullscreenPanel === null || fullscreenPanel === 'editor';
  const showAgent = fullscreenPanel === null || fullscreenPanel === 'agent';

  const fsBtn = (panel) => (
    <span onClick={() => setFullscreenPanel(fullscreenPanel === panel ? null : panel)}
      style={{ cursor: 'pointer', fontSize: 14, color: C.dim, padding: '2px 4px' }}
      title={fullscreenPanel === panel ? 'Exit fullscreen' : 'Fullscreen'}>
      {fullscreenPanel === panel ? '⊡' : '⊞'}
    </span>
  );

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: C.text, background: C.bg }}>

      {/* Header: project selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, flexShrink: 0 }}>
        <span style={{ fontSize: 14, fontWeight: 700 }}>💻 Codebase</span>
        <select
          value={selectedProject?.id || ''}
          onChange={e => { const p = projects.find(p => p.id === e.target.value); setSelectedProject(p || null); setSelectedFile(null); setFileContent(''); setTree(null); }}
          style={{ ...inp, width: 'auto', minWidth: 180, fontSize: 12 }}
        >
          <option value="">Select a project...</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name} ({p.domain_folder})</option>)}
        </select>
        <button onClick={() => setShowNewProject(!showNewProject)} style={{ ...btn(C.accent), fontSize: 11 }}>+ New Project</button>

        {selectedProject && (
          <>
            <span style={{ fontSize: 10, color: C.dim }}>📁 {selectedProject.project_folder}</span>
            <span style={{ fontSize: 10, color: C.dim, padding: '2px 6px', background: C.accentAlt + '44', borderRadius: 3 }}>{selectedProject.project_type}</span>
          </>
        )}

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: useKimi ? C.accent : C.dim, cursor: 'pointer' }}>
            <input type="checkbox" checked={useKimi} onChange={e => setUseKimi(e.target.checked)} style={{ display: 'none' }} />
            <span style={{ width: 28, height: 14, borderRadius: 7, background: useKimi ? C.accent : C.dim, position: 'relative', display: 'inline-block' }}>
              <span style={{ position: 'absolute', top: 2, left: useKimi ? 16 : 2, width: 10, height: 10, borderRadius: '50%', background: '#fff', transition: 'left .2s' }} />
            </span>
            Kimi
          </label>
        </div>
      </div>

      {/* New project form */}
      {showNewProject && (
        <div style={{ padding: '8px 12px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input placeholder="Project name" value={npName} onChange={e => setNpName(e.target.value)} style={{ ...inp, width: 140 }} />
          <input placeholder="Domain folder (e.g. green_gardens)" value={npDomain} onChange={e => setNpDomain(e.target.value)} style={{ ...inp, width: 180 }} />
          <select value={npType} onChange={e => setNpType(e.target.value)} style={{ ...inp, width: 110 }}>
            {['general', 'web', 'mobile', 'api', 'landing_page'].map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input placeholder="Description" value={npDesc} onChange={e => setNpDesc(e.target.value)} style={{ ...inp, width: 200 }} />
          <button onClick={handleCreateProject} style={{ ...btn(C.success), fontSize: 11 }}>Create</button>
          <button onClick={() => setShowNewProject(false)} style={{ ...btn(C.border), fontSize: 11 }}>✕</button>
        </div>
      )}

      {/* Three panels + full aggregation */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Panel 1: File Tree */}
        {showTree && (
          <div style={{ flex: fullscreenPanel === 'tree' ? 1 : '0 0 240px', borderRight: `1px solid ${C.border}`, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: C.bg }}>
            <div style={{ padding: '6px 10px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 6, background: C.bgAlt }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: C.muted, flex: 1 }}>EXPLORER</span>
              {selectedProject && <span onClick={() => setShowNewFile(!showNewFile)} style={{ cursor: 'pointer', fontSize: 16, color: C.accent }}>+</span>}
              {fsBtn('tree')}
            </div>
            {showNewFile && selectedProject && (
              <div style={{ padding: '6px 8px', borderBottom: `1px solid ${C.border}`, display: 'flex', gap: 4 }}>
                <input placeholder="path/file.ext" value={newFilePath} onChange={e => setNewFilePath(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleCreateFile()} style={{ ...inp, fontSize: 11, padding: '4px 6px' }} autoFocus />
                <button onClick={handleCreateFile} style={{ ...btn(C.success), fontSize: 10, padding: '3px 8px' }}>✓</button>
              </div>
            )}
            <div style={{ flex: 1, overflowY: 'auto', paddingTop: 4 }}>
              {!selectedProject ? (
                <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 11 }}>Select or create a project</div>
              ) : !tree ? (
                <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 11 }}>Loading...</div>
              ) : tree.children?.length === 0 ? (
                <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 11 }}>Empty project — create files</div>
              ) : (
                tree.children?.map(n => (
                  <TreeNode key={n.path} node={n} depth={0} selectedPath={selectedFile?.path} onSelect={handleTreeSelect} expanded={expanded} toggleExpand={toggleExpand} />
                ))
              )}
            </div>
          </div>
        )}

        {/* Panel 2: Editor */}
        {showEditor && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', borderRight: showAgent ? `1px solid ${C.border}` : 'none' }}>
            {selectedFile ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 12px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, flexShrink: 0 }}>
                  <span>{langIcon(selectedFile.name)}</span>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>{selectedFile.name}</span>
                  {hasUnsaved && <span style={{ fontSize: 9, color: C.accent, fontWeight: 700 }}>●</span>}
                  <span style={{ fontSize: 10, color: C.dim }}>{fileLang}</span>
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: 4, alignItems: 'center' }}>
                    {editing ? (
                      <>
                        <button onClick={handleSave} disabled={saving || !hasUnsaved} style={{ ...btn(hasUnsaved ? C.success : C.border), fontSize: 10 }}>{saving ? '⏳' : '💾 Save'}</button>
                        <button onClick={() => { if (hasUnsaved && !window.confirm('Discard?')) return; setEditing(false); setEditContent(fileContent); setHasUnsaved(false); }} style={{ ...btn(C.border), fontSize: 10 }}>View</button>
                      </>
                    ) : (
                      <button onClick={() => { setEditing(true); setEditContent(fileContent); }} style={{ ...btn(C.accentAlt), fontSize: 10 }}>✏️ Edit</button>
                    )}
                    <button onClick={handleDeleteFile} style={{ ...btn(C.border), fontSize: 10 }}>🗑</button>
                    {fsBtn('editor')}
                  </div>
                </div>
                <div style={{ flex: 1, overflow: 'auto' }}>
                  {fileLoading ? <div style={{ padding: 30, textAlign: 'center', color: C.dim }}>Loading...</div>
                   : editing ? (
                    <textarea value={editContent}
                      onChange={e => { setEditContent(e.target.value); setHasUnsaved(e.target.value !== fileContent); }}
                      onKeyDown={e => {
                        if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); handleSave(); }
                        if (e.key === 'Tab') { e.preventDefault(); const s = e.target.selectionStart; setEditContent(editContent.substring(0, s) + '  ' + editContent.substring(e.target.selectionEnd)); setHasUnsaved(true); requestAnimationFrame(() => { e.target.selectionStart = e.target.selectionEnd = s + 2; }); }
                      }}
                      spellCheck={false}
                      style={{ width: '100%', height: '100%', resize: 'none', background: C.bg, color: C.text, border: 'none', outline: 'none', padding: '12px 16px', fontFamily: '"Fira Code","JetBrains Mono",Consolas,monospace', fontSize: 13, lineHeight: 1.6, tabSize: 2, boxSizing: 'border-box' }} />
                  ) : (
                    <pre style={{ margin: 0, padding: '12px 16px', fontFamily: '"Fira Code","JetBrains Mono",Consolas,monospace', fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: C.text, background: C.bg, height: '100%', overflow: 'auto' }}>
                      {fileContent || '(empty file)'}
                    </pre>
                  )}
                </div>
              </>
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.dim }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 48, opacity: 0.4 }}>📝</div>
                  <div style={{ fontSize: 13, color: C.muted, marginTop: 8 }}>Select a file to edit</div>
                  {fsBtn('editor')}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Panel 3: Coding Agent */}
        {showAgent && (
          <div style={{ flex: fullscreenPanel === 'agent' ? 1 : '0 0 380px', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: C.bgPanel }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, flexShrink: 0 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: C.muted, flex: 1 }}>🤖 UNIFIED AGENT</span>
              <button onClick={() => setAgentResponse('')} style={{ ...btn(C.border), fontSize: 10, padding: '2px 8px' }}>Clear</button>
              {fsBtn('agent')}
            </div>

            {/* Intelligence sources */}
            {agentCaps?.capabilities && (
              <div style={{ padding: '4px 12px', borderBottom: `1px solid ${C.border}`, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {Object.entries(agentCaps.capabilities).map(([key, cap]) => (
                  <span key={key} style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 8,
                    background: cap.available ? '#3fb95022' : '#f8514922',
                    color: cap.available ? '#3fb950' : '#f85149',
                    fontWeight: 600,
                  }} title={cap.description}>
                    {cap.available ? '●' : '○'} {key.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            )}

            {/* Agent rules: upload docs + instructions */}
            <div style={{ padding: '6px 12px', borderBottom: `1px solid ${C.border}`, background: C.bg }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <span style={{ fontSize: 10, color: C.muted }}>📜 Rules:</span>
                <input type="file" id="agentRuleUpload" style={{ display: 'none' }}
                  onChange={async (e) => {
                    if (!e.target.files?.length) return;
                    const fd = new FormData();
                    fd.append('file', e.target.files[0]);
                    fd.append('category', 'coding_standards');
                    await fetch(`${API_BASE_URL}/api/v1/agent/rules/upload`, { method: 'POST', body: fd });
                    e.target.value = '';
                    fetch(`${API_BASE_URL}/api/v1/agent/rules`).then(r => r.ok ? r.json() : { rules: [] }).then(d => setAgentRules(d.rules || []));
                  }}
                />
                <button onClick={() => document.getElementById('agentRuleUpload')?.click()}
                  style={{ ...btn(C.bgDark), fontSize: 9, padding: '2px 8px' }}>📤 Upload</button>
                {agentRules.length > 0 && <span style={{ fontSize: 9, color: C.success }}>{agentRules.length} global</span>}
                {selectedProject && (
                  <>
                    <span style={{ fontSize: 9, color: C.dim }}>|</span>
                    <input type="file" id="domainRuleUpload" style={{ display: 'none' }}
                      onChange={async (e) => {
                        if (!e.target.files?.length || !selectedProject) return;
                        const fd = new FormData();
                        fd.append('file', e.target.files[0]);
                        await fetch(`${API_BASE_URL}/api/v1/domain/${encodeURIComponent(selectedProject.domain_folder || selectedProject.project_folder)}/rules/upload`, { method: 'POST', body: fd });
                        e.target.value = '';
                      }}
                    />
                    <button onClick={() => document.getElementById('domainRuleUpload')?.click()}
                      style={{ ...btn(C.bgDark), fontSize: 9, padding: '2px 8px' }}>📁 Domain Rule</button>
                  </>
                )}
              </div>
            </div>

            <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
              {agentResponse ? (
                <pre style={{ margin: 0, fontFamily: '"Fira Code",Consolas,monospace', fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: C.text }}>
                  {agentResponse}
                </pre>
              ) : (
                <div style={{ textAlign: 'center', color: C.dim, paddingTop: 40 }}>
                  <div style={{ fontSize: 40, opacity: 0.4 }}>🤖</div>
                  <div style={{ fontSize: 12, marginTop: 8, maxWidth: 260, margin: '8px auto 0' }}>
                    Ask the coding agent to write code, create files, refactor, or build features for your project
                  </div>
                </div>
              )}
              <div ref={agentEndRef} />
            </div>

            <div style={{ padding: '8px 12px', borderTop: `1px solid ${C.border}`, background: C.bgAlt }}>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  placeholder={selectedProject ? `Build something for ${selectedProject.name}...` : 'Select a project first...'}
                  value={agentPrompt}
                  onChange={e => setAgentPrompt(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleAgentSend()}
                  disabled={!selectedProject || agentLoading}
                  style={{ ...inp, flex: 1 }}
                />
                <input type="file" id="agentDocUpload" accept=".pdf,.txt,.md,.doc,.docx,.csv,.json,.py,.js,.ts,.jsx,.tsx" style={{ display: 'none' }}
                  onChange={async (e) => {
                    if (!e.target.files?.length) return;
                    const f = e.target.files[0];
                    const text = await f.text().catch(() => `[File: ${f.name}]`);
                    setAgentPrompt(`Implement based on this document: ${f.name}\n\n${text.substring(0, 3000)}`);
                    e.target.value = '';
                  }}
                />
                <button onClick={() => document.getElementById('agentDocUpload')?.click()} title="Upload spec, design doc, or code"
                  style={{ ...btn(C.bgDark), fontSize: 14, padding: '4px 8px' }}>📎</button>
                <button onClick={handleAgentSend} disabled={!selectedProject || agentLoading || !agentPrompt.trim()} style={{ ...btn(C.accent), opacity: agentLoading ? 0.5 : 1 }}>
                  {agentLoading ? '⏳' : '▶'}
                </button>
              </div>
              {selectedProject && (
                <div style={{ fontSize: 10, color: C.dim, marginTop: 4 }}>
                  Project: {selectedProject.name} · {selectedProject.project_folder}
                  {selectedFile && <span> · File: {selectedFile.name}</span>}
                </div>
              )}
            </div>
          </div>
        )}
        </div>

        {/* Full aggregation: extra sections */}
        {fullData && (fullData.version_control || fullData.cicd_pipelines || fullData.agent_status || fullData.testing_status) && (
          <div style={{ padding: '12px 16px', borderTop: `1px solid ${C.border}`, background: C.bg, maxHeight: 240, overflowY: 'auto' }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: C.muted, marginBottom: 10, textTransform: 'uppercase' }}>Full Aggregation</div>
            {fullData?.version_control && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Version Control</div>
                {typeof fullData.version_control === 'object' ? (
                  Object.entries(fullData.version_control).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.version_control)}</span>
                )}
              </div>
            )}
            {fullData?.cicd_pipelines && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>CI/CD Pipelines</div>
                {typeof fullData.cicd_pipelines === 'object' ? (
                  Object.entries(fullData.cicd_pipelines).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.cicd_pipelines)}</span>
                )}
              </div>
            )}
            {fullData?.agent_status && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Agent Status</div>
                {typeof fullData.agent_status === 'object' ? (
                  Object.entries(fullData.agent_status).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.agent_status)}</span>
                )}
              </div>
            )}
            {fullData?.testing_status && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Testing Status</div>
                {typeof fullData.testing_status === 'object' ? (
                  Object.entries(fullData.testing_status).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.testing_status)}</span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
