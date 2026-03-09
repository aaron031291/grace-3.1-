import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../config/api';

const TerminalLogViewer = ({ onClose }) => {
    const [logs, setLogs] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isPaused, setIsPaused] = useState(false);
    const scrollRef = useRef(null);
    const wsRef = useRef(null);

    useEffect(() => {
        // Convert http/https to ws/wss
        const wsUrl = API_BASE_URL.replace(/^http/, 'ws') + '/api/autonomous/logs/stream';

        const connect = () => {
            wsRef.current = new WebSocket(wsUrl);

            wsRef.current.onopen = () => {
                setIsConnected(true);
                setLogs(prev => [...prev, '\x1b[32m[SYSTEM] Connected to Grace Autonomous Core log stream...\x1b[0m']);
            };

            wsRef.current.onmessage = (event) => {
                if (!isPaused) {
                    setLogs(prev => {
                        const newLogs = [...prev, event.data];
                        // Keep last 1000 lines max
                        return newLogs.length > 1000 ? newLogs.slice(newLogs.length - 1000) : newLogs;
                    });
                }
            };

            wsRef.current.onclose = () => {
                setIsConnected(false);
                setLogs(prev => [...prev, '\x1b[31m[SYSTEM] Disconnected from log stream. Reconnecting...\x1b[0m']);
                setTimeout(connect, 3000);
            };

            wsRef.current.onerror = (error) => {
                console.error("WebSocket error", error);
                wsRef.current.close();
            };
        };

        connect();

        return () => {
            if (wsRef.current) {
                wsRef.current.onclose = null; // Prevent reconnect loop on unmount
                wsRef.current.close();
            }
        };
    }, [isPaused]);

    // Auto-scroll to bottom
    useEffect(() => {
        if (!isPaused && scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs, isPaused]);

    const clearLogs = () => setLogs([]);

    // Simple ANSI color parser (very basic)
    const renderLogLine = (line, index) => {
        if (!line) return null;

        // Highlight specific keywords if no ANSI codes are present
        let color = '#ccc';
        let fontWeight = 'normal';

        if (line.includes('[ERROR]') || line.includes('Exception') || line.includes('Failed')) {
            color = '#f44336';
        } else if (line.includes('[WARNING]') || line.includes('WARN')) {
            color = '#ff9800';
        } else if (line.includes('[INFO]') || line.includes('SUCCESS') || line.includes('[OK]')) {
            color = '#4caf50';
        } else if (line.includes('DEBUG')) {
            color = '#888';
        } else if (line.includes('API') || line.includes('HTTP')) {
            color = '#2196f3';
        }

        // Quick hack for the system messages we inject above
        if (line.includes('\\x1b[32m')) color = '#4caf50';
        if (line.includes('\\x1b[31m')) color = '#f44336';

        const cleanLine = line.replace(/\\x1b\[\d+m/g, '').replace(/\[0m/g, '');

        return (
            <div key={index} style={{ color, fontWeight, marginBottom: 2, wordBreak: 'break-all' }}>
                {cleanLine}
            </div>
        );
    };

    return (
        <div style={{
            position: 'fixed',
            bottom: 24,
            right: 320, // Next to ActivityFeed
            width: 600,
            height: 400,
            background: 'rgba(10, 10, 26, 0.95)',
            border: '1px solid #333',
            borderRadius: 8,
            boxShadow: '0 8px 32px rgba(0,0,0,0.8)',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 999,
            fontFamily: 'monospace',
            backdropFilter: 'blur(10px)',
        }}>
            {/* Terminal Header */}
            <div style={{
                height: 32,
                background: '#16162a',
                borderBottom: '1px solid #333',
                display: 'flex',
                alignItems: 'center',
                padding: '0 12px',
                borderTopLeftRadius: 8,
                borderTopRightRadius: 8,
                justifyContent: 'space-between',
                cursor: 'move' // Note: add drag capability later if needed
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: isConnected ? '#4caf50' : '#f44336' }} />
                    <span style={{ fontSize: 12, color: '#eee', fontWeight: 'bold' }}>Grace Core Terminal</span>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={() => setIsPaused(!isPaused)} style={btnStyle}>
                        {isPaused ? '▶ Resume' : '⏸ Pause'}
                    </button>
                    <button onClick={clearLogs} style={btnStyle}>🗑 Clear</button>
                    <button onClick={onClose} style={{ ...btnStyle, color: '#e94560' }}>✕</button>
                </div>
            </div>

            {/* Terminal Body */}
            <div
                ref={scrollRef}
                style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: 12,
                    fontSize: 12,
                    lineHeight: 1.4,
                }}>
                {logs.map((line, i) => renderLogLine(line, i))}
                {logs.length === 0 && <div style={{ color: '#666' }}>Waiting for logs...</div>}
            </div>
        </div>
    );
};

const btnStyle = {
    background: 'transparent',
    border: '1px solid #444',
    color: '#aaa',
    borderRadius: 4,
    padding: '2px 8px',
    fontSize: 11,
    cursor: 'pointer',
};

export default TerminalLogViewer;
