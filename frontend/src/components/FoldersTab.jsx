import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../config/api';
import { CHUNKED_THRESHOLD } from '../hooks/useChunkedUpload';
import UploadProgress from './UploadProgress';

const COLORS = {
  bg: '#1a1a2e',
  bgAlt: '#16213e',
  bgDark: '#0f3460',
  accent: '#e94560',
  accentAlt: '#533483',
  text: '#eee',
  textMuted: '#aaa',
  textDim: '#888',
  border: '#333',
  success: '#4caf50',
  warning: '#ff9800',
  error: '#e94560',
};

const btnStyle = {
  padding: '6px 14px',
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 500,
  color: '#fff',
  background: COLORS.accentAlt,
  transition: 'opacity .15s',
};

const inputStyle = {
  padding: '7px 10px',
  border: `1px solid ${COLORS.border}`,
  borderRadius: 4,
  background: COLORS.bgAlt,
  color: COLORS.text,
  fontSize: 13,
  outline: 'none',
  width: '100%',
  boxSizing: 'border-box',
};

const _sectionTitle = {
  fontSize: 12,
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  color: COLORS.textMuted,
  marginBottom: 8,
  marginTop: 16,
};

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
}

function _fileIcon(nameOrExt) {
  const ext = (nameOrExt || '').split('.').pop().toLowerCase();
  const map = {
    md: '📝', txt: '📝', doc: '📝', docx: '📝', rtf: '📝',
    py: '🐍', js: '🟨', ts: '🔷', jsx: '⚛️', tsx: '⚛️',
    json: '📋', yaml: '⚙️', yml: '⚙️', toml: '⚙️', ini: '⚙️', cfg: '⚙️',
    csv: '📊', xml: '📰', html: '🌐', css: '🎨',
    pdf: '📕', png: '🖼️', jpg: '🖼️', jpeg: '🖼️', gif: '🖼️', svg: '🖼️',
    sh: '🖥️', bash: '🖥️', sql: '🗄️', log: '📋',
  };
  return map[ext] || '📄';
}

// ── Tree Node (Unused) ──────────────────────────────────────────────────
function _TreeNode({ node, depth, selectedPath, onSelect, expandedPaths, toggleExpand, searchFilter }) {
  const isDir = node.type === 'directory';
  const isExpanded = expandedPaths.has(node.path);
  const isSelected = selectedPath === node.path;
  const hasChildren = isDir && node.children && node.children.length > 0;

  const filtered = searchFilter
    ? node.name.toLowerCase().includes(searchFilter)
    : true;

  const childrenMatch = isDir && node.children?.some(c =>
    c.name.toLowerCase().includes(searchFilter || '') ||
    (c.children && c.children.length > 0)
  );

  if (searchFilter && !filtered && !childrenMatch) return null;

  return (
    <>
      <div
        onClick={() => {
          onSelect(node);
          if (isDir) toggleExpand(node.path);
        }}
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '4px 8px',
          paddingLeft: 8 + depth * 16,
          cursor: 'pointer',
          background: isSelected ? COLORS.bgDark : 'transparent',
          borderLeft: isSelected ? `2px solid ${COLORS.accent}` : '2px solid transparent',
          fontSize: 13,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          color: isSelected ? COLORS.text : COLORS.textMuted,
          userSelect: 'none',
        }}
        title={node.path}
      >
        {isDir && (
          <span style={{ marginRight: 4, fontSize: 10, width: 12, textAlign: 'center', flexShrink: 0 }}>
            {hasChildren ? (isExpanded ? '▼' : '▶') : ' '}
          </span>
        )}
        {!isDir && <span style={{ width: 16, flexShrink: 0 }} />}
        <span style={{ marginRight: 6, flexShrink: 0 }}>{isDir ? '📁' : '📄'}</span>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{node.name}</span>
        {isDir && node.file_count != null && (
          <span style={{ marginLeft: 'auto', paddingLeft: 8, fontSize: 11, color: COLORS.textDim, flexShrink: 0 }}>
            {node.file_count}
          </span>
        )}
      </div>
      {isDir && isExpanded && node.children && node.children.map(child => (
        <_TreeNode
          key={child.path}
          node={child}
          depth={depth + 1}
          selectedPath={selectedPath}
          onSelect={onSelect}
          expandedPaths={expandedPaths}
          toggleExpand={toggleExpand}
          searchFilter={searchFilter}
        />
      ))}
    </>
  );
}

