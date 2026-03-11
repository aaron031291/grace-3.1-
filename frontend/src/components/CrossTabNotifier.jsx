/**
 * CrossTabNotifier — Notifications when Grace finds something relevant
 * in another tab. Click to navigate to that tab.
 */
import { useState, useEffect } from 'react';

let _notifications = [];
let _notifListeners = [];
let _navigateFn = null;

// eslint-disable-next-line react-refresh/only-export-components
export function setNavigator(fn) { _navigateFn = fn; }

// eslint-disable-next-line react-refresh/only-export-components
export function notify(message, targetTab, type = 'info') {
  const notif = {
    id: Date.now(),
    message,
    targetTab,
    type,
    ts: new Date().toISOString(),
    read: false,
  };
  _notifications = [notif, ..._notifications].slice(0, 20);
  _notifListeners.forEach(fn => fn([..._notifications]));
}

export default function CrossTabNotifier() {
  const [notifications, setNotifications] = useState([]);
  const [showPanel, setShowPanel] = useState(false);

  useEffect(() => {
    _notifListeners.push(setNotifications);
    return () => { _notifListeners = _notifListeners.filter(fn => fn !== setNotifications); };
  }, []);

  const unread = notifications.filter(n => !n.read).length;

  const handleClick = (notif) => {
    notif.read = true;
    setNotifications([...notifications]);
    if (_navigateFn && notif.targetTab) {
      _navigateFn(notif.targetTab);
    }
    setShowPanel(false);
  };

  const clearAll = () => {
    _notifications = [];
    setNotifications([]);
  };

  const COLORS = { info: '#2196f3', warning: '#ff9800', error: '#e94560', success: '#4caf50' };

  return (
    <div style={{ position: 'relative' }}>
      <button onClick={() => setShowPanel(!showPanel)} style={{
        background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px',
        color: unread > 0 ? '#e94560' : '#888', fontSize: 16, position: 'relative',
      }}>
        🔔
        {unread > 0 && (
          <span style={{
            position: 'absolute', top: -2, right: 0, background: '#e94560',
            color: '#fff', fontSize: 9, fontWeight: 700, borderRadius: 8,
            padding: '0 4px', minWidth: 14, textAlign: 'center',
          }}>{unread}</span>
        )}
      </button>

      {showPanel && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, width: 320,
          background: '#1a1a2e', border: '1px solid #333', borderRadius: 8,
          boxShadow: '0 8px 24px rgba(0,0,0,.5)', zIndex: 1000,
          maxHeight: 400, overflow: 'auto',
        }}>
          <div style={{
            padding: '8px 12px', borderBottom: '1px solid #333',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#eee' }}>Notifications</span>
            {notifications.length > 0 && (
              <button onClick={clearAll} style={{
                background: 'none', border: 'none', color: '#666',
                fontSize: 10, cursor: 'pointer',
              }}>Clear all</button>
            )}
          </div>
          {notifications.length === 0 && (
            <div style={{ padding: 20, textAlign: 'center', color: '#666', fontSize: 12 }}>
              No notifications
            </div>
          )}
          {notifications.map(n => (
            <div key={n.id} onClick={() => handleClick(n)} style={{
              padding: '10px 12px', borderBottom: '1px solid #222', cursor: 'pointer',
              background: n.read ? 'transparent' : '#16213e11',
              borderLeft: `3px solid ${COLORS[n.type] || COLORS.info}`,
            }}>
              <div style={{ fontSize: 12, color: n.read ? '#888' : '#eee' }}>{n.message}</div>
              {n.targetTab && (
                <div style={{ fontSize: 10, color: COLORS[n.type], marginTop: 2 }}>
                  → Open {n.targetTab}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
