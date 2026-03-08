import React from 'react';
import KnowledgeBaseManager from './KnowledgeBaseManager';
import '../App.css';

/**
 * KnowledgeTab - Dedicated tab for managing the Knowledge Base, 
 * Separated from the Whitelist (Integrations) Tab.
 */
function KnowledgeTab() {
    return (
        <div className="tab-container fade-in">
            <div className="tab-header">
                <h1>Knowledge Base</h1>
                <p className="tab-subtitle">
                    Manage deterministic context, document embedding, and Qdrant memory synthesis.
                </p>
            </div>

            <div className="tab-content" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                <section className="dashboard-section" style={{ padding: 0, border: 'none', background: 'transparent' }}>
                    <KnowledgeBaseManager />
                </section>
            </div>
        </div>
    );
}

export default KnowledgeTab;
