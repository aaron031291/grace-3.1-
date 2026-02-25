import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', accentAlt: '#533483',
  text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  success: '#4caf50', warn: '#ff9800',
};

const btn = {
  padding: '6px 14px', border: 'none', borderRadius: 4, cursor: 'pointer',
  fontSize: 13, fontWeight: 500, color: '#fff', background: C.accentAlt,
};

function formatBytes(b) {
  if (!b) return '0 B';
  const k = 1024, s = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(b) / Math.log(k));
  return (b / Math.pow(k, i)).toFixed(1) + ' ' + s[i];
}

function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
    + ' ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function fileIcon(name) {
  const ext = (name || '').split('.').pop().toLowerCase();
  const m = {
    pdf: '📕', doc: '📘', docx: '📘', txt: '📝', md: '📝',
    csv: '📊', json: '📋', xml: '📰', html: '🌐',
    py: '🐍', js: '🟨', ts: '🔷', jsx: '⚛️', tsx: '⚛️',
    png: '🖼️', jpg: '🖼️', jpeg: '🖼️', gif: '🖼️', svg: '🖼️',
    yaml: '⚙️', yml: '⚙️', toml: '⚙️', log: '📋',
  };
  return m[ext] || '📄';
}

function statusBadge(status) {
  const colors = { completed: C.success, pending: C.warn, processing: '#2196f3', failed: C.accent };
  return (
    <span style={{
      fontSize: 10, padding: '2px 6px', borderRadius: 3, fontWeight: 600,
      background: (colors[status] || C.dim) + '22', color: colors[status] || C.dim,
      textTransform: 'uppercase',
    }}>{status}</span>
  );
}

