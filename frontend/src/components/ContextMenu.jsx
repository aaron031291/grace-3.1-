import React, { useState, useEffect } from 'react';
import { brainCall } from '../api/brain-client';

const C = {
    bg: '#12122a', bgDark: '#0a0a1a', bgHover: '#1a1a3a',
    accent: '#e94560', text: '#eee', dim: '#888', border: '#333'
};

export default function ContextMenu() {
    const [contextData, setContextData] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [prompt, setPrompt] = useState("");

    useEffect(() => {
        const handleContextMenu = (e) => {
            // Traverse up to find a marked context artifact
            let el = e.target;
            let artifact = null;

            while (el && el !== document.body) {
                if (el.dataset.artifactType) {
                    artifact = {
                        type: el.dataset.artifactType, // 'doc', 'code', 'folder'
                        id: el.dataset.artifactId,
                        name: el.dataset.artifactName,
                        domain: el.dataset.artifactDomain || 'Global'
                    };
                    break;
                }
                el = el.parentElement;
            }

            if (artifact) {
                e.preventDefault();
                setContextData({
                    x: e.clientX,
                    y: e.clientY,
                    artifact
                });
                setPrompt("");
            } else {
                setContextData(null);
            }
        };

        const handleClickOutside = () => setContextData(null);

        document.addEventListener('contextmenu', handleContextMenu);
        document.addEventListener('click', handleClickOutside);
        return () => {
            document.removeEventListener('contextmenu', handleContextMenu);
            document.removeEventListener('click', handleClickOutside);
        };
    }, []);

    if (!contextData) return null;

    const { x, y, artifact } = contextData;

    const handleAction = async (actionType, overridePrompt = null) => {
        setIsSubmitting(true);
        const instruction = overridePrompt || prompt || actionType;

        try {
            // Submit real task to Python backend
            const res = await fetch(`http://localhost:8000/api/devlab/task`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    artifact_path: artifact.id, // Absolute or relative path from tree
                    intent: instruction,
                    domain: artifact.domain
                })
            });

            if (res.ok) {
                const data = await res.json();

                // Dispatch custom event to tell App.jsx / DevTab.jsx to open this task
                window.dispatchEvent(new CustomEvent('DEVLAB_TASK_STARTED', {
                    detail: {
                        taskId: data.task_id,
                        artifactName: artifact.name,
                        intent: instruction
                    }
                }));
            } else {
                alert("Failed to start agent task.");
            }
        } catch (e) {
            alert("Network error starting agent.");
        }

        setIsSubmitting(false);
        setContextData(null);
    };

    const menuStyle = {
        position: 'fixed',
        top: Math.min(y, window.innerHeight - 250),
        left: Math.min(x, window.innerWidth - 250),
        width: 250,
        background: C.bg,
        border: `1px solid ${C.border}`,
        borderRadius: 8,
        boxShadow: '0 10px 30px rgba(0,0,0,0.8)',
        zIndex: 9999,
        overflow: 'hidden',
        padding: 8
    };

    const itemStyle = {
        padding: '8px 12px',
        cursor: 'pointer',
        fontSize: 12,
        color: C.text,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        borderRadius: 4,
        transition: 'background 0.1s'
    };

    return (
        <div style={menuStyle} onClick={e => e.stopPropagation()}>
            <div style={{ padding: '4px 8px 8px', borderBottom: `1px solid ${C.border}`, marginBottom: 6 }}>
                <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', fontWeight: 700 }}>{artifact.type} Options</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: C.text, marginTop: 4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{artifact.name}</div>
            </div>

            <div
                style={itemStyle}
                onMouseEnter={e => e.currentTarget.style.background = C.bgHover}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                onClick={() => handleAction('Refactor & Optimize')}
            >
                <span>🛠️</span> Code this (Refactor/Optimize)
            </div>
            <div
                style={itemStyle}
                onMouseEnter={e => e.currentTarget.style.background = C.bgHover}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                onClick={() => handleAction('Fix Bugs')}
            >
                <span>🐛</span> Fix this bug
            </div>

            <div style={{ padding: '8px', borderTop: `1px solid ${C.border}`, marginTop: 6 }}>
                <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', fontWeight: 700, marginBottom: 8 }}>Custom Request</div>
                <textarea
                    placeholder="Add this feature..."
                    value={prompt}
                    onChange={e => setPrompt(e.target.value)}
                    style={{ width: '100%', outline: 'none', background: C.bgDark, border: `1px solid ${C.border}`, borderRadius: 4, color: C.text, padding: 6, fontSize: 11, minHeight: 50, resize: 'none' }}
                    onClick={e => e.stopPropagation()} // Keep menu open when clicking textarea
                />
                <button
                    onClick={() => handleAction('Custom Feature', prompt)}
                    disabled={!prompt.trim() || isSubmitting}
                    style={{ width: '100%', marginTop: 6, background: C.accent, color: '#fff', border: 'none', padding: '6px', borderRadius: 4, fontSize: 11, fontWeight: 700, cursor: isSubmitting ? 'wait' : 'pointer', opacity: (!prompt.trim() || isSubmitting) ? 0.5 : 1 }}
                >
                    {isSubmitting ? 'Submitting...' : 'Send to Task Manager 🚀'}
                </button>
            </div>
        </div>
    );
}
