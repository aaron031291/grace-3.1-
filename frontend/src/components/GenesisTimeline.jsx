import React, { lazy, Suspense } from 'react';
import CommitTimeline from './version_control/CommitTimeline';

/**
 * GenesisTimeline Wrapper
 * This component wraps the version control timeline for the global app state.
 */
export default function GenesisTimeline({ domain, onClose }) {
    // Mock data for the timeline since it's a stub
    const [commits, setCommits] = React.useState([
        { sha: 'latest', message: `Initial Genesis for ${domain}`, author: 'Grace', timestamp: new Date().toISOString(), committer: 'Grace' }
    ]);

    return (
        <div style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', zIndex: 2000,
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20
        }}>
            <div style={{
                width: 600, maxHeight: '80vh', background: '#0d0d22', border: '1px solid #e94560',
                borderRadius: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column'
            }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid #1a1a2e', display: 'flex', justifyContent: 'space-between' }}>
                    <h3 style={{ margin: 0, color: '#e94560' }}>⧗ Genesis Timeline: {domain}</h3>
                    <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#888', cursor: 'pointer', fontSize: 20 }}>×</button>
                </div>
                <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
                    <CommitTimeline
                        commits={commits}
                        selectedCommit={commits[0]}
                        onSelectCommit={() => { }}
                        onRevert={() => alert('Revert functionality not implemented in stub')}
                    />
                </div>
            </div>
        </div>
    );
}
