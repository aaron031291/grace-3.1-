import { useState, useEffect, useCallback, useRef } from "react";
import ChatList from "./ChatList";
import ChatWindow from "./ChatWindow";
import ConsensusChat from "./ConsensusChat";
import DevChat from "./DevChat";
import { API_BASE_URL } from "../config/api";
import "./ChatTab.css";

const STATUS_COLORS = {
  healthy: "#4caf50",
  operational: "#4caf50",
  degraded: "#ff9800",
  warning: "#ff9800",
  error: "#f44336",
  critical: "#f44336",
  offline: "#f44336",
  unknown: "#aaa",
};

function getStatusColor(status) {
  if (!status) return STATUS_COLORS.unknown;
  return STATUS_COLORS[status.toLowerCase()] || STATUS_COLORS.unknown;
}

function StatusDot({ status }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        backgroundColor: getStatusColor(status),
        marginRight: 8,
        flexShrink: 0,
      }}
    />
  );
}

function WorldModelPanel({ onClose }) {
  const [systemState, setSystemState] = useState(null);
  const [subsystems, setSubsystems] = useState([]);
  const [stateLoading, setStateLoading] = useState(true);
  const [stateError, setStateError] = useState(null);
  const [graceQuery, setGraceQuery] = useState("");
  const [graceMessages, setGraceMessages] = useState([]);
  const [graceSending, setGraceSending] = useState(false);
  const graceEndRef = useRef(null);
  const [fullData, setFullData] = useState(null);

  const fetchSystemState = useCallback(async () => {
    try {
      setStateLoading(true);
      setStateError(null);
      const [stateRes, subsystemsRes] = await Promise.allSettled([
        fetch(`${API_BASE_URL}/api/world-model/state`),
        fetch(`${API_BASE_URL}/api/world-model/subsystems`),
      ]);

      if (stateRes.status === "fulfilled" && stateRes.value.ok) {
        const data = await stateRes.value.json();
        setSystemState(data);
      } else {
        setStateError("Failed to load system state");
      }

      if (subsystemsRes.status === "fulfilled" && subsystemsRes.value.ok) {
        const data = await subsystemsRes.value.json();
        setSubsystems(data.subsystems || data || []);
      }
    } catch (err) {
      setStateError(err.message || "Network error");
    } finally {
      setStateLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSystemState();
    const interval = setInterval(fetchSystemState, 30000);
    return () => clearInterval(interval);
  }, [fetchSystemState]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/tabs/chat/full`).then(r => r.ok ? r.json() : null).then(setFullData).catch(() => {});
  }, []);

  useEffect(() => {
    graceEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [graceMessages]);

  const handleGraceSend = async (e) => {
    e.preventDefault();
    if (!graceQuery.trim() || graceSending) return;

    const query = graceQuery.trim();
    setGraceQuery("");
    setGraceMessages((prev) => [...prev, { role: "user", content: query }]);
    setGraceSending(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/world-model/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, include_system_state: true }),
      });

      if (!response.ok) throw new Error(`API error: ${response.status}`);
      const data = await response.json();
      setGraceMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response || data.message || data.answer || JSON.stringify(data),
        },
      ]);
    } catch (err) {
      setGraceMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err.message}`, isError: true },
      ]);
    } finally {
      setGraceSending(false);
    }
  };

  const overallStatus = systemState?.status || systemState?.health || "unknown";
  const kbStats = systemState?.knowledge_base || systemState?.kb_stats || null;
  const capabilities = systemState?.capabilities || systemState?.active_capabilities || [];

  return (
    <div style={styles.worldPanel}>
      <div style={styles.worldHeader}>
        <span style={styles.worldTitle}>World Model</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            onClick={fetchSystemState}
            style={styles.refreshBtn}
            title="Refresh"
            disabled={stateLoading}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{
                animation: stateLoading ? "spin 1s linear infinite" : "none",
              }}
            >
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
            </svg>
          </button>
          <button onClick={onClose} style={styles.closeBtn} title="Close panel">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      <div style={styles.worldBody}>
        {stateLoading && !systemState ? (
          <div style={styles.loadingBox}>Loading system state...</div>
        ) : stateError && !systemState ? (
          <div style={styles.errorBox}>
            <span>{stateError}</span>
            <button onClick={fetchSystemState} style={styles.retryBtn}>
              Retry
            </button>
          </div>
        ) : (
          <>
            {/* System Health */}
            <div style={styles.section}>
              <div style={styles.sectionHeader}>System Health</div>
              <div style={styles.healthRow}>
                <StatusDot status={overallStatus} />
                <span style={{ color: getStatusColor(overallStatus), fontWeight: 600, textTransform: "capitalize" }}>
                  {overallStatus}
                </span>
              </div>
              {systemState?.uptime && (
                <div style={styles.metaText}>Uptime: {systemState.uptime}</div>
              )}
              {systemState?.last_updated && (
                <div style={styles.metaText}>
                  Updated: {new Date(systemState.last_updated).toLocaleTimeString()}
                </div>
              )}
            </div>

            {/* Subsystems */}
            {subsystems.length > 0 && (
              <div style={styles.section}>
                <div style={styles.sectionHeader}>
                  Subsystems ({subsystems.length})
                </div>
                <div style={styles.subsystemList}>
                  {subsystems.map((sub, i) => (
                    <div key={sub.name || i} style={styles.subsystemItem}>
                      <StatusDot status={sub.status || sub.state} />
                      <span style={styles.subsystemName}>
                        {sub.name || sub.id || `Subsystem ${i + 1}`}
                      </span>
                      <span
                        style={{
                          ...styles.subsystemStatus,
                          color: getStatusColor(sub.status || sub.state),
                        }}
                      >
                        {sub.status || sub.state || "unknown"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Knowledge Base Stats */}
            {kbStats && (
              <div style={styles.section}>
                <div style={styles.sectionHeader}>Knowledge Base</div>
                <div style={styles.statsGrid}>
                  {Object.entries(kbStats).map(([key, value]) => (
                    <div key={key} style={styles.statItem}>
                      <span style={styles.statValue}>
                        {typeof value === "number" ? value.toLocaleString() : String(value)}
                      </span>
                      <span style={styles.statLabel}>
                        {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Source Code */}
            {systemState?.source_code && (
              <div style={styles.section}>
                <div style={styles.sectionHeader}>Source Code</div>
                <div style={styles.statsGrid}>
                  <div style={styles.statItem}>
                    <span style={styles.statValue}>{(systemState.source_code.total_python_files || 0).toLocaleString()}</span>
                    <span style={styles.statLabel}>Python Files</span>
                  </div>
                  <div style={styles.statItem}>
                    <span style={styles.statValue}>{(systemState.source_code.total_lines || 0).toLocaleString()}</span>
                    <span style={styles.statLabel}>Lines of Code</span>
                  </div>
                </div>
                {systemState.source_code.modules && (
                  <div style={{ marginTop: 8 }}>
                    {Object.entries(systemState.source_code.modules).slice(0, 8).map(([mod, count]) => (
                      <div key={mod} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '2px 0', color: '#aaa' }}>
                        <span>{mod}/</span>
                        <span style={{ color: '#eee' }}>{count} files</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Database */}
            {systemState?.database?.connected && (
              <div style={styles.section}>
                <div style={styles.sectionHeader}>Database ({systemState.database.table_count || 0} tables)</div>
                <div style={{ maxHeight: 120, overflowY: 'auto' }}>
                  {systemState.database.row_counts && Object.entries(systemState.database.row_counts).slice(0, 10).map(([table, count]) => (
                    <div key={table} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '2px 0', color: '#aaa' }}>
                      <span>{table}</span>
                      <span style={{ color: '#eee' }}>{count} rows</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Chats */}
            {systemState?.chats?.available && (
              <div style={styles.section}>
                <div style={styles.sectionHeader}>Chat History</div>
                <div style={styles.statsGrid}>
                  <div style={styles.statItem}>
                    <span style={styles.statValue}>{(systemState.chats.total_chats || 0).toLocaleString()}</span>
                    <span style={styles.statLabel}>Conversations</span>
                  </div>
                  <div style={styles.statItem}>
                    <span style={styles.statValue}>{(systemState.chats.total_messages || 0).toLocaleString()}</span>
                    <span style={styles.statLabel}>Messages</span>
                  </div>
                </div>
              </div>
            )}

            {/* APIs */}
            {systemState?.apis?.total_routes > 0 && (
              <div style={styles.section}>
                <div style={styles.sectionHeader}>APIs ({systemState.apis.total_routes} endpoints)</div>
                <div style={{ fontSize: 11, color: '#aaa' }}>All endpoints connected to world model</div>
              </div>
            )}

            {/* Capabilities */}
            {capabilities.length > 0 && (
              <div style={styles.section}>
                <div style={styles.sectionHeader}>Active Capabilities</div>
                <div style={styles.capList}>
                  {capabilities.map((cap, i) => (
                    <span key={i} style={styles.capBadge}>
                      {typeof cap === "string" ? cap : cap.name || cap.id}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Full aggregation: extra sections */}
            {fullData?.cognitive_decisions && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Cognitive Decisions</div>
                {typeof fullData.cognitive_decisions === 'object' ? (
                  Object.entries(fullData.cognitive_decisions).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.cognitive_decisions)}</span>
                )}
              </div>
            )}
            {fullData?.llm_status && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>LLM Status</div>
                {typeof fullData.llm_status === 'object' ? (
                  Object.entries(fullData.llm_status).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.llm_status)}</span>
                )}
              </div>
            )}
            {fullData?.mcp_tools && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>MCP Tools</div>
                {typeof fullData.mcp_tools === 'object' ? (
                  Object.entries(fullData.mcp_tools).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.mcp_tools)}</span>
                )}
              </div>
            )}
            {fullData?.voice_status && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Voice Status</div>
                {typeof fullData.voice_status === 'object' ? (
                  Object.entries(fullData.voice_status).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.voice_status)}</span>
                )}
              </div>
            )}
          </>
        )}

        {/* Ask Grace Mini-Chat */}
        <div style={styles.graceSection}>
          <div style={styles.sectionHeader}>Ask Grace</div>
          <div style={styles.graceMessages}>
            {graceMessages.length === 0 && (
              <div style={styles.graceEmpty}>
                Ask about system state, health, or capabilities...
              </div>
            )}
            {graceMessages.map((msg, i) => (
              <div
                key={i}
                style={{
                  ...styles.graceMsg,
                  alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                  backgroundColor:
                    msg.role === "user"
                      ? "#0f3460"
                      : msg.isError
                        ? "rgba(244,67,54,0.15)"
                        : "#1a1a2e",
                  borderColor: msg.isError ? "#f44336" : "transparent",
                }}
              >
                <span style={styles.graceMsgRole}>
                  {msg.role === "user" ? "You" : "Grace"}
                </span>
                <span style={styles.graceMsgContent}>{msg.content}</span>
              </div>
            ))}
            {graceSending && (
              <div style={{ ...styles.graceMsg, alignSelf: "flex-start", backgroundColor: "#1a1a2e" }}>
                <span style={styles.graceMsgRole}>Grace</span>
                <span style={{ ...styles.graceMsgContent, color: "#aaa" }}>
                  Thinking...
                </span>
              </div>
            )}
            <div ref={graceEndRef} />
          </div>
          <form onSubmit={handleGraceSend} style={styles.graceForm}>
            <input
              type="text"
              value={graceQuery}
              onChange={(e) => setGraceQuery(e.target.value)}
              placeholder="Ask about system state..."
              disabled={graceSending}
              style={styles.graceInput}
            />
            <button
              type="submit"
              disabled={graceSending || !graceQuery.trim()}
              style={{
                ...styles.graceSendBtn,
                opacity: graceSending || !graceQuery.trim() ? 0.4 : 1,
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function ChatTab() {
  const [chats, setChats] = useState([]);
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [selectedFolder, setSelectedFolder] = useState("");
  const [loading, setLoading] = useState(false);
  const [showWorldModel, setShowWorldModel] = useState(false);
  const [chatMode, setChatMode] = useState("general"); // general, consensus
  const [useKimi, setUseKimi] = useState(false);
  const [folderContext, setFolderContext] = useState("");
  const [availableFolders, setAvailableFolders] = useState([]);

  // Multi-model roundtable state
  const [modelToggles, setModelToggles] = useState({
    opus: false,
    kimi: false,
    qwen: false,
    reasoning: false,
  });
  const [availableModels, setAvailableModels] = useState([]);
  const [consensusMode, setConsensusMode] = useState(false);
  const [consensusResult, setConsensusResult] = useState(null);
  const [consensusRunning, setConsensusRunning] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/docs/by-folder`)
      .then(r => r.ok ? r.json() : { folders: [] })
      .then(d => setAvailableFolders((d.folders || []).map(f => f.folder)))
      .catch(() => {});
    fetch(`${API_BASE_URL}/api/consensus/models`)
      .then(r => r.ok ? r.json() : { models: [] })
      .then(d => setAvailableModels(d.models || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchChats();
  }, [selectedFolder]);

  const fetchChats = async () => {
    try {
      setLoading(true);
      const folderParam = selectedFolder
        ? `&folder_path=${encodeURIComponent(selectedFolder)}`
        : "";
      const response = await fetch(
        `${API_BASE_URL}/chats?limit=50${folderParam}`
      );
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      const data = await response.json();
      setChats(data?.chats || []);
      if (data?.chats?.length > 0 && !selectedChatId) {
        setSelectedChatId(data.chats[0].id);
      } else if (!data?.chats || data.chats.length === 0) {
        setSelectedChatId(null);
      }
    } catch (error) {
      console.error("Failed to fetch chats:", error);
      setChats([]);
      setSelectedChatId(null);
    } finally {
      setLoading(false);
    }
  };

  const createNewChat = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/chats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "New Chat",
          description: "New conversation",
          folder_path: selectedFolder,
        }),
      });
      const newChat = await response.json();
      setChats([newChat, ...chats]);
      setSelectedChatId(newChat.id);
    } catch (error) {
      console.error("Failed to create chat:", error);
    }
  };

  const deleteChat = async (chatId) => {
    try {
      await fetch(`${API_BASE_URL}/chats/${chatId}`, {
        method: "DELETE",
      });
      const updatedChats = chats.filter((c) => c.id !== chatId);
      setChats(updatedChats);
      if (selectedChatId === chatId) {
        setSelectedChatId(updatedChats.length > 0 ? updatedChats[0].id : null);
      }
    } catch (error) {
      console.error("Failed to delete chat:", error);
    }
  };

  const updateChatTitle = async (chatId, newTitle) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chats/${chatId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle }),
      });
      const updated = await response.json();
      setChats(chats.map((c) => (c.id === chatId ? updated : c)));
    } catch (error) {
      console.error("Failed to update chat:", error);
    }
  };

  return (
    <div className="chat-tab" style={{ position: "relative" }}>
      {/* Toolbar */}
      <div style={styles.toolbar}>
        <div style={styles.toolbarLeft}>
          {/* Model toggles */}
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {[
              { id: "opus", label: "Opus", icon: "🧠", color: "#9c27b0" },
              { id: "kimi", label: "Kimi", icon: "🌙", color: "#e94560" },
              { id: "qwen", label: "Qwen", icon: "⚡", color: "#2196f3" },
              { id: "reasoning", label: "Reason", icon: "🔮", color: "#ff9800" },
            ].map(m => {
              const isOn = modelToggles[m.id];
              const modelInfo = availableModels.find(am => am.id === m.id);
              const isAvail = modelInfo ? modelInfo.available : true;
              return (
                <button
                  key={m.id}
                  onClick={() => {
                    const newToggles = { ...modelToggles, [m.id]: !isOn };
                    setModelToggles(newToggles);
                    const activeCount = Object.values(newToggles).filter(Boolean).length;
                    setConsensusMode(activeCount >= 2);
                    if (m.id === "kimi") setUseKimi(!isOn);
                  }}
                  disabled={!isAvail}
                  title={`${m.label}${modelInfo ? ` — ${modelInfo.strengths?.join(", ")}` : ""}${!isAvail ? " (not configured)" : ""}`}
                  style={{
                    padding: "3px 8px",
                    border: `1px solid ${isOn ? m.color : "#444"}`,
                    borderRadius: 12,
                    background: isOn ? `${m.color}22` : "transparent",
                    color: isOn ? m.color : "#666",
                    fontSize: 11,
                    fontWeight: isOn ? 700 : 500,
                    cursor: isAvail ? "pointer" : "not-allowed",
                    opacity: isAvail ? 1 : 0.4,
                    display: "flex",
                    alignItems: "center",
                    gap: 3,
                    transition: "all .15s",
                  }}
                >
                  <span style={{ fontSize: 12 }}>{m.icon}</span>
                  {m.label}
                  <span style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: isOn ? m.color : "#444",
                    transition: "background .15s",
                  }} />
                </button>
              );
            })}
            {consensusMode && (
              <span style={{
                fontSize: 9, padding: "2px 6px", borderRadius: 3,
                background: "#4caf5022", color: "#4caf50", fontWeight: 700,
                border: "1px solid #4caf5044", marginLeft: 2,
              }}>ROUNDTABLE</span>
            )}
          </div>

          {/* Chat mode selector */}
          <div style={{ display: "flex", gap: 2, background: "#111", borderRadius: 6, padding: 2 }}>
            {[
              { id: "general", label: "💬 Chat" },
              { id: "consensus", label: "🤝 Consensus" },
              { id: "dev", label: "🛠️ Dev" },
            ].map(m => (
              <button key={m.id} onClick={() => setChatMode(m.id)} style={{
                padding: "4px 10px", border: "none", borderRadius: 4, cursor: "pointer",
                fontSize: 11, fontWeight: chatMode === m.id ? 700 : 500,
                background: chatMode === m.id ? "#e94560" : "transparent",
                color: chatMode === m.id ? "#fff" : "#888",
              }}>{m.label}</button>
            ))}
          </div>

          {/* Folder context selector */}
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 12, color: "#888" }}>📁</span>
            <select
              value={folderContext}
              onChange={e => setFolderContext(e.target.value)}
              style={{
                padding: "4px 8px", fontSize: 12, background: "#1a1a2e",
                color: folderContext ? "#e94560" : "#888",
                border: "1px solid #333", borderRadius: 4, outline: "none",
                maxWidth: 160,
              }}
            >
              <option value="">All folders</option>
              {availableFolders.map(f => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
            {folderContext && (
              <span
                onClick={() => setFolderContext("")}
                style={{ cursor: "pointer", fontSize: 14, color: "#888" }}
                title="Clear folder context"
              >✕</span>
            )}
          </div>
        </div>
        <button
          onClick={() => setShowWorldModel(!showWorldModel)}
          style={{
            ...styles.worldToggleBtn,
            backgroundColor: showWorldModel ? "#0f3460" : "transparent",
            borderColor: showWorldModel ? "#e94560" : "#444",
          }}
          title={showWorldModel ? "Hide World Model" : "Show World Model"}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
          </svg>
          <span style={{ fontSize: 13 }}>World Model</span>
        </button>
      </div>

      {/* Main content area */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {chatMode === "consensus" ? (
          <div style={{ flex: showWorldModel ? "1 1 70%" : "1 1 100%", overflow: "hidden" }}>
            <ConsensusChat />
          </div>
        ) : chatMode === "dev" ? (
          <div style={{ flex: showWorldModel ? "1 1 70%" : "1 1 100%", overflow: "hidden" }}>
            <DevChat />
          </div>
        ) : (
          <div
            style={{
              flex: showWorldModel ? "1 1 70%" : "1 1 100%",
              display: "flex",
              overflow: "hidden",
              transition: "flex 0.2s ease",
            }}
          >
            <ChatList
              chats={chats}
              selectedChatId={selectedChatId}
              selectedFolder={selectedFolder}
              onSelectChat={setSelectedChatId}
              onSelectFolder={setSelectedFolder}
              onCreateChat={createNewChat}
              onDeleteChat={deleteChat}
              onUpdateTitle={updateChatTitle}
              loading={loading}
            />
            <ChatWindow
              chatId={selectedChatId}
              folderPath={
                chats.find((c) => c.id === selectedChatId)?.folder_path ||
                selectedFolder
              }
              onChatCreated={fetchChats}
            />
          </div>
        )}

        {showWorldModel && (
          <WorldModelPanel onClose={() => setShowWorldModel(false)} />
        )}
      </div>
    </div>
  );
}

const styles = {
  toolbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "6px 12px",
    backgroundColor: "#12122a",
    borderBottom: "1px solid #262640",
    flexShrink: 0,
  },
  toolbarLeft: {
    display: "flex",
    alignItems: "center",
    gap: 16,
  },
  kimiToggle: {
    display: "flex",
    alignItems: "center",
  },
  toggleLabel: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    cursor: "pointer",
    userSelect: "none",
  },
  toggleCheckbox: {
    display: "none",
  },
  toggleTrack: {
    display: "inline-flex",
    alignItems: "center",
    width: 36,
    height: 18,
    borderRadius: 9,
    transition: "background-color 0.2s",
    position: "relative",
    flexShrink: 0,
  },
  toggleThumb: {
    display: "block",
    width: 14,
    height: 14,
    borderRadius: "50%",
    backgroundColor: "#eee",
    transition: "transform 0.2s",
    boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
  },
  worldToggleBtn: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "5px 12px",
    border: "1px solid",
    borderRadius: 6,
    backgroundColor: "transparent",
    color: "#eee",
    cursor: "pointer",
    fontSize: 13,
    transition: "all 0.2s",
  },
  worldPanel: {
    flex: "0 0 30%",
    minWidth: 280,
    maxWidth: 420,
    borderLeft: "1px solid #262640",
    display: "flex",
    flexDirection: "column",
    backgroundColor: "#16213e",
    overflow: "hidden",
  },
  worldHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 14px",
    borderBottom: "1px solid #262640",
    backgroundColor: "#0f1a30",
    flexShrink: 0,
  },
  worldTitle: {
    fontSize: 15,
    fontWeight: 700,
    color: "#eee",
    letterSpacing: 0.5,
  },
  closeBtn: {
    background: "none",
    border: "none",
    color: "#aaa",
    cursor: "pointer",
    padding: 4,
    borderRadius: 4,
    display: "flex",
    alignItems: "center",
  },
  refreshBtn: {
    background: "none",
    border: "none",
    color: "#aaa",
    cursor: "pointer",
    padding: 4,
    borderRadius: 4,
    display: "flex",
    alignItems: "center",
  },
  worldBody: {
    flex: 1,
    overflowY: "auto",
    padding: "0 0 8px 0",
  },
  loadingBox: {
    padding: 24,
    textAlign: "center",
    color: "#aaa",
    fontSize: 13,
  },
  errorBox: {
    padding: 20,
    textAlign: "center",
    color: "#f44336",
    fontSize: 13,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 10,
  },
  retryBtn: {
    padding: "4px 14px",
    borderRadius: 4,
    border: "1px solid #f44336",
    backgroundColor: "transparent",
    color: "#f44336",
    cursor: "pointer",
    fontSize: 12,
  },
  section: {
    padding: "12px 14px",
    borderBottom: "1px solid #1a2744",
  },
  sectionHeader: {
    fontSize: 12,
    fontWeight: 600,
    color: "#aaa",
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  healthRow: {
    display: "flex",
    alignItems: "center",
    gap: 4,
  },
  metaText: {
    fontSize: 11,
    color: "#777",
    marginTop: 4,
  },
  subsystemList: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  subsystemItem: {
    display: "flex",
    alignItems: "center",
    padding: "5px 8px",
    borderRadius: 4,
    backgroundColor: "rgba(255,255,255,0.03)",
    fontSize: 13,
  },
  subsystemName: {
    flex: 1,
    color: "#ddd",
  },
  subsystemStatus: {
    fontSize: 11,
    textTransform: "capitalize",
    fontWeight: 500,
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 8,
  },
  statItem: {
    display: "flex",
    flexDirection: "column",
    padding: "8px 10px",
    borderRadius: 6,
    backgroundColor: "rgba(255,255,255,0.04)",
    textAlign: "center",
  },
  statValue: {
    fontSize: 18,
    fontWeight: 700,
    color: "#eee",
  },
  statLabel: {
    fontSize: 10,
    color: "#888",
    marginTop: 2,
    textTransform: "capitalize",
  },
  capList: {
    display: "flex",
    flexWrap: "wrap",
    gap: 6,
  },
  capBadge: {
    display: "inline-block",
    padding: "3px 10px",
    borderRadius: 12,
    backgroundColor: "rgba(15,52,96,0.6)",
    border: "1px solid #1a3a5c",
    color: "#8ab4f8",
    fontSize: 11,
    fontWeight: 500,
  },
  graceSection: {
    display: "flex",
    flexDirection: "column",
    padding: "12px 14px 8px",
    flex: 1,
    minHeight: 180,
  },
  graceMessages: {
    flex: 1,
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: 6,
    marginBottom: 8,
    minHeight: 80,
    maxHeight: 260,
    padding: "4px 0",
  },
  graceEmpty: {
    fontSize: 12,
    color: "#666",
    textAlign: "center",
    padding: "16px 8px",
    fontStyle: "italic",
  },
  graceMsg: {
    padding: "6px 10px",
    borderRadius: 8,
    maxWidth: "90%",
    fontSize: 12,
    lineHeight: 1.45,
    border: "1px solid transparent",
  },
  graceMsgRole: {
    display: "block",
    fontSize: 10,
    fontWeight: 600,
    color: "#888",
    marginBottom: 2,
    textTransform: "uppercase",
  },
  graceMsgContent: {
    color: "#ddd",
    wordBreak: "break-word",
    whiteSpace: "pre-wrap",
  },
  graceForm: {
    display: "flex",
    gap: 6,
  },
  graceInput: {
    flex: 1,
    padding: "7px 10px",
    borderRadius: 6,
    border: "1px solid #333",
    backgroundColor: "#1a1a2e",
    color: "#eee",
    fontSize: 12,
    outline: "none",
  },
  graceSendBtn: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "6px 10px",
    borderRadius: 6,
    border: "1px solid #0f3460",
    backgroundColor: "#0f3460",
    color: "#eee",
    cursor: "pointer",
    transition: "opacity 0.2s",
  },
};