// ---------------------------------------------------------------------------
// Document row — used in both views
// ---------------------------------------------------------------------------
function DocRow({ doc, onSelect, selected }) {
  return (
    <div
      onClick={() => onSelect(doc)}
      style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px',
        cursor: 'pointer',
        background: selected ? C.bgDark : 'transparent',
        borderLeft: selected ? `3px solid ${C.accent}` : '3px solid transparent',
        transition: 'background .1s',
      }}
      onMouseEnter={e => { if (!selected) e.currentTarget.style.background = C.bgAlt; }}
      onMouseLeave={e => { if (!selected) e.currentTarget.style.background = 'transparent'; }}
    >
      <span style={{ fontSize: 20, flexShrink: 0 }}>{fileIcon(doc.filename)}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: C.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {doc.filename}
        </div>
        <div style={{ fontSize: 11, color: C.dim, marginTop: 2, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {doc.folder && <span>📁 {doc.folder}</span>}
          <span>{formatBytes(doc.file_size)}</span>
          <span>{fmtDate(doc.created_at)}</span>
        </div>
      </div>
      <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
        {statusBadge(doc.status)}
        {doc.total_chunks > 0 && (
          <span style={{ fontSize: 10, color: C.dim }}>{doc.total_chunks} chunks</span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function DocsTab() {
  const [view, setView] = useState('all');      // 'all' | 'folders'
  const [docs, setDocs] = useState([]);
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('newest');
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detail, setDetail] = useState(null);
  const [expandedFolders, setExpandedFolders] = useState(new Set());

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadFolder, setUploadFolder] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const fileRef = useRef(null);

  const [fullData, setFullData] = useState(null);
  const [notification, setNotification] = useState(null);
  const notifTimer = useRef(null);
  const notify = useCallback((msg, type = 'success') => {
    setNotification({ msg, type });
    clearTimeout(notifTimer.current);
    notifTimer.current = setTimeout(() => setNotification(null), 4000);
  }, []);

  // ── Fetch data ──────────────────────────────────────────────────────
  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ sort, limit: '500' });
      if (search) params.set('search', search);
      const res = await fetch(`${API_BASE_URL}/api/docs/all?${params}`);
      if (res.ok) { const d = await res.json(); setDocs(d.documents || []); }
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, [sort, search]);

  const fetchByFolder = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/docs/by-folder`);
      if (res.ok) { const d = await res.json(); setFolders(d.folders || []); }
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/docs/stats`);
      if (res.ok) setStats(await res.json());
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    if (view === 'all') fetchAll();
    else fetchByFolder();
    fetchStats();
  }, [view, fetchAll, fetchByFolder, fetchStats]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/tabs/docs/full`).then(r => r.ok ? r.json() : null).then(setFullData).catch(() => {});
  }, []);

  // Related docs & tags
  const [relatedDocs, setRelatedDocs] = useState([]);
  const [docTags, setDocTags] = useState([]);
  const [reprocessing, setReprocessing] = useState(false);

  // ── Doc detail ──────────────────────────────────────────────────────
  const loadDetail = useCallback(async (doc) => {
    setSelectedDoc(doc);
    setDetailLoading(true);
    setDetail(null);
    setRelatedDocs([]);
    setDocTags([]);
    try {
      const [detailRes, relatedRes, tagsRes] = await Promise.allSettled([
        fetch(`${API_BASE_URL}/api/docs/document/${doc.id}`),
        fetch(`${API_BASE_URL}/api/intelligence/document/${doc.id}/related?limit=6`),
        fetch(`${API_BASE_URL}/api/intelligence/document/${doc.id}/tags`),
      ]);
      if (detailRes.status === 'fulfilled' && detailRes.value.ok) setDetail(await detailRes.value.json());
      if (relatedRes.status === 'fulfilled' && relatedRes.value.ok) {
        const rd = await relatedRes.value.json();
        setRelatedDocs(rd.related || []);
      }
      if (tagsRes.status === 'fulfilled' && tagsRes.value.ok) {
        const td = await tagsRes.value.json();
        setDocTags([...(td.tags || []), ...(td.librarian_tags || []).map(t => t.name)]);
      }
    } catch { /* silent */ }
    finally { setDetailLoading(false); }
  }, []);

  const handleDelete = async (docId) => {
    if (!window.confirm('Delete this document from the library?')) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/docs/document/${docId}?delete_file=false`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      notify('Document removed from library');
      setSelectedDoc(null);
      setDetail(null);
      if (view === 'all') fetchAll(); else fetchByFolder();
      fetchStats();
    } catch (e) { notify(e.message, 'error'); }
  };

  // ── Upload ──────────────────────────────────────────────────────────
  const handleUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    let count = 0;
    for (const f of Array.from(files)) {
      try {
        const fd = new FormData();
        fd.append('file', f);
        fd.append('folder', uploadFolder);
        const res = await fetch(`${API_BASE_URL}/api/docs/upload`, { method: 'POST', body: fd });
        if (res.ok) count++;
      } catch { /* continue */ }
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = '';
    if (count > 0) {
      notify(`${count} file${count > 1 ? 's' : ''} added to library`);
      if (view === 'all') fetchAll(); else fetchByFolder();
      fetchStats();
    }
    setShowUpload(false);
  };

  // ── Toggle folder ───────────────────────────────────────────────────
  const toggleFolder = (name) => {
    setExpandedFolders(prev => {
      const n = new Set(prev);
      if (n.has(name)) n.delete(name); else n.add(name);
      return n;
    });
  };

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', height: '100%', color: C.text, background: C.bg, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', position: 'relative' }}>

      {notification && (
        <div style={{
          position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 100,
          padding: '8px 20px', borderRadius: 6, fontSize: 13, fontWeight: 500,
          background: notification.type === 'success' ? C.success : C.accent, color: '#fff',
          boxShadow: '0 4px 14px rgba(0,0,0,.4)',
        }}>{notification.msg}</div>
      )}

      {/* ── Left: Document list ──────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: `1px solid ${C.border}`, minWidth: 0 }}>

        {/* Header bar */}
        <div style={{ padding: '12px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 10, background: C.bgAlt }}>
          <span style={{ fontSize: 16, fontWeight: 700 }}>📚 Docs Library</span>
          {stats && (
            <span style={{ fontSize: 11, color: C.dim }}>
              {stats.total_documents} docs · {stats.total_size_mb || 0} MB · {stats.total_folders} folders
            </span>
          )}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
            <button onClick={() => setShowUpload(!showUpload)} style={{ ...btn, background: C.accent, fontSize: 12, padding: '4px 10px' }}>
              📤 Upload
            </button>
            <button onClick={() => { if (view === 'all') fetchAll(); else fetchByFolder(); fetchStats(); }} style={{ ...btn, background: C.bgDark, fontSize: 12, padding: '4px 10px' }}>↻</button>
          </div>
        </div>

        {/* Upload bar */}
        {showUpload && (
          <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              placeholder="Folder (optional, e.g. reports/2024)"
              value={uploadFolder}
              onChange={e => setUploadFolder(e.target.value)}
              style={{ padding: '5px 8px', border: `1px solid ${C.border}`, borderRadius: 4, background: C.bg, color: C.text, fontSize: 12, flex: '1 1 180px', outline: 'none' }}
            />
            <input type="file" ref={fileRef} onChange={handleUpload} style={{ display: 'none' }} multiple />
            <button onClick={() => fileRef.current?.click()} disabled={uploading} style={{ ...btn, background: C.success, fontSize: 12, padding: '5px 12px' }}>
              {uploading ? '⏳ Uploading...' : '📎 Choose Files'}
            </button>
            <button onClick={() => setShowUpload(false)} style={{ ...btn, background: C.border, fontSize: 12, padding: '5px 8px' }}>✕</button>
          </div>
        )}

        {/* View toggle + search + sort */}
        <div style={{ padding: '8px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', gap: 8, alignItems: 'center', background: C.bg }}>
          <div style={{ display: 'flex', background: C.bgAlt, borderRadius: 4, overflow: 'hidden' }}>
            <button onClick={() => setView('all')} style={{ ...btn, borderRadius: 0, fontSize: 12, padding: '5px 12px', background: view === 'all' ? C.accentAlt : 'transparent' }}>All Docs</button>
            <button onClick={() => setView('folders')} style={{ ...btn, borderRadius: 0, fontSize: 12, padding: '5px 12px', background: view === 'folders' ? C.accentAlt : 'transparent' }}>By Folder</button>
          </div>
          {view === 'all' && (
            <>
              <input
                placeholder="Search filename..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && fetchAll()}
                style={{ padding: '5px 8px', border: `1px solid ${C.border}`, borderRadius: 4, background: C.bgAlt, color: C.text, fontSize: 12, flex: 1, outline: 'none' }}
              />
              <select value={sort} onChange={e => setSort(e.target.value)} style={{ padding: '5px 6px', border: `1px solid ${C.border}`, borderRadius: 4, background: C.bgAlt, color: C.text, fontSize: 12, outline: 'none' }}>
                <option value="newest">Newest</option>
                <option value="oldest">Oldest</option>
                <option value="name">Name</option>
                <option value="size">Size</option>
              </select>
            </>
          )}
        </div>

        {/* Document list */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', color: C.dim, fontSize: 13 }}>Loading documents...</div>
          ) : view === 'all' ? (
            docs.length === 0 ? (
              <div style={{ padding: 60, textAlign: 'center', color: C.dim }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>📚</div>
                <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 6 }}>No documents yet</div>
                <div style={{ fontSize: 12 }}>Upload files to start building your library</div>
              </div>
            ) : (
              docs.map(doc => (
                <DocRow key={doc.id} doc={doc} selected={selectedDoc?.id === doc.id} onSelect={loadDetail} />
              ))
            )
          ) : (
            /* Folder view */
            folders.length === 0 ? (
              <div style={{ padding: 60, textAlign: 'center', color: C.dim }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>📁</div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>No folders yet</div>
              </div>
            ) : (
              folders.map(f => {
                const isOpen = expandedFolders.has(f.folder);
                return (
                  <div key={f.folder}>
                    <div
                      onClick={() => toggleFolder(f.folder)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px',
                        cursor: 'pointer', background: C.bgAlt, borderBottom: `1px solid ${C.border}`,
                        userSelect: 'none',
                      }}
                    >
                      <span style={{ fontSize: 10, width: 14, textAlign: 'center', color: C.muted }}>{isOpen ? '▼' : '▶'}</span>
                      <span style={{ fontSize: 16 }}>📁</span>
                      <span style={{ flex: 1, fontSize: 13, fontWeight: 600 }}>{f.folder}</span>
                      <span style={{ fontSize: 11, color: C.dim }}>{f.document_count} docs · {formatBytes(f.total_size)}</span>
                    </div>
                    {isOpen && f.documents.map(doc => (
                      <DocRow key={doc.id} doc={doc} selected={selectedDoc?.id === doc.id} onSelect={loadDetail} />
                    ))}
                  </div>
                );
              })
            )
          )}
        </div>
      </div>

      {/* ── Right: Document detail panel ─────────────────────────────── */}
      <div style={{ flex: '0 0 380px', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: C.bg }}>
        {selectedDoc ? (
          <>
            <div style={{ padding: '12px 16px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 22 }}>{fileIcon(selectedDoc.filename)}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {selectedDoc.filename}
                </div>
                <div style={{ fontSize: 11, color: C.dim }}>{selectedDoc.folder || '(root)'}</div>
              </div>
              <span onClick={() => { setSelectedDoc(null); setDetail(null); }} style={{ cursor: 'pointer', fontSize: 16, color: C.muted, lineHeight: 1 }}>✕</span>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px' }}>
              {detailLoading ? (
                <div style={{ padding: 30, textAlign: 'center', color: C.dim, fontSize: 13 }}>Loading details...</div>
              ) : detail ? (
                <>
                  {/* Meta info */}
                  <div style={{ marginBottom: 16 }}>
                    {[
                      ['Status', statusBadge(detail.status)],
                      ['Size', formatBytes(detail.file_size)],
                      ['Source', detail.source],
                      ['Upload method', detail.upload_method],
                      ['MIME type', detail.mime_type],
                      ['Folder', detail.folder || '(root)'],
                      ['Uploaded', fmtDate(detail.created_at)],
                      ['Updated', fmtDate(detail.updated_at)],
                      ['Chunks', detail.total_chunk_count || detail.total_chunks || 0],
                      ['Confidence', detail.confidence_score != null ? (detail.confidence_score * 100).toFixed(0) + '%' : '—'],
                      ['On disk', detail.file_exists_on_disk ? '✅ Yes' : '❌ No'],
                    ].map(([label, val]) => (
                      <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: `1px solid ${C.border}`, fontSize: 12 }}>
                        <span style={{ color: C.muted }}>{label}</span>
                        <span style={{ color: C.text, fontWeight: 500, textAlign: 'right' }}>{typeof val === 'string' || typeof val === 'number' ? val : val}</span>
                      </div>
                    ))}
                  </div>

                  {/* Tags */}
                  {detail.tags && detail.tags.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: C.muted, textTransform: 'uppercase', marginBottom: 6 }}>Tags</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {detail.tags.map((t, i) => (
                          <span key={i} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 10, background: C.accentAlt + '44', color: C.text }}>{t}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Description */}
                  {detail.description && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: C.muted, textTransform: 'uppercase', marginBottom: 6 }}>Description</div>
                      <div style={{ fontSize: 12, color: C.text, lineHeight: 1.5 }}>{detail.description}</div>
                    </div>
                  )}

                  {/* Chunk preview */}
                  {detail.chunks && detail.chunks.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: C.muted, textTransform: 'uppercase', marginBottom: 6 }}>
                        Content Preview ({detail.total_chunk_count} chunks)
                      </div>
                      {detail.chunks.slice(0, 5).map((chunk, i) => (
                        <div key={i} style={{ fontSize: 11, color: C.muted, padding: '6px 8px', marginBottom: 4, background: C.bgAlt, borderRadius: 4, border: `1px solid ${C.border}`, lineHeight: 1.5, maxHeight: 80, overflow: 'hidden' }}>
                          <span style={{ color: C.dim, fontSize: 10, marginRight: 6 }}>#{chunk.index}</span>
                          {chunk.text}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* File path */}
                  {detail.file_path && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: C.muted, textTransform: 'uppercase', marginBottom: 6 }}>File Path</div>
                      <code style={{ fontSize: 11, color: C.muted, wordBreak: 'break-all', background: C.bgAlt, padding: '4px 8px', borderRadius: 4, display: 'block' }}>{detail.file_path}</code>
                    </div>
                  )}

                  {/* Tags (from intelligence) */}
                  {docTags.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: C.muted, textTransform: 'uppercase', marginBottom: 6 }}>Auto-Tags (Librarian)</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {[...new Set(docTags)].map((t, i) => (
                          <span key={i} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 10, background: C.accentAlt + '44', color: C.text, cursor: 'pointer' }}
                            onClick={() => { setView('all'); setSearch(typeof t === 'string' ? t : t.name || ''); }}
                            title="Click to search by this tag"
                          >{typeof t === 'string' ? t : t.name || t}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Related documents */}
                  {relatedDocs.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: C.muted, textTransform: 'uppercase', marginBottom: 6 }}>
                        Related Documents ({relatedDocs.length})
                      </div>
                      {relatedDocs.map((rd, i) => (
                        <div
                          key={i}
                          onClick={() => { if (rd.document_id) loadDetail({ id: rd.document_id, filename: rd.filename }); }}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px',
                            marginBottom: 3, borderRadius: 4, cursor: 'pointer',
                            background: C.bgAlt, border: `1px solid ${C.border}`,
                            fontSize: 12, transition: 'background .1s',
                          }}
                          onMouseEnter={e => e.currentTarget.style.background = C.bgDark}
                          onMouseLeave={e => e.currentTarget.style.background = C.bgAlt}
                        >
                          <span>{fileIcon(rd.filename)}</span>
                          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{rd.filename}</span>
                          <span style={{ fontSize: 10, color: C.warn, flexShrink: 0 }}>
                            {rd.confidence ? (rd.confidence * 100).toFixed(0) + '%' : ''}
                          </span>
                          <span style={{ fontSize: 9, color: C.dim, flexShrink: 0 }}>{rd.relationship_type}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Full aggregation: extra sections */}
                  {fullData?.ingest_status && (
                    <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Ingest Status</div>
                      {typeof fullData.ingest_status === 'object' ? (
                        Object.entries(fullData.ingest_status).map(([k, v]) => (
                          <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                            <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                            <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                          </div>
                        ))
                      ) : (
                        <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.ingest_status)}</span>
                      )}
                    </div>
                  )}
                  {fullData?.ingestion_status && (
                    <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Ingestion Status</div>
                      {typeof fullData.ingestion_status === 'object' ? (
                        Object.entries(fullData.ingestion_status).map(([k, v]) => (
                          <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                            <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                            <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                          </div>
                        ))
                      ) : (
                        <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.ingestion_status)}</span>
                      )}
                    </div>
                  )}
                  {fullData?.kb_connectors && (
                    <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>KB Connectors</div>
                      {typeof fullData.kb_connectors === 'object' ? (
                        Object.entries(fullData.kb_connectors).map(([k, v]) => (
                          <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                            <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                            <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                          </div>
                        ))
                      ) : (
                        <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.kb_connectors)}</span>
                      )}
                    </div>
                  )}
                  {fullData?.intelligence_tags && (
                    <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Intelligence Tags</div>
                      {typeof fullData.intelligence_tags === 'object' ? (
                        Object.entries(fullData.intelligence_tags).map(([k, v]) => (
                          <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                            <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                            <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                          </div>
                        ))
                      ) : (
                        <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.intelligence_tags)}</span>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                    <button
                      onClick={async () => {
                        setReprocessing(true);
                        try {
                          const res = await fetch(`${API_BASE_URL}/api/intelligence/document/${detail.id}/reprocess`, { method: 'POST' });
                          if (res.ok) notify('Librarian reprocessing queued');
                          else notify('Reprocess failed', 'error');
                        } catch { notify('Reprocess failed', 'error'); }
                        finally { setReprocessing(false); }
                      }}
                      disabled={reprocessing}
                      style={{ ...btn, background: C.accentAlt, fontSize: 12, padding: '5px 12px', opacity: reprocessing ? 0.5 : 1 }}
                    >
                      {reprocessing ? '⏳ Processing...' : '🔄 Reprocess'}
                    </button>
                    <button onClick={() => handleDelete(detail.id)} style={{ ...btn, background: C.accent, fontSize: 12, padding: '5px 12px' }}>🗑 Remove</button>
                  </div>
                </>
              ) : (
                <div style={{ padding: 30, textAlign: 'center', color: C.dim, fontSize: 13 }}>Failed to load details</div>
              )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ textAlign: 'center', color: C.dim }}>
                <div style={{ fontSize: 48, marginBottom: 12, opacity: 0.5 }}>📋</div>
                <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4, color: C.muted }}>Select a document</div>
                <div style={{ fontSize: 12 }}>Click any document to see its details</div>
              </div>
            </div>
            {fullData && (fullData.ingest_status || fullData.ingestion_status || fullData.kb_connectors || fullData.intelligence_tags) && (
              <div style={{ padding: '12px 16px', borderTop: `1px solid ${C.border}` }}>
                {fullData?.ingest_status && (
                  <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Ingest Status</div>
                    {typeof fullData.ingest_status === 'object' ? Object.entries(fullData.ingest_status).map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                        <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                        <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                      </div>
                    )) : <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.ingest_status)}</span>}
                  </div>
                )}
                {fullData?.ingestion_status && (
                  <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Ingestion Status</div>
                    {typeof fullData.ingestion_status === 'object' ? Object.entries(fullData.ingestion_status).map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                        <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                        <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                      </div>
                    )) : <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.ingestion_status)}</span>}
                  </div>
                )}
                {fullData?.kb_connectors && (
                  <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>KB Connectors</div>
                    {typeof fullData.kb_connectors === 'object' ? Object.entries(fullData.kb_connectors).map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                        <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                        <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                      </div>
                    )) : <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.kb_connectors)}</span>}
                  </div>
                )}
                {fullData?.intelligence_tags && (
                  <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Intelligence Tags</div>
                    {typeof fullData.intelligence_tags === 'object' ? Object.entries(fullData.intelligence_tags).map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                        <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                        <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                      </div>
                    )) : <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.intelligence_tags)}</span>}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
