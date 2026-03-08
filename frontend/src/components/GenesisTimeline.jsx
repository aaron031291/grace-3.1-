import React, { useState, useEffect } from 'react';
import { brainCall } from '../api/brain-client';
import './GenesisTimeline.css';

/**
 * GenesisTimeline
 * Streams and visualizes the structured internal Audit/Clarity framework
 * logs to give the user a transparent window into Grace's "thoughts"
 * and real-time playbook evaluations.
 */
function GenesisTimeline() {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchTimeline = async () => {
        try {
            const data = await brainCall('govern', 'audit_logs', { limit: 20 });
            if (data && data.logs) {
                setEvents(data.logs);
            }
        } catch (error) {
            console.error('Failed to fetch Genesis Timeline logs:', error);
        } finally {
            setLoading(false);
        }
    };

    // Poll the backend logs every 5 seconds for a "live stream" effect
    useEffect(() => {
        fetchTimeline();
        const interval = setInterval(fetchTimeline, 5000);
        return () => clearInterval(interval);
    }, []);

    if (loading && events.length === 0) {
        return <div className="genesis-timeline loading">Synchronizing Genesis Logs...</div>;
    }

    if (events.length === 0) {
        return <div className="genesis-timeline empty">No recent cognitive actions logged.</div>;
    }

    // Determine color schemes based on event severity or origin
    const getEventStyle = (event) => {
        const payloadStr = JSON.stringify(event.payload).toLowerCase();
        if (payloadStr.includes('error') || payloadStr.includes('fail') || event.action === 'escalate') {
            return 'event-critical';
        }
        if (payloadStr.includes('heal') || payloadStr.includes('playbook') || event.action === 'heal') {
            return 'event-heal';
        }
        if (event.action === 'decision' || event.action === 'approved') {
            return 'event-cognitive';
        }
        return 'event-info';
    };

    return (
        <div className="genesis-timeline">
            <h3><span className="live-dot" /> Grace Live "Thought" Stream</h3>
            <p className="subtitle">Real-time clarity logs from the Immutable Root Registry</p>

            <div className="timeline-container">
                {events.map((evt, index) => {
                    const styleClass = getEventStyle(evt);
                    const timestamp = new Date(evt.timestamp).toLocaleTimeString();

                    return (
                        <div key={index} className={`timeline-item ${styleClass}`}>
                            <div className="timeline-time">{timestamp}</div>
                            <div className="timeline-content">
                                <span className="action-badge">{evt.action || "SYSTEM"}</span>
                                <strong>{evt.target_id || "Global Mesh"}</strong>
                                <p className="rationale">
                                    {evt.payload?.description || evt.payload?.what_description || JSON.stringify(evt.payload)}
                                </p>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default GenesisTimeline;
