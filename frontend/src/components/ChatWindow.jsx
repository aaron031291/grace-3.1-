import { useState, useEffect, useRef } from "react";
import "./ChatWindow.css";

export default function ChatWindow({ chatId, folderPath, onChatCreated }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatInfo, setChatInfo] = useState(null);
  const [temperature, setTemperature] = useState(0.7);
  const [showTempControl, setShowTempControl] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (chatId) {
      fetchChatHistory();
      fetchChatInfo();
    } else {
      setMessages([]);
      setChatInfo(null);
    }
  }, [chatId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const toggleSourceExpanded = (messageId, sourceIdx) => {
    const key = `${messageId}-${sourceIdx}`;
    setExpandedSources((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const formatDate = (isoString) => {
    if (!isoString) return "Unknown";
    const date = new Date(isoString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const dateOnly = new Date(
      date.getFullYear(),
      date.getMonth(),
      date.getDate()
    );
    const todayOnly = new Date(
      today.getFullYear(),
      today.getMonth(),
      today.getDate()
    );
    const yesterdayOnly = new Date(
      yesterday.getFullYear(),
      yesterday.getMonth(),
      yesterday.getDate()
    );

    if (dateOnly.getTime() === todayOnly.getTime()) {
      return `Today at ${date.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      })}`;
    } else if (dateOnly.getTime() === yesterdayOnly.getTime()) {
      return `Yesterday at ${date.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      })}`;
    } else {
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    }
  };

  const fetchChatHistory = async () => {
    try {
      const response = await fetch(
        `http://localhost:8000/chats/${chatId}/messages`
      );
      const data = await response.json();
      setMessages(data.messages);
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
    }
  };

  const fetchChatInfo = async () => {
    try {
      const response = await fetch(`http://localhost:8000/chats/${chatId}`);
      const data = await response.json();
      setChatInfo(data);
      setTemperature(data.temperature || 0.7);
    } catch (error) {
      console.error("Failed to fetch chat info:", error);
    }
  };

  const updateTemperature = async (newTemp) => {
    setTemperature(newTemp);
    try {
      await fetch(`http://localhost:8000/chats/${chatId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ temperature: newTemp }),
      });
      setChatInfo((prev) => ({ ...prev, temperature: newTemp }));
    } catch (error) {
      console.error("Failed to update temperature:", error);
    }
  };

  const generateTitleFromContent = async (firstMessage) => {
    try {
      console.log("=== Starting title generation ===");
      console.log("Chat ID:", chatId);
      console.log("First message:", firstMessage);

      const response = await fetch(`http://localhost:8000/generate-title`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: firstMessage,
        }),
      });

      console.log("Title generation response status:", response.status);

      if (response.ok) {
        const result = await response.json();
        console.log("Full response from server:", result);

        // Extract and clean the title
        let generatedTitle = result.title || "";
        generatedTitle = generatedTitle.trim().replace(/^"|"$/g, "").trim(); // Remove quotes and extra whitespace

        if (!generatedTitle) {
          console.warn("Generated title is empty, skipping update");
          return;
        }

        console.log("Generated title from LLM:", generatedTitle);

        // Update chat with the generated title
        console.log("Updating chat with title:", generatedTitle);
        const updateResponse = await fetch(
          `http://localhost:8000/chats/${chatId}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: generatedTitle }),
          }
        );

        console.log("Update response status:", updateResponse.status);

        if (updateResponse.ok) {
          console.log("Chat title updated successfully");
          // Update local state immediately - this triggers re-render
          setChatInfo((prev) => {
            const updated = { ...prev, title: generatedTitle };
            console.log("Local state updated with title:", updated);
            return updated;
          });
          // Refresh the chat list in the parent component
          if (onChatCreated) {
            console.log("Calling onChatCreated to refresh chat list");
            onChatCreated();
          }
        } else {
          console.error("Failed to update title:", updateResponse.status);
          const errorText = await updateResponse.text();
          console.error("Error response:", errorText);
        }
      } else {
        console.error(
          "Failed to generate title, response status:",
          response.status
        );
        const errorText = await response.text();
        console.error("Error response:", errorText);
      }
    } catch (error) {
      console.error("Failed to generate title:", error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || !chatId || loading) return;

    const userMessage = input.trim();
    const isFirstMessage = messages.length === 0;
    const currentChatTitle = chatInfo?.title;
    setInput("");

    // Add user message immediately
    const newUserMessage = {
      id: Date.now(),
      role: "user",
      content: userMessage,
      tokens: null,
    };
    setMessages((prev) => [...prev, newUserMessage]);
    setLoading(true);

    try {
      // Send prompt and get response
      const response = await fetch(
        `http://localhost:8000/chats/${chatId}/prompt`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content: userMessage,
            temperature: chatInfo?.temperature || 0.7,
            top_p: 0.9,
            top_k: 40,
          }),
        }
      );

      // Handle 404 - Knowledge not found
      if (response.status === 404) {
        const errorData = await response.json();
        console.log("Knowledge not found (404):", errorData.detail);

        // Add assistant message about self-learning
        const assistantMessage = {
          id: Date.now() + Math.random(),
          role: "assistant",
          content:
            "🔄 Knowledge not found, triggering self-learning. Please upload relevant documents to the knowledge base so I can learn and answer your questions better.",
          tokens: null,
          sources: [],
          isSystemMessage: true, // Mark as system message
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setLoading(false);
        return; // Exit early
      }

      if (!response.ok) {
        // Try to get error details
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || "Failed to send message";
        throw new Error(errorMessage);
      }

      const result = await response.json();

      // Add assistant message with sources if available
      const assistantMessage = {
        id: result.assistant_message_id,
        role: "assistant",
        content: result.message,
        tokens: null,
        sources: result.sources || [], // Include sources from response
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Generate title if this is the first message and chat has no title or has default title
      if (
        isFirstMessage &&
        (currentChatTitle === "New Chat" || !currentChatTitle)
      ) {
        await generateTitleFromContent(userMessage);
      }
    } catch (error) {
      console.error("Failed to send message:", error);

      // Create a more informative error message
      let errorMessage = "Failed to send message. ";
      if (error.message.includes("Knowledge not found")) {
        errorMessage =
          "Knowledge not found. Please upload documents to the knowledge base.";
      } else if (error.message.includes("not running")) {
        errorMessage = "Ollama service is not running. Please start Ollama.";
      }

      // Add error message as assistant response
      const errorAssistantMessage = {
        id: Date.now() + Math.random(),
        role: "assistant",
        content: `❌ ${errorMessage}`,
        tokens: null,
        sources: [],
        isSystemMessage: true,
      };

      setMessages((prev) => [...prev, errorAssistantMessage]);

      // Remove the user message if the request failed
      setMessages((prev) => prev.filter((msg) => msg.id !== newUserMessage.id));
    } finally {
      setLoading(false);
    }
  };

  if (!chatId) {
    return (
      <div className="chat-window empty">
        <div className="empty-state">
          <svg
            width="64"
            height="64"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <h2>Select a chat or create a new one</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-window">
      <div className="chat-header">
        <div className="chat-header-top">
          <h2>{chatInfo?.title || "Chat"}</h2>
          {folderPath && (
            <span className="folder-context-badge">📁 {folderPath}</span>
          )}
        </div>
        {chatInfo && (
          <div className="chat-info">
            <span className="model-badge">{chatInfo.model}</span>
            <div className="temp-control">
              <button
                className="temp-badge"
                onClick={() => setShowTempControl(!showTempControl)}
                title="Click to adjust temperature"
              >
                Temp: {temperature.toFixed(1)}
              </button>
              {showTempControl && (
                <div className="temp-slider-container">
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={temperature}
                    onChange={(e) =>
                      updateTemperature(parseFloat(e.target.value))
                    }
                    className="temp-slider"
                  />
                  <span className="temp-value">{temperature.toFixed(2)}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="messages-container">
        {messages.length === 0 && (
          <div className="no-messages">
            <p>No messages yet. Start a conversation!</p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`message message-${msg.role}${
              msg.isSystemMessage ? " message-system" : ""
            }`}
          >
            <div className="message-avatar">
              {msg.role === "user" ? "👤" : msg.isSystemMessage ? "⚙️" : "🤖"}
            </div>
            <div className="message-content">
              <div className="message-role">{msg.role}</div>
              <div className="message-text">{msg.content}</div>
              {msg.tokens && (
                <div className="message-meta">Tokens: {msg.tokens}</div>
              )}
              {msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                  <button
                    className="sources-header-button"
                    onClick={() => toggleSourceExpanded(msg.id, -1)}
                  >
                    <span className="sources-toggle">
                      {expandedSources[`${msg.id}--1`] ? "▼" : "▶"}
                    </span>
                    <span className="sources-title">
                      📚 Sources ({msg.sources.length})
                    </span>
                  </button>
                  {expandedSources[`${msg.id}--1`] && (
                    <div className="sources-list">
                      {msg.sources.map((source, idx) => {
                        const isExpanded = expandedSources[`${msg.id}-${idx}`];
                        return (
                          <div key={idx} className="source-item">
                            <button
                              className="source-header-button"
                              onClick={() => toggleSourceExpanded(msg.id, idx)}
                            >
                              <span className="source-toggle">
                                {isExpanded ? "▼" : "▶"}
                              </span>
                              <span className="source-filename">
                                {source.filename}
                              </span>
                              {source.score && (
                                <span className="source-score">
                                  Relevancy score:{" "}
                                  {(source.score * 100).toFixed(0)}%
                                </span>
                              )}
                            </button>
                            {isExpanded && (
                              <div className="source-expanded-content">
                                <div className="source-metadata">
                                  <div className="metadata-row">
                                    <span className="metadata-label">
                                      Source:
                                    </span>
                                    <span className="metadata-value">
                                      {source.source || "Unknown"}
                                    </span>
                                  </div>
                                  {source.upload_method && (
                                    <div className="metadata-row">
                                      <span className="metadata-label">
                                        Added via:
                                      </span>
                                      <span className="metadata-value">
                                        {source.upload_method}
                                      </span>
                                    </div>
                                  )}
                                  {source.created_at && (
                                    <div className="metadata-row">
                                      <span className="metadata-label">
                                        Date:
                                      </span>
                                      <span className="metadata-value">
                                        {formatDate(source.created_at)}
                                      </span>
                                    </div>
                                  )}
                                  {source.trust_score !== undefined && (
                                    <div className="metadata-row">
                                      <span className="metadata-label">
                                        Confidence Score:
                                      </span>
                                      <span className="metadata-value confidence-badge">
                                        {(source.trust_score * 100).toFixed(0)}%
                                      </span>
                                    </div>
                                  )}
                                  {source.chunk_index !== undefined && (
                                    <div className="metadata-row">
                                      <span className="metadata-label">
                                        Chunk:
                                      </span>
                                      <span className="metadata-value">
                                        #{source.chunk_index}
                                      </span>
                                    </div>
                                  )}
                                </div>
                                <div className="source-text">{source.text}</div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message message-assistant loading-indicator">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="message-role">assistant</div>
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

      <form onSubmit={sendMessage} className="message-input-form">
        <div className="input-wrapper">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            disabled={loading}
            className="message-input"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="send-btn"
          >
            {loading ? (
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="spinner"
              >
                <circle cx="12" cy="12" r="1">
                  <animate
                    attributeName="r"
                    from="1"
                    to="8"
                    dur="1.2s"
                    repeatCount="indefinite"
                  />
                  <animate
                    attributeName="opacity"
                    from="1"
                    to="0"
                    dur="1.2s"
                    repeatCount="indefinite"
                  />
                </circle>
              </svg>
            ) : (
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
