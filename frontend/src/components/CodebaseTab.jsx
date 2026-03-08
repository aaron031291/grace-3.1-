import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

import { FolderPlus, Upload, Edit, Move, Search, Network } from 'lucide-react';

const C = {
  bg: '#080814', bgAlt: '#12122a', highlight: '#1a1a3a',
  accent: '#e94560', success: '#3fb950', warn: '#d29922', error: '#f85149',
  buttonRed: '#e84855', buttonBlue: '#1b3b6f', buttonPurple: '#5b3c88', buttonYellow: '#f29c38',
  text: '#eee', dim: '#888', border: '#222', muted: '#aaa'
};

function langIcon(name) {
  const ext = (name || '').split('.').pop().toLowerCase();
  const m = { py: '🐍', js: '🟨', ts: '🔷', jsx: '⚛️', tsx: '⚛️', html: '🌐', css: '🎨', json: '📋', md: '📝', sh: '🖥️', sql: '🗄️', yaml: '⚙️', yml: '⚙️' };
  return m[ext] || '📄';
}

export default function CodebaseTab({ domain = "Global (All Domains)" }) {
  const [environments, setEnvironments] = useState(["root", "backend", "frontend"]);
  const [selectedEnv, setSelectedEnv] = useState("backend");

  const [tree, setTree] = useState(null);
  const [expanded, setExpanded] = useState(new Set());
  const [selectedNode, setSelectedNode] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [history, setHistory] = useState([]);
  const [diffMode, setDiffMode] = useState(false);
  const [compareVersion, setCompareVersion] = useState(null);
  const [compareContent, setCompareContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // Phase 29: File Manager UI Enhancements
  const [contextMenu, setContextMenu] = useState(null);
  const [toast, setToast] = useState(null);

  // Rename/edit state
  const [editingNodePath, setEditingNodePath] = useState(null);
  const [editingNodeName, setEditingNodeName] = useState("");

  // Analysis state
  const [analyzePath, setAnalyzePath] = useState("");
  const [useKimi, setUseKimi] = useState(false);

  const showToast = (msg, type = 'info') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const refreshTree = useCallback(async (env) => {
    try {
      const r = await fetch(`${API_BASE_URL}/api/codebase-hub/tree/${env}`);
      if (r.ok) {
        const d = await r.json();
        setTree(d?.children || []);
      } else {
        setTree([]);
        showToast('Failed to load tree', 'error');
      }
    } catch {
      setTree([]);
      showToast('Network error', 'error');
    }
  }, []);

  const fetchEnvironments = async () => {
    try {
      const r = await fetch(`${API_BASE_URL}/api/codebase-hub/projects`);
      if (r.ok) {
        const d = await r.json();
        if (d && d.length > 0) {
          setEnvironments(d);
          if (!d.includes(selectedEnv)) {
            setSelectedEnv(d[0]);
            refreshTree(d[0]);
          } else {
            refreshTree(selectedEnv);
          }
        }
      }
    } catch {
      refreshTree(selectedEnv);
    }
  };

  useEffect(() => {
    fetchEnvironments();
  }, [refreshTree]);

  const toggleExpand = path => {
    const nx = new Set(expanded);
    if (nx.has(path)) nx.delete(path); else nx.add(path);
    setExpanded(nx);
  };

  const handleSelect = async (node) => {
    setSelectedNode(node);
    setAnalyzePath(node.path);
    setDiffMode(false);
    setCompareVersion(null);
    if (node.type === 'file') {
      try {
        const res = await fetch(`${API_BASE_URL}/api/codebase-hub/file?path=${encodeURIComponent(node.path)}`);
        if (res.ok) {
          const d = await res.json();
          setFileContent(d.content || "");
          setHistory(d.genesis_history || []);
        } else {
          showToast('Failed to load file content', 'error');
        }
      } catch { showToast('Network error loading file', 'error'); }
    }
  };

  const handleContextMenu = (e, node) => {
    e.preventDefault();
    e.nativeEvent.stopImmediatePropagation();
    e.stopPropagation();
    setSelectedNode(node);
    setAnalyzePath(node.path);

    // Inject selected file into universal Dev Lab agent context
    window.selectedArtifacts = [{
      id: node.path,
      type: node.type === 'directory' ? 'folder' : 'code',
      name: node.name
    }];

    setContextMenu({ x: e.clientX, y: e.clientY, node });
  };

  const closeContextMenu = () => setContextMenu(null);

  const handleSave = async () => {
    if (!selectedNode || selectedNode.type !== 'file') return;
    setIsSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/codebase-hub/file`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedNode.path, content: fileContent })
      });
      if (res.ok) {
        handleSelect(selectedNode);
        showToast('Saved successfully', 'success');
      }
    } catch { showToast('Save failed', 'error'); }
    setIsSaving(false);
  };

  const handleAction = async (actionType) => {
    closeContextMenu();
    // Prompt-based actions for simplicity, can be replaced with Modals
    if (actionType === 'new_dir') {
      const dirName = prompt("Enter new directory name:");
      if (!dirName) return;
      const parentPath = selectedNode ? (selectedNode.type === 'directory' ? selectedNode.path : selectedNode.path.split('/').slice(0, -1).join('/')) : '';
      const fullPath = parentPath ? `${parentPath}/${dirName}` : dirName;

      try {
        const res = await fetch(`${API_BASE_URL}/api/codebase-hub/file/create`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_name: selectedEnv, type: 'directory', name: dirName, path: fullPath })
        });
        if (res.ok) { showToast('Directory created', 'success'); refreshTree(selectedEnv); }
      } catch { showToast('Failed to create directory', 'error'); }
    }

    else if (actionType === 'rename') {
      if (!selectedNode) return showToast("Select a file first", "warn");
      const newName = prompt("Enter new name:", selectedNode.name);
      if (!newName) return;
      try {
        const res = await fetch(`${API_BASE_URL}/api/codebase-hub/rename`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ old_path: selectedNode.path, new_name: newName })
        });
        if (res.ok) { showToast('Renamed successfully', 'success'); refreshTree(selectedEnv); }
      } catch { showToast('Rename failed', 'error'); }
    }

    else if (actionType === 'move') {
      if (!selectedNode) return showToast("Select a file first", "warn");
      const destPath = prompt("Enter destination folder path:", "");
      if (destPath === null) return;
      try {
        const res = await fetch(`${API_BASE_URL}/api/codebase-hub/move`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source_path: selectedNode.path, dest_path: destPath })
        });
        if (res.ok) { showToast('Moved successfully', 'success'); refreshTree(selectedEnv); }
      } catch { showToast('Move failed', 'error'); }
    }

    else if (actionType === 'upload') {
      const input = document.createElement('input');
      input.type = 'file';
      input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        const destDir = selectedNode && selectedNode.type === 'directory' ? selectedNode.path : '';
        try {
          const res = await fetch(`${API_BASE_URL}/api/codebase-hub/upload?directory=${encodeURIComponent(destDir)}`, {
            method: 'POST',
            body: formData
          });
          if (res.ok) { showToast('Uploaded successfully', 'success'); refreshTree(selectedEnv); }
        } catch { showToast('Upload failed', 'error'); }
      };
      input.click();
    }

    else if (actionType === 'analyze') {
      if (!analyzePath) return showToast("Enter a path to analyze", "warn");
      setFileContent(`Analyzing ${analyzePath}...`);
      try {
        const res = await fetch(`${API_BASE_URL}/api/codebase-hub/analyze`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: analyzePath, model: useKimi ? 'kimi' : 'qwen' })
        });
        if (res.ok) {
          const data = await res.json();
          setFileContent(data.analysis);
          showToast('Analysis complete', 'success');
        }
      } catch { showToast('Analysis failed', 'error'); }
    }

    else if (actionType === 'delete') {
      if (!selectedNode) return;
      if (!confirm(`Delete ${selectedNode.path}?`)) return;
      try {
        const res = await fetch(`${API_BASE_URL}/api/codebase-hub/file?path=${encodeURIComponent(selectedNode.path)}`, { method: 'DELETE' });
        if (res.ok) { showToast('Deleted successfully', 'success'); setSelectedNode(null); refreshTree(selectedEnv); }
      } catch { showToast('Delete failed', 'error'); }
    }
  };

  const handleDrop = async (sourcePath, destDir) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/codebase-hub/move`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_path: sourcePath, dest_path: destDir })
      });
      if (res.ok) { showToast('Moved successfully', 'success'); refreshTree(selectedEnv); }
    } catch { showToast('Move failed', 'error'); }
  };

  const handleRenameSubmit = async (node) => {
    if (!editingNodePath || editingNodeName === node.name || !editingNodeName.trim()) {
      setEditingNodePath(null);
      return;
    }
    const oldPath = node.path;
    const newName = editingNodeName;
    setEditingNodePath(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/codebase-hub/rename`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_path: oldPath, new_name: newName })
      });
      if (res.ok) { showToast('Renamed successfully', 'success'); refreshTree(selectedEnv); }
    } catch { showToast('Rename failed', 'error'); }
  };

  const loadDiff = async (h) => {
    setDiffMode(true);
    setCompareVersion(h.linear_version);
    setCompareContent("Loading snapshot...");
    try {
      const res = await fetch(`${API_BASE_URL}/api/codebase-hub/file/version?genesis_key=${h.genesis_key}`);
      if (res.ok) {
        const d = await res.json();
        setCompareContent(d.content || "");
      } else {
        setCompareContent(`Error loading snapshot tracking for ${h.genesis_key}`);
      }
    } catch {
      setCompareContent("Network error loading snapshot.");
    }
  };

  const TreeNode = ({ node, depth }) => {
    if (!node) return null;
    const isDir = node.type === 'directory';
    const isOpen = expanded.has(node.path);
    const isSel = selectedNode?.path === node.path;
    const hasKids = isDir && node.children?.length > 0;

    return (
      <>
        <div
          draggable
          onDragStart={(e) => { e.stopPropagation(); e.dataTransfer.setData('text/plain', node.path); }}
          onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); if (isDir) e.currentTarget.style.background = C.highlight; }}
          onDragLeave={(e) => { e.currentTarget.style.background = isSel ? C.highlight : 'transparent'; }}
          onDrop={(e) => {
            e.preventDefault();
            e.stopPropagation();
            e.currentTarget.style.background = isSel ? C.highlight : 'transparent';
            const source = e.dataTransfer.getData('text/plain');
            if (source && source !== node.path && isDir) handleDrop(source, node.path);
          }}
          onClick={(e) => { e.stopPropagation(); handleSelect(node); if (isDir) toggleExpand(node.path); }}
          onContextMenu={(e) => handleContextMenu(e, node)}
          data-artifact-type={isDir ? 'folder' : 'code'}
          data-artifact-id={node.path}
          data-context-item={JSON.stringify({ path: node.path, name: node.name, type: node.type })}
          style={{
            display: 'flex', alignItems: 'center', padding: '4px 8px', paddingLeft: 8 + depth * 12,
            cursor: 'pointer', fontSize: 13, color: isSel ? '#fff' : C.text,
            background: isSel ? C.highlight : 'transparent', userSelect: 'none',
            borderLeft: isSel ? `2px solid ${C.accent}` : '2px solid transparent',
          }}
        >
          {isDir && <span style={{ fontSize: 9, width: 14, textAlign: 'center', marginRight: 4, color: C.dim }}>{hasKids ? (isOpen ? '▼' : '▶') : ' '}</span>}
          {!isDir && <span style={{ width: 18 }} />}
          <span style={{ marginRight: 6 }}>{isDir ? '📁' : langIcon(node.name)}</span>

          {editingNodePath === node.path ? (
            <input
              value={editingNodeName}
              onChange={e => setEditingNodeName(e.target.value)}
              onBlur={() => handleRenameSubmit(node)}
              onKeyDown={e => { if (e.key === 'Enter') handleRenameSubmit(node); if (e.key === 'Escape') setEditingNodePath(null); }}
              autoFocus
              onClick={e => e.stopPropagation()}
              style={{ background: 'transparent', color: '#fff', border: `1px solid ${C.border}`, outline: 'none', fontSize: 13, padding: '0 4px', width: '100%' }}
            />
          ) : (
            <span
              onDoubleClick={(e) => { e.stopPropagation(); setEditingNodePath(node.path); setEditingNodeName(node.name); }}
              onClick={(e) => {
                if (isSel) { e.stopPropagation(); setEditingNodePath(node.path); setEditingNodeName(node.name); }
              }}
              style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              title="Click when selected or double click to rename"
            >
              {node.name}
            </span>
          )}
        </div>
        {isDir && isOpen && node.children?.map(c => <TreeNode key={c.path} node={c} depth={depth + 1} />)}
      </>
    );
  };

  const currentFolderFiles = selectedNode?.type === 'directory' ? selectedNode.children : [];

  return (
    <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }} onClick={closeContextMenu}>
      {/* Toast Notification */}
      {toast && (
        <div style={{ position: 'fixed', top: 20, right: 20, background: toast.type === 'error' ? C.buttonRed : C.success, color: '#fff', padding: '12px 24px', borderRadius: 8, zIndex: 9999, fontWeight: 700, boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}>
          {toast.msg} <span style={{ marginLeft: 12, cursor: 'pointer' }} onClick={() => setToast(null)}>×</span>
        </div>
      )}

      {/* Context Menu */}
      {contextMenu && (
        <div style={{
          position: 'fixed', top: contextMenu.y, left: contextMenu.x, background: C.bgAlt, border: `1px solid ${C.border}`,
          borderRadius: 6, padding: '4px 0', zIndex: 1000, boxShadow: '0 4px 12px rgba(0,0,0,0.5)', minWidth: 150
        }}>
          <div style={{ padding: '8px 16px', fontSize: 13, color: C.text, cursor: 'pointer' }} onClick={() => handleAction('new_dir')}>📁 New Directory</div>
          <div style={{ padding: '8px 16px', fontSize: 13, color: C.text, cursor: 'pointer' }} onClick={() => handleAction('upload')}>📤 Upload File</div>
          <div style={{ padding: '8px 16px', fontSize: 13, color: C.text, cursor: 'pointer' }} onClick={() => { closeContextMenu(); setEditingNodePath(contextMenu.node.path); setEditingNodeName(contextMenu.node.name); }}>✏️ Rename</div>
          {contextMenu.node.type === 'file' && <div style={{ padding: '8px 16px', fontSize: 13, color: C.text, cursor: 'pointer' }} onClick={() => handleAction('analyze')}>🤖 AI Analyze (Kimi)</div>}
          <div style={{ height: 1, background: C.border, margin: '4px 0' }} />
          <div style={{ padding: '8px 16px', fontSize: 13, color: C.error, cursor: 'pointer' }} onClick={() => handleAction('delete')}>🗑️ Delete</div>
        </div>
      )}

      {/* Codebase Editor & Genesis History */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: C.bg }}>
        {!selectedNode ? (
          <div style={{ margin: 'auto', textAlign: 'center', color: C.dim }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>📁</div>
            <div style={{ fontSize: 14 }}>Select a file or folder from the explorer.</div>
          </div>
        ) : selectedNode.type === 'directory' ? (
          <div style={{ padding: 24, overflowY: 'auto' }}>
            <h2 style={{ margin: '0 0 16px 0', color: '#fff', fontSize: 18 }}>{selectedNode.path}</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
              {currentFolderFiles?.map(f => (
                <div
                  key={f.path}
                  onClick={() => handleSelect(f)}
                  onContextMenu={(e) => handleContextMenu(e, f)}
                  style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 6, padding: 16, cursor: 'pointer', transition: 'all 0.1s' }}
                  data-artifact-type={f.type === 'directory' ? 'folder' : 'code'}
                >
                  <div style={{ fontSize: 24, marginBottom: 8 }}>{f.type === 'directory' ? '📁' : langIcon(f.name)}</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.name}</div>
                  <div style={{ fontSize: 11, color: C.dim, marginTop: 4 }}>Size: {f.size || 'N/A'} bytes</div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
            {/* Code Panel */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '12px 16px', background: C.bgAlt, borderBottom: `1px solid ${C.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 16 }}>{langIcon(selectedNode.name)}</span>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#fff' }}>{selectedNode.name}</div>
                </div>
                {!diffMode && (
                  <button
                    onClick={handleSave}
                    disabled={isSaving}
                    style={{ background: C.success, color: '#fff', border: 'none', padding: '6px 16px', borderRadius: 4, fontSize: 13, fontWeight: 700, cursor: isSaving ? 'wait' : 'pointer', transition: 'all 0.1s' }}
                  >
                    {isSaving ? '⧗ Minting Genesis Key...' : 'Save & Track Revision'}
                  </button>
                )}
                {diffMode && (
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <div style={{ fontSize: 11, background: C.warn, color: '#000', padding: '2px 8px', borderRadius: 4, fontWeight: 800 }}>
                      VISUAL DIFF (Current vs {compareVersion})
                    </div>
                    <button onClick={() => setDiffMode(false)} style={{ background: C.bgAlt, color: C.text, border: `1px solid ${C.border}`, padding: '4px 12px', borderRadius: 4, fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>
                      Exit Diff
                    </button>
                  </div>
                )}
              </div>

              {diffMode ? (
                <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                  <textarea
                    readOnly
                    value={`// (Historic Genesis Version: ${compareVersion})\n\n${compareContent}`}
                    style={{ flex: 1, background: '#1c0f13', color: '#ffb3b3', border: 'none', borderRight: `1px solid ${C.border}`, padding: 16, fontFamily: 'monospace', fontSize: 13, resize: 'none', outline: 'none' }}
                  />
                  <textarea
                    readOnly
                    value={`// Current Live Version\n\n${fileContent}`}
                    style={{ flex: 1, background: '#0e1f14', color: '#b3ffb3', border: 'none', padding: 16, fontFamily: 'monospace', fontSize: 13, resize: 'none', outline: 'none' }}
                  />
                </div>
              ) : (
                <textarea
                  value={fileContent}
                  onChange={e => setFileContent(e.target.value)}
                  style={{ flex: 1, background: C.bg, color: C.text, border: 'none', padding: 16, fontFamily: 'monospace', fontSize: 13, resize: 'none', outline: 'none', lineHeight: 1.5 }}
                />
              )}
            </div>

            {/* Genesis History Panel (Right Slide-out) */}
            <div style={{ width: 280, borderLeft: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '16px', borderBottom: `1px solid ${C.border}` }}>
                <div style={{ fontSize: 14, fontWeight: 800, color: '#fff' }}>⧗ Genesis History</div>
                <div style={{ fontSize: 11, color: C.dim, marginTop: 4 }}>Immutable version lineage</div>
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
                {history.map((h, i) => (
                  <div
                    key={i}
                    onDoubleClick={() => loadDiff(h)}
                    style={{ background: C.bg, border: `1px solid ${compareVersion === h.linear_version ? C.accent : C.border}`, borderRadius: 6, padding: 12, cursor: 'pointer', transition: 'all 0.1s' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 800, color: i === 0 ? C.success : C.text }}>{h.linear_version} {i === 0 && '(Live)'}</span>
                      <span style={{ fontSize: 10, color: C.dim }}>{h.timestamp}</span>
                    </div>
                    <div style={{ fontSize: 11, color: C.muted, marginBottom: 4 }}>{h.trigger}</div>
                    <div style={{ fontSize: 10, fontFamily: 'monospace', color: C.dim }}>{h.genesis_key}</div>
                    {i !== 0 && <div style={{ fontSize: 10, color: C.accent, marginTop: 8, fontStyle: 'italic' }}>Double-click to diff</div>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}


