import React, { useState, useEffect, useRef } from "react";
import { API_BASE_URL } from "../config/api";

export default function SpindleHitlChat() {
  const [activeHandoffs, setActiveHandoffs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedHandoffId, setSelectedHandoffId] = useState(null);
  
  // Chat state
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchActiveHandoffs();
    const interval = setInterval(fetchActiveHandoffs, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, activeHandoffs]);

  const fetchActiveHandoffs = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/spindle/hitl/active`);
      if (res.ok) {
        const data = await res.json();
        setActiveHandoffs(data.handoffs || []);
      }
    } catch (err) {
      console.error("Failed to fetch Spindle active handoffs", err);
    } finally {
      setLoading(false);
    }
  };

  const selectedHandoff = activeHandoffs.find(h => h.handoff_id === selectedHandoffId);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || chatLoading) return;
    
    const text = inputText.trim();
    setInputText("");
    
    setMessages(prev => [...prev, { role: "operator", text }]);
    
    // Command parser
    if (text.startsWith("!resolve ")) {
      const decision = text.replace("!resolve ", "").trim();
      await handleResolve(decision);
      return;
    }

    // Normal chat to Grace/Spindle regarding the issue
    setChatLoading(true);
    try {
      // Append context about the active handoff if one is selected
      let queryContext = "";
      if (selectedHandoff) {
         queryContext = `[Context: Active Handoff ID ${selectedHandoff.handoff_id}, Signal: ${selectedHandoff.signal}. The operator asks:] `;
      }
      
      const res = await fetch(`${API_BASE_URL}/api/world-model/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryContext + text, include_system_state: true })
      });
      
      if (!res.ok) throw new Error("API Error");
      const data = await res.json();
      
      setMessages(prev => [...prev, { 
        role: "grace", 
        text: data.response || data.message || data.answer || JSON.stringify(data)
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "grace", isError: true, text: `API Error: ${err.message}` }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleResolve = async (decision) => {
    if (!selectedHandoffId) {
      setMessages(prev => [...prev, { role: "system", isError: true, text: "No handoff selected to resolve." }]);
      return;
    }
    
    setChatLoading(true);
    setMessages(prev => [...prev, { role: "system", text: `Triggering !resolve for ${selectedHandoffId}...` }]);
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/spindle/hitl/${selectedHandoffId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, notes: "Resolved via SpindleHitlChat UI" })
      });
      
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      
      setMessages(prev => [...prev, { role: "system", text: `Success: ${data.message}` }]);
      setSelectedHandoffId(null);
      fetchActiveHandoffs();
      
    } catch (err) {
      setMessages(prev => [...prev, { role: "system", isError: true, text: `Failed to resolve: ${err.message}` }]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%",
      backgroundColor: "#161622", color: "#ddd", fontFamily: "-apple-system, sans-serif"
    }}>
      {/* Header */}
      <div style={{
        padding: "8px 12px", background: "#1a1a2e", borderBottom: "1px solid #333",
        display: "flex", justifyContent: "space-between", alignItems: "center"
      }}>
        <div style={{ fontSize: 13, fontWeight: "bold", color: "#e94560", display: "flex", alignItems: "center", gap: 6 }}>
          <span>🛡️</span> Spindle Operations
        </div>
        <div style={{ fontSize: 11, color: activeHandoffs.length > 0 ? "#ff9800" : "#4caf50" }}>
          {loading ? "Syncing..." : `${activeHandoffs.length} Active Handoffs`}
        </div>
      </div>

      {/* Handoff List */}
      {activeHandoffs.length > 0 && (
        <div style={{ maxHeight: "35%", overflowY: "auto", borderBottom: "1px solid #262640", background: "#0f0f1a" }}>
          {activeHandoffs.map(h => (
            <div
              key={h.handoff_id}
              onClick={() => setSelectedHandoffId(h.handoff_id)}
              style={{
                padding: "8px 12px", borderBottom: "1px solid #222", cursor: "pointer",
                background: selectedHandoffId === h.handoff_id ? "#262640" : "transparent",
                transition: "background 0.2s"
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <strong style={{ fontSize: 12, color: "#e94560" }}>{h.signal || "UNKNOWN_SIGNAL"}</strong>
                <span style={{ fontSize: 10, color: "#888" }}>{new Date(h.received_at).toLocaleTimeString()}</span>
              </div>
              <div style={{ fontSize: 11, color: "#aaa" }}>
                 Trust Score: <span style={{ color: "#fff", fontWeight: "bold" }}>{h.trust_score !== undefined ? h.trust_score.toFixed(2) : "N/A"}</span>
              </div>
              {h.failed_layers && h.failed_layers.length > 0 && (
                <div style={{ fontSize: 11, color: "#ff9800", marginTop: 4 }}>
                  Failed: {h.failed_layers.join(", ")}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Chat Area */}
      <div style={{ flex: 1, overflowY: "auto", padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
        {messages.length === 0 && (
          <div style={{ textAlign: "center", color: "#666", fontSize: 12, marginTop: 20 }}>
            {activeHandoffs.length > 0
              ? "Select an issue and talk to Grace or use !resolve"
              : "No active Spindle handoffs. System is healthy."}
          </div>
        )}
        
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === "operator" ? "flex-end" : "flex-start",
            maxWidth: "85%",
            padding: "8px 12px",
            borderRadius: 8,
            fontSize: 12,
            lineHeight: 1.4,
            backgroundColor: m.role === "operator" ? "#0f3460" : m.role === "system" ? "#1a1a2e" : "#533483",
            color: m.isError ? "#ff5555" : "#eee",
            border: m.isError ? "1px solid #ff5555" : "1px solid transparent",
            wordBreak: "break-word"
          }}>
             <div style={{ fontSize: 10, color: "#aaa", marginBottom: 4, fontWeight: "bold" }}>
               {m.role === "operator" ? "Operator" : m.role === "grace" ? "Grace" : "System"}
             </div>
             <div>{m.text}</div>
          </div>
        ))}
        {chatLoading && (
          <div style={{ alignSelf: "flex-start", padding: "8px 12px", borderRadius: 8, backgroundColor: "#533483", fontSize: 12, color: "#ccc" }}>
             Grace is analyzing...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div style={{ padding: 10, borderTop: "1px solid #333", background: "#1a1a2e" }}>
         <form onSubmit={handleSendMessage} style={{ display: "flex", gap: 8 }}>
           <input
             type="text"
             value={inputText}
             onChange={e => setInputText(e.target.value)}
             disabled={chatLoading}
             placeholder={selectedHandoffId ? "Talk to Grace or !resolve <decision>" : "Waiting for issues..."}
             style={{
               flex: 1, padding: "8px 12px", borderRadius: 20, border: "1px solid #444",
               background: "#111", color: "#fff", fontSize: 13, outline: "none"
             }}
           />
           <button
             type="submit"
             disabled={chatLoading || !inputText.trim()}
             style={{
               background: "#e94560", color: "#fff", border: "none", borderRadius: "50%",
               width: 36, height: 36, display: "flex", alignItems: "center", justifyContent: "center",
               cursor: (chatLoading || !inputText.trim()) ? "not-allowed" : "pointer",
               opacity: (chatLoading || !inputText.trim()) ? 0.5 : 1
             }}
           >
             <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
               <line x1="22" y1="2" x2="11" y2="13" />
               <polygon points="22 2 15 22 11 13 2 9 22 2" />
             </svg>
           </button>
         </form>
         <div style={{ fontSize: 10, color: "#666", marginTop: 6, textAlign: "center" }}>
           Use <strong style={{ color: "#aaa" }}>!resolve</strong> to ingest procedural memory fix
         </div>
      </div>
    </div>
  );
}