// ── Main Component ─────────────────────────────────────────────────────
const FoldersTab = () => {
  const [_tree, setTree] = useState(null);
  const [_treeLoading, setTreeLoading] = useState(false);
  const [currentPath, setCurrentPath] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [dirItems, setDirItems] = useState([]);
  const [dirLoading, setDirLoading] = useState(false);
  const [fileContent, setFileContent] = useState('');
  const [fileLoading, setFileLoading] = useState(false);
  const [_stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [notification, setNotification] = useState(null);

  const [_expandedPaths, _setExpandedPaths] = useState(new Set());
  const [_treeSearch, _setTreeSearch] = useState('');
  const [showPlusMenu, setShowPlusMenu] = useState(false);

  // CRUD state
  const [newDirName, setNewDirName] = useState('');
  const [showNewDir, setShowNewDir] = useState(false);
  const [renameOld, setRenameOld] = useState('');
  const [renameNew, setRenameNew] = useState('');
  const [_showRename, setShowRename] = useState(false);
  const [moveSource, setMoveSource] = useState('');
  const [moveDest, setMoveDest] = useState('');
  const [_showMove, setShowMove] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [_uploadProgress, setUploadProgress] = useState(null);

  // AI state
  const [analyzeTarget, setAnalyzeTarget] = useState('');
  const [_useKimi, _setUseKimi] = useState(false);
  const [_analyzing, _setAnalyzing] = useState(false);
  const [_analysisResult, _setAnalysisResult] = useState(null);
  const [_organizeTarget, _setOrganizeTarget] = useState('');
  const [_organizeDryRun, _setOrganizeDryRun] = useState(true);
  const [_organizing, _setOrganizing] = useState(false);
  const [_organizeResult, _setOrganizeResult] = useState(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const [actionBusy, setActionBusy] = useState(false);

  // Editor state
  const [editMode, setEditMode] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [hasUnsaved, setHasUnsaved] = useState(false);
  const [showNewFile, setShowNewFile] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [viewMode, setViewMode] = useState('grid'); // grid or list

  const fileInputRef = useRef(null);
  const notifTimer = useRef(null);
  const editorRef = useRef(null);

  // ── Notifications ────────────────────────────────────────────────────
  const notify = useCallback((msg, type = 'success') => {
    setNotification({ msg, type });
    clearTimeout(notifTimer.current);
    notifTimer.current = setTimeout(() => setNotification(null), 4000);
  }, []);

  // ── Fetch tree ───────────────────────────────────────────────────────
  const fetchTree = useCallback(async () => {
    setTreeLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/tree`);
      if (!res.ok) throw new Error('Failed to load file tree');
      const data = await res.json();
      setTree(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setTreeLoading(false);
    }
  }, []);

  // ── Browse directory ─────────────────────────────────────────────────
  const browseDir = useCallback(async (path) => {
    setDirLoading(true);
    setSelectedFile(null);
    setFileContent('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/browse?path=${encodeURIComponent(path)}`);
      if (!res.ok) throw new Error('Failed to browse directory');
      const data = await res.json();
      setDirItems(data.items || data.children || data.entries || []);
    } catch (e) {
      setError(e.message);
      setDirItems([]);
    } finally {
      setDirLoading(false);
    }
  }, []);

  // ── Load file content ────────────────────────────────────────────────
  const loadFile = useCallback(async (path) => {
    setFileLoading(true);
    setFileContent('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/file/content?path=${encodeURIComponent(path)}`);
      if (!res.ok) throw new Error('Failed to load file');
      const data = await res.json();
      setFileContent(data.content ?? data.text ?? JSON.stringify(data, null, 2));
    } catch (e) {
      setError(e.message);
    } finally {
      setFileLoading(false);
    }
  }, []);

  // ── Fetch stats ──────────────────────────────────────────────────────
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/stats`);
      if (!res.ok) return;
      setStats(await res.json());
    } catch { /* silent */ }
  }, []);

  // ── Mount ────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchTree();
    fetchStats();
  }, [fetchTree, fetchStats]);

  useEffect(() => {
    browseDir(currentPath);
  }, [currentPath, browseDir]);

  // ── Tree interactions ────────────────────────────────────────────────
  const _toggleExpand = useCallback((path) => {
    _setExpandedPaths(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  const _handleTreeSelect = useCallback((node) => {
    // Mount to global context for agents
    window.selectedArtifacts = [{
      id: node.path,
      type: node.type === 'directory' ? 'folder' : 'code',
      name: node.name
    }];

    if (node.type === 'directory') {
      setCurrentPath(node.path);
      setSelectedFile(null);
    } else {
      setSelectedFile(node);
      loadFile(node.path);
      setAnalyzeTarget(node.path);
    }
  }, [loadFile]);

  const handleDirItemClick = useCallback((item) => {
    // Mount to global context for agents
    window.selectedArtifacts = [{
      id: item.path,
      type: (item.type === 'directory' || item.is_dir) ? 'folder' : 'code',
      name: item.name
    }];

    if (item.type === 'directory' || item.is_dir) {
      setCurrentPath(item.path);
      setSelectedFile(null);
    } else {
      setSelectedFile(item);
      loadFile(item.path);
      setAnalyzeTarget(item.path);
    }
  }, [loadFile]);

  // ── CRUD ─────────────────────────────────────────────────────────────
  const refresh = useCallback(() => {
    fetchTree();
    browseDir(currentPath);
    fetchStats();
  }, [fetchTree, browseDir, currentPath, fetchStats]);

  const handleCreateDir = async () => {
    if (!newDirName.trim()) return;
    setActionBusy(true);
    try {
      const dirPath = currentPath ? `${currentPath}/${newDirName}` : newDirName;
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/directory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: dirPath }),
      });
      if (!res.ok) throw new Error('Failed to create directory');
      setNewDirName('');
      setShowNewDir(false);
      notify('Directory created');
      refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setActionBusy(false);
    }
  };

  const _handleUpload = async (e, targetDir) => {
    const files = e.target ? e.target.files : e;
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadProgress(null);
    const uploadDir = targetDir ?? currentPath;
    let uploadCount = 0;
    try {
      for (const f of Array.from(files)) {
        if (f.size > CHUNKED_THRESHOLD) {
          // Large file — use chunked upload
          const initRes = await fetch(`${API_BASE_URL}/api/upload/initiate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              filename: f.name,
              file_size: f.size,
              folder: uploadDir,
              auto_ingest: true,
            }),
          });
          if (!initRes.ok) throw new Error(`Initiation failed for ${f.name}`);
          const { upload_id, total_chunks, chunk_size } = await initRes.json();

          for (let i = 0; i < total_chunks; i++) {
            const start = i * chunk_size;
            const end = Math.min(start + chunk_size, f.size);
            const blob = f.slice(start, end);
            const chunkData = await blob.arrayBuffer();
            const hashBuf = await crypto.subtle.digest('SHA-256', chunkData);
            const chunkHash = Array.from(new Uint8Array(hashBuf)).map(b => b.toString(16).padStart(2, '0')).join('');

            const fd = new FormData();
            fd.append('upload_id', upload_id);
            fd.append('chunk_index', String(i));
            fd.append('chunk_hash', chunkHash);
            fd.append('chunk', new Blob([chunkData]), `chunk_${i}`);

            const cRes = await fetch(`${API_BASE_URL}/api/upload/chunk`, { method: 'POST', body: fd });
            if (!cRes.ok) throw new Error(`Chunk ${i} failed for ${f.name}`);

            setUploadProgress({
              phase: 'uploading', percent: ((i + 1) / total_chunks) * 90,
              bytesUploaded: end, totalBytes: f.size,
            });
          }

          setUploadProgress({ phase: 'assembling', percent: 95, bytesUploaded: f.size, totalBytes: f.size });
          const compRes = await fetch(`${API_BASE_URL}/api/upload/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ upload_id }),
          });
          if (!compRes.ok) throw new Error(`Assembly failed for ${f.name}`);
          setUploadProgress({ phase: 'complete', percent: 100, bytesUploaded: f.size, totalBytes: f.size });
        } else {
          // Small file — direct upload
          const formData = new FormData();
          formData.append('file', f);
          formData.append('directory', uploadDir);
          const res = await fetch(`${API_BASE_URL}/api/librarian-fs/file/upload`, {
            method: 'POST',
            body: formData,
          });
          if (!res.ok) throw new Error(`Upload failed for ${f.name}`);
        }
        uploadCount++;
      }
      notify(`${uploadCount} file${uploadCount > 1 ? 's' : ''} uploaded to ${uploadDir || 'root'}`);
      refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      setUploadProgress(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteFile = async (path) => {
    if (!window.confirm(`Delete file "${path}"?`)) return;
    setActionBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/file?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      if (selectedFile?.path === path) { setSelectedFile(null); setFileContent(''); }
      notify('File deleted');
      refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setActionBusy(false);
    }
  };

  const handleDeleteDir = async (path) => {
    if (!window.confirm(`Delete directory "${path}" and all contents?`)) return;
    setActionBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/directory?path=${encodeURIComponent(path)}&force=true`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      if (currentPath.startsWith(path)) setCurrentPath('');
      notify('Directory deleted');
      refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setActionBusy(false);
    }
  };

  const _handleRename = async () => {
    if (!renameOld.trim() || !renameNew.trim()) return;
    setActionBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/file/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_path: renameOld, new_path: renameNew }),
      });
      if (!res.ok) throw new Error('Rename failed');
      setShowRename(false);
      setRenameOld('');
      setRenameNew('');
      notify('Renamed successfully');
      refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setActionBusy(false);
    }
  };

  const _handleMove = async () => {
    if (!moveSource.trim() || !moveDest.trim()) return;
    setActionBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/file/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_path: moveSource, destination_dir: moveDest }),
      });
      if (!res.ok) throw new Error('Move failed');
      setShowMove(false);
      setMoveSource('');
      setMoveDest('');
      notify('Moved successfully');
      refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setActionBusy(false);
    }
  };

  // ── Editor: save & create ───────────────────────────────────────────
  const handleSaveFile = async () => {
    if (!selectedFile?.path) return;
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/file/content`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile.path, content: editContent }),
      });
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || 'Save failed'); }
      const data = await res.json();
      setFileContent(editContent);
      setHasUnsaved(false);
      setSelectedFile(prev => ({ ...prev, size: data.size, modified: data.modified }));
      notify('File saved');
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateFile = async () => {
    if (!newFileName.trim()) return;
    setActionBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/file/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: newFileName.trim(), directory: currentPath, content: '' }),
      });
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || 'Create failed'); }
      const data = await res.json();
      setShowNewFile(false);
      setNewFileName('');
      notify('File created');
      refresh();
      setSelectedFile({ path: data.path, name: data.name, size: data.size });
      setEditMode(true);
      setEditContent('');
      setFileContent('');
      setHasUnsaved(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setActionBusy(false);
    }
  };

  const enterEditMode = () => {
    setEditMode(true);
    setEditContent(fileContent);
    setHasUnsaved(false);
  };

  const exitEditMode = () => {
    if (hasUnsaved && !window.confirm('Discard unsaved changes?')) return;
    setEditMode(false);
    setEditContent('');
    setHasUnsaved(false);
  };

  const handleEditorChange = (e) => {
    setEditContent(e.target.value);
    setHasUnsaved(e.target.value !== fileContent);
  };

  const handleEditorKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      handleSaveFile();
    }
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = e.target.selectionStart;
      const end = e.target.selectionEnd;
      const val = e.target.value;
      setEditContent(val.substring(0, start) + '  ' + val.substring(end));
      setHasUnsaved(true);
      requestAnimationFrame(() => {
        e.target.selectionStart = e.target.selectionEnd = start + 2;
      });
    }
  };

  // ── AI ───────────────────────────────────────────────────────────────
  const _handleAnalyze = async () => {
    if (!analyzeTarget.trim()) return;
    _setAnalyzing(true);
    _setAnalysisResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: analyzeTarget, use_kimi: _useKimi }),
      });
      if (!res.ok) throw new Error('Analysis failed');
      _setAnalysisResult(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      _setAnalyzing(false);
    }
  };

  const _handleAutoOrganize = async () => {
    if (!_organizeTarget.trim()) return;
    _setOrganizing(true);
    _setOrganizeResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/librarian-fs/auto-organize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: _organizeTarget, use_kimi: _useKimi, dry_run: _organizeDryRun }),
      });
      if (!res.ok) throw new Error('Auto-organize failed');
      _setOrganizeResult(await res.json());
      if (!_organizeDryRun) refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      _setOrganizing(false);
    }
  };

  // ── Search ───────────────────────────────────────────────────────────
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    setSearchResults([]);
    try {
      const res = await fetch(`${API_BASE_URL}/retrieve/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, limit: 10, threshold: 0.3 }),
      });
      if (!res.ok) throw new Error('Search failed');
      const data = await res.json();
      setSearchResults(data.chunks || data.results || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setSearching(false);
    }
  };

  // ── Breadcrumbs ──────────────────────────────────────────────────────
  const breadcrumbs = (() => {
    const parts = currentPath.split('/').filter(Boolean);
    const crumbs = [{ label: '📁 Root', path: '' }];
    let acc = '';
    for (const p of parts) {
      acc = acc ? `${acc}/${p}` : p;
      crumbs.push({ label: p, path: acc });
    }
    return crumbs;
  })();

  // ── Render ───────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', height: '100%', color: COLORS.text, background: COLORS.bg, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', position: 'relative' }}>

      {/* Notification toast */}
      {notification && (
        <div style={{
          position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
          zIndex: 100, padding: '8px 20px', borderRadius: 6, fontSize: 13, fontWeight: 500,
          background: notification.type === 'success' ? COLORS.success : COLORS.error,
          color: '#fff', boxShadow: '0 4px 14px rgba(0,0,0,.4)',
        }}>
          {notification.msg}
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div style={{
          position: 'absolute', top: 12, right: 12, zIndex: 100, padding: '8px 16px',
          borderRadius: 6, background: COLORS.error, color: '#fff', fontSize: 13,
          display: 'flex', alignItems: 'center', gap: 10, maxWidth: 400, boxShadow: '0 4px 14px rgba(0,0,0,.4)',
        }}>
          <span style={{ flex: 1 }}>{error}</span>
          <span onClick={() => setError(null)} style={{ cursor: 'pointer', fontWeight: 700, fontSize: 16 }}>×</span>
        </div>
      )}

      {/* Left panel removed per request */}

      {/* ── Center: Content ─────────────────────────────────────────── */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Breadcrumb */}
        <div style={{ padding: '8px 16px', borderBottom: `1px solid ${COLORS.border}`, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4, fontSize: 13, background: COLORS.bgAlt }}>
          {breadcrumbs.map((c, i) => (
            <span key={c.path} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              {i > 0 && <span style={{ color: COLORS.textDim }}>/</span>}
              <span
                onClick={() => { setCurrentPath(c.path); setSelectedFile(null); }}
                style={{ cursor: 'pointer', color: i === breadcrumbs.length - 1 ? COLORS.text : COLORS.textMuted, fontWeight: i === breadcrumbs.length - 1 ? 600 : 400 }}
              >
                {c.label}
              </span>
            </span>
          ))}
          <span onClick={refresh} style={{ marginLeft: 'auto', cursor: 'pointer', fontSize: 12, color: COLORS.textMuted }} title="Refresh">↻</span>
        </div>

        {/* Toolbar: Search */}
        <div style={{ padding: '8px 16px', borderBottom: `1px solid ${COLORS.border}`, display: 'flex', gap: 8, alignItems: 'center', background: COLORS.bgAlt, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, color: COLORS.textDim, fontWeight: 500 }}>path: {currentPath || '/'}</span>
          {uploading && <span style={{ fontSize: 12, color: COLORS.accent, fontWeight: 500 }}>⏳ Uploading...</span>}
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: 6, marginLeft: 'auto', flex: '0 1 300px' }}>
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{ ...inputStyle, flex: 1, fontSize: 12, padding: '5px 8px' }}
            />
            <button type="submit" disabled={searching} style={{ ...btnStyle, background: COLORS.accent, fontSize: 12, padding: '5px 10px', opacity: searching ? 0.6 : 1 }}>
              {searching ? '...' : '🔍'}
            </button>
          </form>
        </div>

        {/* Inline New Folder creation */}
        {showNewDir && (
          <div style={{ padding: '8px 16px', borderBottom: `1px solid ${COLORS.border}`, background: COLORS.bgAlt, display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: COLORS.textMuted }}>📁 Create in <b>{currentPath || '/'}</b>:</span>
            <input
              placeholder="folder-name (nested: a/b/c)"
              value={newDirName}
              onChange={e => setNewDirName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreateDir()}
              style={{ ...inputStyle, flex: 1, fontSize: 12, padding: '5px 8px' }}
              autoFocus
            />
            <button onClick={handleCreateDir} disabled={actionBusy} style={{ ...btnStyle, background: COLORS.success, fontSize: 12, padding: '5px 12px' }}>Create</button>
            <button onClick={() => { setShowNewDir(false); setNewDirName(''); }} style={{ ...btnStyle, background: COLORS.border, fontSize: 12, padding: '5px 8px' }}>✕</button>
          </div>
        )}

        {/* Search results */}
        {searchResults.length > 0 && (
          <div style={{ padding: '8px 16px', borderBottom: `1px solid ${COLORS.border}`, maxHeight: 240, overflowY: 'auto', background: COLORS.bgAlt }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: COLORS.textMuted }}>{searchResults.length} results</span>
              <span onClick={() => setSearchResults([])} style={{ cursor: 'pointer', fontSize: 12, color: COLORS.textDim }}>Clear</span>
            </div>
            {searchResults.map((r, i) => (
              <div key={i} style={{ padding: '8px 10px', marginBottom: 4, borderRadius: 4, background: COLORS.bg, fontSize: 12, border: `1px solid ${COLORS.border}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, color: COLORS.text }}>{r.metadata?.filename || `Doc ${r.document_id}`}</span>
                  <span style={{ color: COLORS.warning }}>{r.score ? (r.score * 100).toFixed(0) + '%' : ''}</span>
                </div>
                <div style={{ color: COLORS.textMuted, lineHeight: 1.4, whiteSpace: 'pre-wrap', maxHeight: 60, overflow: 'hidden' }}>{r.text}</div>
              </div>
            ))}
          </div>
        )}

        {/* Main content area — project-style document panel */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

          {!selectedFile ? (
            /* Document list — files in the current directory (FULL WIDTH) */
            <div style={{
              flex: 1, display: 'flex', flexDirection: 'column', background: COLORS.bg, position: 'relative'
            }}>

              {showNewDir && (
                <div style={{ padding: '8px 16px', borderBottom: `1px solid ${COLORS.border}`, display: 'flex', gap: 4, alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: COLORS.textMuted }}>📁 Create new folder:</span>
                  <input
                    placeholder="folder-name (nested: a/b/c)"
                    value={newDirName}
                    onChange={e => setNewDirName(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleCreateDir()}
                    style={{ ...inputStyle, fontSize: 12, padding: '5px 8px', flex: 1, maxWidth: 300 }}
                    autoFocus
                  />
                  <button onClick={handleCreateDir} disabled={actionBusy} style={{ ...btnStyle, fontSize: 12, padding: '5px 12px', background: COLORS.success }}>Create</button>
                  <button onClick={() => { setShowNewDir(false); setNewDirName(''); }} style={{ ...btnStyle, fontSize: 12, padding: '5px 8px', background: COLORS.border }}>✕</button>
                </div>
              )}

              {showNewFile && (
                <div style={{ padding: '8px 16px', borderBottom: `1px solid ${COLORS.border}`, display: 'flex', gap: 4 }}>
                  <span style={{ fontSize: 12, color: COLORS.textMuted }}>📄 Create new file:</span>
                  <input
                    placeholder="filename.md"
                    value={newFileName}
                    onChange={e => setNewFileName(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleCreateFile()}
                    style={{ ...inputStyle, fontSize: 12, padding: '5px 8px', flex: 1, maxWidth: 300 }}
                    autoFocus
                  />
                  <button onClick={handleCreateFile} disabled={actionBusy} style={{ ...btnStyle, fontSize: 12, padding: '5px 12px', background: COLORS.success }}>Create</button>
                  <button onClick={() => { setShowNewFile(false); setNewFileName(''); }} style={{ ...btnStyle, fontSize: 12, padding: '5px 8px', background: COLORS.border }}>✕</button>
                </div>
              )}

              {/* View toggle */}
              <div style={{ display: 'flex', gap: 2, padding: '8px 16px', background: COLORS.bg }}>
                <button onClick={() => setViewMode('grid')} style={{
                  padding: '4px 12px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12,
                  background: viewMode === 'grid' ? COLORS.accentAlt : 'transparent', color: viewMode === 'grid' ? '#fff' : COLORS.textMuted,
                }}>▦ Grid</button>
                <button onClick={() => setViewMode('list')} style={{
                  padding: '4px 12px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12,
                  background: viewMode === 'list' ? COLORS.accentAlt : 'transparent', color: viewMode === 'list' ? '#fff' : COLORS.textMuted,
                }}>☰ List</button>
              </div>

              <div style={{ flex: 1, overflowY: 'auto', padding: viewMode === 'grid' ? 16 : 0 }}>
                {dirLoading ? (
                  <div style={{ padding: 16, fontSize: 13, color: COLORS.textDim, textAlign: 'center' }}>Loading...</div>
                ) : viewMode === 'grid' ? (
                  /* ── GRID VIEW (Windows Explorer style) ──────────── */
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
                    {/* Folders */}
                    {dirItems.filter(i => i.type === 'directory' || i.is_dir).map(item => (
                      <div
                        key={item.path || item.name}
                        onClick={() => handleDirItemClick(item)}
                        style={{
                          width: 120, padding: '16px 8px', textAlign: 'center', cursor: 'pointer',
                          borderRadius: 8, background: 'transparent', transition: 'background .15s',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = COLORS.bgAlt}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                      >
                        <div style={{ fontSize: 48, marginBottom: 8 }}>📁</div>
                        <div style={{ fontSize: 12, color: COLORS.textMuted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
                          {item.name}
                        </div>
                        <div style={{ fontSize: 10, color: COLORS.textDim }}>{item.file_count ?? ''} items</div>
                      </div>
                    ))}
                    {/* Files */}
                    {dirItems.filter(i => i.type !== 'directory' && !i.is_dir).map(item => {
                      return (
                        <div
                          key={item.path || item.name}
                          onClick={() => handleDirItemClick(item)}
                          style={{
                            width: 120, padding: '16px 8px', textAlign: 'center', cursor: 'pointer',
                            borderRadius: 8, transition: 'background .15s', background: 'transparent', border: '1px solid transparent'
                          }}
                          onMouseEnter={e => e.currentTarget.style.background = COLORS.bgAlt}
                          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                        >
                          <div style={{ fontSize: 42, marginBottom: 8 }}>{_fileIcon(item.extension || item.name)}</div>
                          <div style={{
                            fontSize: 12, color: COLORS.textMuted,
                            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500
                          }}>
                            {item.name}
                          </div>
                          <div style={{ fontSize: 10, color: COLORS.textDim }}>{formatBytes(item.size)}</div>
                        </div>
                      );
                    })}
                    {dirItems.length === 0 && (
                      <div style={{ padding: '40px 16px', textAlign: 'center', color: COLORS.textDim, fontSize: 14, width: '100%' }}>
                        <div style={{ fontSize: 48, marginBottom: 12 }}>📂</div>
                        This folder is empty
                      </div>
                    )}
                  </div>
                ) : (
                  /* ── LIST VIEW (original) ────────────────────────── */
                  <div style={{ padding: 16 }}>
                    {dirItems.filter(i => i.type === 'directory' || i.is_dir).map(item => (
                      <div
                        key={item.path || item.name}
                        onClick={() => handleDirItemClick(item)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px',
                          cursor: 'pointer', fontSize: 13, color: COLORS.textMuted, borderRadius: 6,
                          background: 'transparent', transition: 'background .1s', borderBottom: `1px solid ${COLORS.bgAlt}`
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = COLORS.bgAlt}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                      >
                        <span style={{ flexShrink: 0, fontSize: 18 }}>📁</span>
                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>{item.name}</span>
                        <span style={{ fontSize: 11, color: COLORS.textDim }}>{item.file_count ?? ''} items</span>
                        <span onClick={e => { e.stopPropagation(); handleDeleteDir(item.path); }}
                          title="Delete folder" style={{ cursor: 'pointer', fontSize: 14, color: COLORS.textDim, opacity: 0.8, padding: 4 }}>🗑</span>
                      </div>
                    ))}
                    {dirItems.filter(i => i.type !== 'directory' && !i.is_dir).map(item => {
                      return (
                        <div
                          key={item.path || item.name}
                          onClick={() => handleDirItemClick(item)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', borderRadius: 6,
                            cursor: 'pointer', fontSize: 13, color: COLORS.textMuted, transition: 'all .1s', borderBottom: `1px solid ${COLORS.bgAlt}`
                          }}
                          onMouseEnter={e => e.currentTarget.style.background = COLORS.bgAlt}
                          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                        >
                          <span style={{ flexShrink: 0, fontSize: 18 }}>{_fileIcon(item.extension || item.name)}</span>
                          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
                            {item.name}
                          </span>
                          <span style={{ fontSize: 11, color: COLORS.textDim, flexShrink: 0, marginRight: 16 }}>{formatBytes(item.size)}</span>
                          <span onClick={e => { e.stopPropagation(); handleDeleteFile(item.path); }}
                            title="Delete file" style={{ cursor: 'pointer', fontSize: 14, color: COLORS.textDim, opacity: 0.8, padding: 4 }}>🗑</span>
                        </div>
                      );
                    })}
                    {dirItems.length === 0 && (
                      <div style={{ padding: '40px 16px', textAlign: 'center', color: COLORS.textDim, fontSize: 14, width: '100%' }}>
                        <div style={{ fontSize: 48, marginBottom: 12 }}>📂</div>
                        This folder is empty
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Floating + Menu */}
              <div style={{ position: 'absolute', bottom: 32, right: 32, zIndex: 1000, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 12 }}>
                {showPlusMenu && (
                  <div style={{ background: COLORS.bgAlt, border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: '8px 0', boxShadow: '0 8px 24px rgba(0,0,0,0.6)', minWidth: 160, overflow: 'hidden' }}>
                    <div style={{ padding: '12px 20px', fontSize: 14, cursor: 'pointer', color: COLORS.text, display: 'flex', gap: 10, transition: 'background 0.1s' }} onMouseEnter={e => e.currentTarget.style.background = COLORS.bgDark} onMouseLeave={e => e.currentTarget.style.background = 'transparent'} onClick={() => { setShowPlusMenu(false); setShowNewDir(true); }}><span>📁</span> New Folder</div>
                    <div style={{ padding: '12px 20px', fontSize: 14, cursor: 'pointer', color: COLORS.text, display: 'flex', gap: 10, transition: 'background 0.1s' }} onMouseEnter={e => e.currentTarget.style.background = COLORS.bgDark} onMouseLeave={e => e.currentTarget.style.background = 'transparent'} onClick={() => { setShowPlusMenu(false); setShowNewFile(true); }}><span>📄</span> New File</div>
                    <div style={{ padding: '12px 20px', fontSize: 14, cursor: 'pointer', color: COLORS.text, display: 'flex', gap: 10, transition: 'background 0.1s' }} onMouseEnter={e => e.currentTarget.style.background = COLORS.bgDark} onMouseLeave={e => e.currentTarget.style.background = 'transparent'} onClick={() => { setShowPlusMenu(false); fileInputRef.current?.click(); }}><span>📤</span> Upload</div>
                  </div>
                )}
                <button
                  onClick={() => setShowPlusMenu(!showPlusMenu)}
                  style={{ width: 64, height: 64, borderRadius: '50%', background: COLORS.accent, color: '#fff', fontSize: 32, paddingBottom: 4, border: 'none', cursor: 'pointer', boxShadow: '0 6px 20px rgba(233,69,96,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'transform 0.1s' }}
                  onMouseDown={e => e.currentTarget.style.transform = 'scale(0.95)'}
                  onMouseUp={e => e.currentTarget.style.transform = 'scale(1)'}
                >
                  {showPlusMenu ? '✕' : '+'}
                </button>
              </div>
            </div>

          ) : (

            /* Document editor / viewer */
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
              <>
                {/* Editor toolbar */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 12, padding: '12px 20px',
                  borderBottom: `1px solid ${COLORS.border}`, background: COLORS.bgAlt,
                  minHeight: 50,
                }}>
                  <button onClick={() => setSelectedFile(null)} style={{ ...btnStyle, background: COLORS.bg, border: `1px solid ${COLORS.border}`, marginRight: 12 }}>← Back</button>
                  <span style={{ fontSize: 18 }}>{_fileIcon(selectedFile.extension || selectedFile.name)}</span>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{selectedFile.name}</span>
                  {hasUnsaved && <span style={{ fontSize: 11, color: COLORS.accent, fontWeight: 700, padding: '2px 6px', background: 'rgba(233,69,96,0.2)', borderRadius: 4 }}>UNSAVED</span>}
                  {selectedFile.size != null && (
                    <span style={{ fontSize: 12, color: COLORS.textDim }}>{formatBytes(selectedFile.size)}</span>
                  )}

                  <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
                    {editMode ? (
                      <>
                        <button
                          onClick={handleSaveFile}
                          disabled={saving || !hasUnsaved}
                          style={{
                            ...btnStyle, fontSize: 13, padding: '6px 14px',
                            background: hasUnsaved ? COLORS.success : COLORS.bgDark,
                            opacity: saving ? 0.5 : 1,
                          }}
                        >
                          {saving ? '⏳ Saving...' : '💾 Save'}
                        </button>
                        <span style={{ fontSize: 11, color: COLORS.textDim }}>Ctrl+S</span>
                        <button
                          onClick={exitEditMode}
                          style={{ ...btnStyle, fontSize: 13, padding: '6px 12px', background: COLORS.border }}
                        >
                          👁️ View
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={enterEditMode}
                        style={{ ...btnStyle, fontSize: 13, padding: '6px 14px', background: COLORS.accentAlt }}
                      >
                        ✏️ Edit
                      </button>
                    )}
                    <span
                      onClick={e => { e.stopPropagation(); handleDeleteFile(selectedFile.path); }}
                      title="Delete file"
                      style={{ cursor: 'pointer', fontSize: 16, color: COLORS.textDim, padding: '4px', marginLeft: 8 }}
                    >🗑</span>
                    <span
                      onClick={() => { if (hasUnsaved && !window.confirm('Discard unsaved changes?')) return; setSelectedFile(null); setFileContent(''); setEditMode(false); setHasUnsaved(false); }}
                      style={{ cursor: 'pointer', fontSize: 20, color: COLORS.textMuted, padding: '4px', lineHeight: 1 }}
                    >✕</span>
                  </div>
                </div>

                {/* File content: editor or viewer */}
                <div style={{ flex: 1, overflow: 'auto' }}>
                  {fileLoading ? (
                    <div style={{ padding: 60, textAlign: 'center', color: COLORS.textDim, fontSize: 14 }}>Loading file content...</div>
                  ) : editMode ? (
                    <textarea
                      ref={editorRef}
                      value={editContent}
                      onChange={handleEditorChange}
                      onKeyDown={handleEditorKeyDown}
                      spellCheck={false}
                      style={{
                        width: '100%', height: '100%', resize: 'none',
                        background: '#0d1117', color: '#e6edf3',
                        border: 'none', outline: 'none',
                        padding: '24px 32px',
                        fontFamily: '"Fira Code", "JetBrains Mono", "SF Mono", "Cascadia Code", Consolas, monospace',
                        fontSize: 14, lineHeight: 1.7, tabSize: 2,
                        boxSizing: 'border-box',
                      }}
                    />
                  ) : (
                    <pre style={{
                      margin: 0, padding: '24px 32px',
                      fontFamily: '"Fira Code", "JetBrains Mono", "SF Mono", Consolas, monospace',
                      fontSize: 14, lineHeight: 1.7,
                      whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                      color: '#e6edf3', background: '#0d1117',
                      height: '100%', overflow: 'auto',
                    }}>
                      {fileContent || '(empty file — click Edit to start writing)'}
                    </pre>
                  )}
                </div>

                {/* Floating + Menu for Editor context */}
                <div style={{ position: 'absolute', bottom: 32, right: 32, zIndex: 1000, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 12 }}>
                  {showPlusMenu && (
                    <div style={{ background: COLORS.bgAlt, border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: '8px 0', boxShadow: '0 8px 24px rgba(0,0,0,0.6)', minWidth: 160, overflow: 'hidden' }}>
                      <div style={{ padding: '12px 20px', fontSize: 14, cursor: 'pointer', color: COLORS.text, display: 'flex', gap: 10, transition: 'background 0.1s' }} onMouseEnter={e => e.currentTarget.style.background = COLORS.bgDark} onMouseLeave={e => e.currentTarget.style.background = 'transparent'} onClick={() => { setShowPlusMenu(false); enterEditMode(); }}><span>✏️</span> Edit</div>
                      <div style={{ padding: '12px 20px', fontSize: 14, cursor: 'pointer', color: COLORS.text, display: 'flex', gap: 10, transition: 'background 0.1s' }} onMouseEnter={e => e.currentTarget.style.background = COLORS.bgDark} onMouseLeave={e => e.currentTarget.style.background = 'transparent'} onClick={() => { setShowPlusMenu(false); handleDeleteFile(selectedFile.path); }}><span>🗑️</span> Delete</div>
                      <div style={{ padding: '12px 20px', fontSize: 14, cursor: 'pointer', color: COLORS.text, display: 'flex', gap: 10, transition: 'background 0.1s' }} onMouseEnter={e => e.currentTarget.style.background = COLORS.bgDark} onMouseLeave={e => e.currentTarget.style.background = 'transparent'} onClick={() => { setShowPlusMenu(false); setEditContent(fileContent); setHasUnsaved(false); }}><span>↩️</span> Undo Changes</div>
                    </div>
                  )}
                  <button
                    onClick={() => setShowPlusMenu(!showPlusMenu)}
                    style={{ width: 64, height: 64, borderRadius: '50%', background: COLORS.accent, color: '#fff', fontSize: 32, paddingBottom: 4, border: 'none', cursor: 'pointer', boxShadow: '0 6px 20px rgba(233,69,96,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'transform 0.1s' }}
                    onMouseDown={e => e.currentTarget.style.transform = 'scale(0.95)'}
                    onMouseUp={e => e.currentTarget.style.transform = 'scale(1)'}
                  >
                    {showPlusMenu ? '✕' : '+'}
                  </button>
                </div>

              </>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FoldersTab;
