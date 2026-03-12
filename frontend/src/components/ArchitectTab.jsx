import { useState } from "react";
import { brainCall } from "../api/brain-client";

const C = {
    bg: "#0a0a1a",
    panel: "#0d0d22",
    border: "#1a1a2e",
    accent: "#e94560",
    success: "#4caf50",
    amber: "#ff9800",
    muted: "#555",
    text: "#ccc",
};

function needScoreColor(score) {
    if (score >= 8) return C.success;
    if (score >= 5) return C.amber;
    return C.accent;
}

const DEFAULT_JSON = `{
  "name": "Metrics Aggregator",
  "description": "Collects real-time events and aggregates them for the dashboard",
  "capabilities": ["data_aggregation", "realtime_metrics"]
}`;

export default function ArchitectTab() {
    const [jsonSpec, setJsonSpec] = useState(DEFAULT_JSON);
    const [loading, setLoading] = useState(false);
    const [proposal, setProposal] = useState(null);
    const [error, setError] = useState(null);
    const [buildStatus, setBuildStatus] = useState(null);
    const [building, setBuilding] = useState(false);

    const handlePropose = async () => {
        setLoading(true);
        setError(null);
        setProposal(null);
        setBuildStatus(null);
        try {
            let spec;
            try {
                spec = JSON.parse(jsonSpec);
            } catch (e) {
                throw new Error("Invalid JSON: " + e.message);
            }

            const data = await brainCall("ai", "propose_architecture", { spec });
            if (!data.ok) throw new Error(data.error || "Proposal failed");

            setProposal(data.data);
        } catch (err) {
            setError(err?.message || "Request failed");
        } finally {
            setLoading(false);
        }
    };

    const handleBuild = async () => {
        if (!proposal?.proposal_id) return;
        setBuilding(true);
        setError(null);
        try {
            const data = await brainCall("ai", "build_architecture", { proposal_id: proposal.proposal_id });
            if (!data.ok) throw new Error(data.error || "Build launch failed");

            setBuildStatus(data.data);
        } catch (err) {
            setError(err?.message || "Build request failed");
        } finally {
            setBuilding(false);
        }
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", height: "100%", background: C.bg, color: C.text }}>
            <div style={{ padding: 16, borderBottom: `1px solid ${C.border}`, background: C.panel }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: C.accent, marginBottom: 8 }}>
                    Architecture Proposer
                </div>
                <div style={{ fontSize: 13, color: C.text, marginBottom: 16, maxWidth: 800 }}>
                    Define a new component in JSON. Grace (via Qwen) will cross-reference her internal Architecture Compass,
                    figure out the exact integration points needed, score the proposal, and then autonomously build it using the Hunter protocol.
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    <textarea
                        value={jsonSpec}
                        onChange={(e) => setJsonSpec(e.target.value)}
                        style={{
                            width: "100%",
                            height: 150,
                            padding: 12,
                            background: "#050510",
                            border: `1px solid ${C.border}`,
                            borderRadius: 8,
                            color: "#aae",
                            fontFamily: "monospace",
                            fontSize: 13,
                            resize: "vertical",
                            outline: "none"
                        }}
                    />
                    <div style={{ display: "flex", justifyContent: "flex-end" }}>
                        <button
                            onClick={handlePropose}
                            disabled={loading}
                            style={{
                                padding: "10px 24px",
                                background: loading ? C.muted : C.accent,
                                border: "none",
                                borderRadius: 8,
                                color: "#fff",
                                fontWeight: 700,
                                cursor: loading ? "not-allowed" : "pointer",
                            }}
                        >
                            {loading ? "Analyzing Architecture..." : "Propose"}
                        </button>
                    </div>
                </div>
            </div>

            <div style={{ flex: 1, overflow: "auto", padding: 24, background: C.bg }}>
                {error && (
                    <div style={{ padding: 12, background: "#2a1515", border: "1px solid #5a2525", borderRadius: 8, color: "#f88", marginBottom: 20 }}>
                        {error}
                    </div>
                )}

                {proposal && (
                    <div style={{
                        background: C.panel,
                        border: `1px solid ${C.border}`,
                        borderRadius: 12,
                        padding: 24,
                        opacity: buildStatus ? 0.92 : 1,
                        pointerEvents: buildStatus ? "none" : "auto"
                    }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
                            <div>
                                <h2 style={{ margin: "0 0 8px 0", color: "#fff" }}>Proposal: {proposal.spec?.name}</h2>
                                <div style={{ color: C.muted, fontSize: 14 }}>{proposal.proposal_id}</div>
                            </div>
                            <div style={{
                                background: `${needScoreColor(proposal.score)}22`,
                                border: `1px solid ${needScoreColor(proposal.score)}`,
                                padding: "8px 16px", borderRadius: 8, textAlign: "center"
                            }}>
                                <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase" }}>Need Score</div>
                                <div style={{ fontSize: 24, fontWeight: "bold", color: needScoreColor(proposal.score) }}>
                                    {typeof proposal.score === "number" ? proposal.score.toFixed(1) : proposal.score} / 10
                                </div>
                            </div>
                        </div>

                        <div style={{ marginBottom: 20 }}>
                            <div style={{ fontSize: 12, color: C.accent, textTransform: "uppercase", marginBottom: 8, fontWeight: "bold" }}>Value Proposition</div>
                            <div style={{ fontSize: 15, lineHeight: 1.6, color: "#eee" }}>{proposal.value}</div>
                        </div>

                        <div style={{ marginBottom: 30 }}>
                            <div style={{ fontSize: 12, color: C.accent, textTransform: "uppercase", marginBottom: 8, fontWeight: "bold" }}>Proposed Integration Points</div>
                            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                                {proposal.connections?.map((c, i) => (
                                    <div key={i} style={{ background: "#111", border: `1px solid ${C.border}`, padding: "6px 12px", borderRadius: 16, fontSize: 13, fontFamily: "monospace", color: "#8da" }}>
                                        {c}
                                    </div>
                                ))}
                                {!proposal.connections?.length && <div style={{ color: C.muted, fontSize: 13 }}>No existing components found to connect to.</div>}
                            </div>
                        </div >

                        <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 24, display: "flex", gap: 16, alignItems: "center" }}>
                            <button
                                onClick={handleBuild}
                                disabled={building || !!buildStatus}
                                style={{
                                    padding: "12px 32px",
                                    background: building ? C.muted : (buildStatus ? C.success : "#4caf50"),
                                    border: "none",
                                    borderRadius: 8,
                                    color: "#fff",
                                    fontWeight: 800,
                                    fontSize: 16,
                                    cursor: (building || buildStatus) ? "not-allowed" : "pointer",
                                    boxShadow: (building || buildStatus) ? "none" : "0 4px 12px rgba(76, 175, 80, 0.3)"
                                }}
                            >
                                {building ? "Assembling..." : (buildStatus ? "Handshake Sent" : "BUILD IT")}
                            </button>

                            <div style={{ fontSize: 13, color: C.muted }}>
                                {buildStatus ?
                                    <span style={{ color: C.success }}>Successfully handed over to HUNTER Assimilator ({buildStatus.request_id}). Watch the backend logs.</span>
                                    : "Clicking Build will trigger the autonomous coding agent to implement this."}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
