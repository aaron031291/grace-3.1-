import { useState, useEffect, useRef } from "react";
import "./DirectoryChat.css";

export default function DirectoryChat({ currentPath = "" }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  const API_BASE = "http://localhost:8000";

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setError(null);

    // Add user message immediately
    const newUserMessage = {
      id: Date.now(),
      role: "user",
      content: userMessage,
    };
    setMessages((prev) => [...prev, newUserMessage]);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat/directory-prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: userMessage,
          directory_path: currentPath || "",
          temperature: 0.7,
          top_p: 0.9,
          top_k: 40,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage =
          errorData.detail || `Server error: ${response.status}`;

        // Handle 404 - Knowledge not found
        if (response.status === 404) {
          const assistantMessage = {
            id: Date.now() + Math.random(),
            role: "assistant",
            content:
              "📁 No documents found in this directory. Please upload some files to this folder first.",
          };
          setMessages((prev) => [...prev, assistantMessage]);
          setLoading(false);
          return;
        }

        throw new Error(errorMessage);
      }

      const result = await response.json();

      const assistantMessage = {
        id: result.message_id || Date.now() + Math.random(),
        role: "assistant",
        content: result.message,
        sources: result.sources || [],
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Failed to send message:", err);
      setError(err.message);

      const errorAssistantMessage = {
        id: Date.now() + Math.random(),
        role: "assistant",
        content: `❌ ${err.message}`,
      };

      setMessages((prev) => [...prev, errorAssistantMessage]);
    } finally {
      setLoading(false);
    }
  };

  const directoryLabel =
    currentPath && currentPath !== ""
      ? `📁 ${currentPath}`
      : "📁 Root Directory";

  return (
    <div className="directory-chat">
      <div className="directory-chat-header">
        <div className="directory-info">
          <span className="directory-label">{directoryLabel}</span>
          <span className="directory-hint">
            Chat about files in this directory only
          </span>
        </div>
      </div>

      <div className="directory-chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>Ask questions about documents in this directory</p>
            <p className="hint">
              The assistant will only use files from:{" "}
              <strong>{directoryLabel}</strong>
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`message ${
              msg.role === "user" ? "user-message" : "assistant-message"
            }`}
          >
            <div className="message-avatar">
              {msg.role === "user" ? "👤" : "🤖"}
            </div>
            <div className="message-content">
              <p>{msg.content}</p>
              {msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                  <span className="sources-label">Sources:</span>
                  <ul>
                    {msg.sources.map((source, idx) => (
                      <li key={idx}>{source.filename || source}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}

        {error && (
          <div className="error-banner">
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading && (
          <div className="message assistant-message loading">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="directory-chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about files in this directory..."
          disabled={loading}
          className="directory-chat-input"
        />
        <button
          type="submit"
          disabled={loading}
          className="directory-chat-send"
        >
          {loading ? "⏳" : "📤"}
        </button>
      </form>
    </div>
  );
}
