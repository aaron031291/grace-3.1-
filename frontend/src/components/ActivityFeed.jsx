/**
 * ActivityFeed — Real-time ticker showing everything Grace is doing.
 * Floating panel (bottom-right), expandable, with icons per action type.
 */
import { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../config/api';

const ICONS = {
  file: '📄', upload: '📤', delete: '🗑️', heal: '🩹', learn: '📚',
  llm: '🧠', search: '🔍', trust: '🛡️', genesis: '🔑', error: '❌',
  system: '⚙️', code: '💻', consensus: '🤝', default: '▶️',
};

function getIcon(type) {
  if (!type) return ICONS.default;
  const t = type.toLowerCase();
  for (const [k, v] of Object.entries(ICONS)) {
    if (t.includes(k)) return v;
  }
  return ICONS.default;
}

function timeAgo(ts) {
  if (!ts) return '';
  const diff = (Date.now() - new Date(ts).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export default function ActivityFeed({ docked = false }) {
  const [events, setEvents] = useState([]);
  const [expanded, setExpanded] = useState(false);
  const [unread, setUnread] = useState(0);
  const intervalRef = useRef(null);

  // Drag state
  const [pos, setPos] = useState({ bottom: 24, left: 310 });
  const isDragging = useRef(false);
  const dragStartPos = useRef({ x: 0, y: 0 });
  const hasDragged = useRef(false);

  const handlePointerDown = (e) => {
    if (docked) return;
    // Prevent dragging from internal panel scroll/text
    if (expanded && e.target.closest('.activity-feed-panel')) return;
    isDragging.current = true;
    hasDragged.current = false;
    dragStartPos.current = { x: e.clientX, y: e.clientY };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e) => {
    if (!isDragging.current) return;
    const dx = e.clientX - dragStartPos.current.x;
    const dy = e.clientY - dragStartPos.current.y;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) hasDragged.current = true;
    dragStartPos.current = { x: e.clientX, y: e.clientY };
    setPos(p => ({ left: p.left + dx, bottom: p.bottom - dy }));
  };

  const handlePointerUp = (e) => {
    if (isDragging.current) {
      isDragging.current = false;
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
  };

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/bi/event-log?limit=30`);
        if (res.ok) {
          const data = await res.json();
          const newEvents = (data.events || []).map((e, i) => ({
            id: i, topic: e.topic || '', source: e.source || '',
            ts: e.ts || '', icon: getIcon(e.topic),
          }));
          setEvents(prevEvents => {
            if (newEvents.length > prevEvents.length) {
              setUnread(prev => prev + (newEvents.length - prevEvents.length));
            }
            return newEvents;
          });
        }
      } catch { /* polling, skip errors */ }
    };
    fetchEvents();
    intervalRef.current = setInterval(fetchEvents, 15000);
    return () => clearInterval(intervalRef.current);
  }, []);

  const toggle = () => {
    if (hasDragged.current) {
      hasDragged.current = false;
      return;
    }
    setExpanded(!expanded);
    if (!expanded) setUnread(0);
  };

  const feedContent = (
    <div className="activity-feed-panel" style={{
      width: docked ? '100%' : 340, height: docked ? '100%' : undefined,
      maxHeight: docked ? '100%' : 400, background: docked ? 'transparent' : '#1a1a2e', 
      border: docked ? 'none' : '1px solid #333',
      borderRadius: docked ? 0 : 10, boxShadow: docked ? 'none' : '0 8px 32px rgba(0,0,0,.5)', 
      overflow: 'hidden',
      marginBottom: docked ? 0 : 8, display: 'flex', flexDirection: 'column',
      cursor: 'default'
    }}>
      {!docked && (
        <div style={{
          padding: '10px 14px', borderBottom: '1px solid #333', background: '#16213e',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#eee' }}>Grace Activity</span>
          <span style={{ fontSize: 11, color: '#888' }}>{events.length} events</span>
        </div>
      )}
      <div style={{ flex: 1, overflow: 'auto', maxHeight: docked ? '100%' : 340 }}>
        {events.length === 0 && (
          <div style={{ padding: 20, textAlign: 'center', color: '#666', fontSize: 12 }}>
            No recent activity
          </div>
        )}
        {events.map(e => (
          <div key={e.id} style={{
            padding: '8px 12px', borderBottom: '1px solid #222',
            display: 'flex', gap: 8, alignItems: 'flex-start',
          }}>
            <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>{e.icon}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 11, color: '#ddd', overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {e.topic.replace(/\./g, ' → ')}
              </div>
              <div style={{ fontSize: 10, color: '#666' }}>
                {e.source} · {timeAgo(e.ts)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  if (docked) {
    return feedContent;
  }

  return (
    <div
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      style={{
        position: 'fixed', bottom: pos.bottom, left: pos.left, zIndex: 1000,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        touchAction: 'none' // Prevent scrolling while dragging
      }}
    >
      {expanded && feedContent}

      <button onClick={toggle} style={{
        width: 40, height: 40, borderRadius: '50%', border: 'none',
        background: expanded ? '#e94560' : '#533483', color: '#fff',
        fontSize: 18, cursor: 'pointer', position: 'relative',
        boxShadow: '0 4px 16px rgba(0,0,0,.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {expanded ? '✕' : '⚡'}
        {unread > 0 && !expanded && (
          <span style={{
            position: 'absolute', top: -4, right: -4, background: '#e94560',
            color: '#fff', fontSize: 10, fontWeight: 700, borderRadius: 10,
            padding: '1px 6px', minWidth: 16, textAlign: 'center',
          }}>{unread}</span>
        )}
      </button>
    </div>
  );
}
