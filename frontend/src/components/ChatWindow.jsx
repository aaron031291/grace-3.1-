import { useState, useEffect, useRef, useCallback } from "react";
import "./ChatWindow.css";
import VoiceButton from "./VoiceButton";
import SearchInternetButton from "./SearchInternetButton";
import { API_BASE_URL, API_V2 } from '../config/api';

export default function ChatWindow({ chatId, folderPath, onChatCreated }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatInfo, setChatInfo] = useState(null);
  const [temperature, setTemperature] = useState(0.7);
  const [showTempControl, setShowTempControl] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});
  const [lastAssistantMessage, setLastAssistantMessage] = useState("");
  const [showSearchInternet, setShowSearchInternet] = useState(false);
  const [lastQuery, setLastQuery] = useState("");
  const [useAgent, setUseAgent] = useState(false);
  const messagesEndRef = useRef(null);

  const fetchChatHistory = useCallback(async () => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/chats/${chatId}/messages`
      );
      const data = await response.json();
      setMessages(data.messages);
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
    }
  }, [chatId]);

  const fetchChatInfo = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/chats/${chatId}`);
      const data = await response.json();
      setChatInfo(data);
      setTemperature(data.temperature || 0.7);
    } catch (error) {
      console.error("Failed to fetch chat info:", error);
    }
  }, [chatId]);

  useEffect(() => {
    if (chatId) {
      fetchChatHistory();
      fetchChatInfo();
    } else {
      setMessages([]);
      setChatInfo(null);
    }
  }, [chatId, fetchChatHistory, fetchChatInfo]);

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

  // Handle voice transcript - populate input and optionally auto-submit
  const handleVoiceTranscript = (transcript) => {
    setInput(transcript);
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

  // Original fetchChatHistory and fetchChatInfo removed since we hoisted them up to replace the original hook

  const updateTemperature = async (newTemp) => {
    setTemperature(newTemp);
    try {
      await fetch(`${API_BASE_URL}/chats/${chatId}`, {
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

      const response = await fetch(`${API_BASE_URL}/generate-title`, {
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
          `${API_BASE_URL}/chats/${chatId}`,
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

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || !chatId || loading) return;

    const userMessage = input.trim();
    setInput("");
    setLoading(true);
    // Reset search internet button state for new query
    setShowSearchInternet(false);

    const isFirstMessage = messages.length === 0;
    const currentChatTitle = chatInfo?.title;

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
      // Brain-first: use /api/v2/chat/send (RAG + unified memory) when not in agent mode
      const endpoint = useAgent
        ? `${API_BASE_URL}/api/mcp/chat`
        : API_V2.chat("send");
      const payload = useAgent ? {
        chat_id: chatId,
        messages: [{ role: "user", content: userMessage }],
        use_rag: true,
        use_web: true,
        stream: true,
        model: chatInfo?.model,
        temperature: chatInfo?.temperature || 0.7
      } : {
        chat_id: chatId,
        message: userMessage,
        use_rag: true,
      };

      // Send prompt and get response
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      // Handle 404 - Knowledge not found
      if (response.status === 404) {
        const errorData = await response.json();
        console.log("Knowledge not found (404):", errorData.detail);

        // Context-aware message based on whether this is a folder-scoped chat
        let notFoundMessage;
        if (folderPath) {
          notFoundMessage = `No relevant information found in folder "${folderPath.split(/[/\\]/).pop()}". You can search the internet to add knowledge to this folder, or switch to a General Chat.`;
          // Allow search button for folder chats so users can populate them!
          setShowSearchInternet(true);
        } else {
          notFoundMessage = "I don't have any information about that in my knowledge base yet.";
          // Show search internet button for general chats
          setShowSearchInternet(true);
        }
        setLastQuery(userMessage);

        // Add assistant message about scope limitation
        const assistantMessage = {
          id: Date.now() + Math.random(),
          role: "assistant",
          content: notFoundMessage,
          tokens: null,
          sources: [],
          isSystemMessage: true, // Mark as system message
          showSearchButton: true, // Show button for all chats now that we have folder scoping
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

      let finalAssistantMessage = "";

      if (useAgent && payload.stream) {
        // Read SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let done = false;

        const tempAssistantId = Date.now() + Math.random();
        setMessages((prev) => [
          ...prev,
          {
            id: tempAssistantId,
            role: "assistant",
            content: "",
            tokens: null,
            sources: [],
            tool_calls: [],
            is_streaming: true,
          }
        ]);

        let assistantContent = "";
        let toolCalls = [];
        let sources = [];
        let accumulatedText = "";

        while (!done) {
          const { value, done: readerDone } = await reader.read();
          done = readerDone;
          if (value) {
            const rawChunk = decoder.decode(value, { stream: true });
            accumulatedText += rawChunk;

            const lines = accumulatedText.split(/\r?\n/);
            accumulatedText = lines.pop(); // keep incomplete line

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const dataStr = line.slice(6);

                if (dataStr === '[DONE]') {
                  done = true;
                  break;
                }

                try {
                  const data = JSON.parse(dataStr);

                  if (data.type === 'tool_call') {
                    toolCalls = [...toolCalls, { tool: data.name, arguments: data.args, success: null, duration_ms: null, result_preview: null }];
                  } else if (data.type === 'tool_result') {
                    // Find last tool call with this name that hasn't finished
                    let foundIdx = -1;
                    for (let i = toolCalls.length - 1; i >= 0; i--) {
                      if (toolCalls[i].tool === data.name && toolCalls[i].success === null) {
                        foundIdx = i;
                        break;
                      }
                    }

                    if (foundIdx !== -1) {
                      const updated = [...toolCalls];
                      updated[foundIdx] = { ...updated[foundIdx], success: data.success, duration_ms: data.duration_ms, result_preview: data.result_preview };
                      toolCalls = updated;
                    }
                  } else if (data.type === 'content') {
                    assistantContent = data.content;
                    sources = data.sources || [];
                  } else if (data.type === 'error') {
                    assistantContent += `\\n❌ Error: ${data.error}`;
                  }

                  // Update UI dynamically
                  setMessages(prev => prev.map(msg =>
                    msg.id === tempAssistantId
                      ? { ...msg, content: assistantContent, tool_calls: toolCalls, sources: sources }
                      : msg
                  ));
                } catch { /* intentionally empty */ }
              }
            }
          }
        }

        // Final cleanup of streaming states
        setMessages(prev => prev.map(msg =>
          msg.id === tempAssistantId
            ? { ...msg, is_streaming: false }
            : msg
        ));
        finalAssistantMessage = assistantContent;

      } else {
        // Standard JSON response (brain v2 returns { ok, data }; legacy /chats/{id}/prompt returns flat)
        const res = await response.json();
        const result = res?.ok && res?.data ? res.data : res;

        const assistantMessage = {
          id: result.assistant_message_id || Date.now() + Math.random(),
          role: "assistant",
          content: result.message || result.content,
          tokens: result.tokens_used || null,
          sources: result.sources || [],
          tool_calls: result.tool_calls_made || [],
        };

        setMessages((prev) => [...prev, assistantMessage]);
        finalAssistantMessage = assistantMessage.content;
      }

      setLastAssistantMessage(finalAssistantMessage); // Track for TTS

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
          {folderPath ? (
            <span className="folder-context-badge" title="This chat is scoped to this folder's learning memory only">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
              </svg>
              <span className="folder-scope-label">Scoped:</span>
              <span className="folder-scope-path">{folderPath.split(/[/\\]/).pop()}</span>
            </span>
          ) : (
            <span className="general-context-badge" title="Full access to world model and all knowledge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
              </svg>
              <span>General</span>
            </span>
          )}
          <div className="agent-toggle-container">
            <label className="switch">
              <input
                type="checkbox"
                checked={useAgent}
                onChange={(e) => setUseAgent(e.target.checked)}
              />
              <span className="slider round"></span>
            </label>
            <span className={`agent-toggle-label ${useAgent ? 'active' : ''}`}>
              {useAgent ? "Agent Mode ON" : "Agent Mode OFF"}
            </span>
          </div>
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
            className={`message message-${msg.role}${msg.isSystemMessage ? " message-system" : ""
              }`}
          >
            <div className="message-avatar">
              {msg.role === "user" ? "👤" : msg.isSystemMessage ? "⚙️" : "🤖"}
            </div>
            <div className="message-content">
              <div className="message-role">{msg.role}</div>
              {msg.content ? (
                <div className="message-text">
                  {msg.content}
                  {msg.role === 'assistant' && !msg.isSystemMessage && (
                    <div style={{ display: 'flex', gap: 6, marginTop: 6, alignItems: 'center' }}>
                      <button onClick={() => {
                        try {
                          fetch(`${API_BASE_URL}/api/oracle/feedback`, {
                            method: 'POST', headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({prompt: messages[messages.indexOf(msg)-1]?.content || '', output: msg.content, outcome: 'positive'}),
                          });
                        } catch {}
                        msg._feedback = 'up';
                      }} title="Good response" style={{
                        background: 'none', border: 'none', cursor: 'pointer', fontSize: 14,
                        opacity: msg._feedback === 'up' ? 1 : 0.4,
                      }}>👍</button>
                      <button onClick={() => {
                        try {
                          fetch(`${API_BASE_URL}/api/oracle/feedback`, {
                            method: 'POST', headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({prompt: messages[messages.indexOf(msg)-1]?.content || '', output: msg.content, outcome: 'negative'}),
                          });
                        } catch {}
                        msg._feedback = 'down';
                      }} title="Bad response" style={{
                        background: 'none', border: 'none', cursor: 'pointer', fontSize: 14,
                        opacity: msg._feedback === 'down' ? 1 : 0.4,
                      }}>👎</button>
                    </div>
                  )}
                </div>
              ) : msg.is_streaming && (!msg.tool_calls || msg.tool_calls.length === 0) ? (
                <div className="loading-text" style={{ marginTop: '0.5rem' }}>
                  Starting agent workflow...
                </div>
              ) : null}
              {msg.tool_calls && msg.tool_calls.length > 0 && (
                <div className="message-tool-calls">
                  {msg.tool_calls.map((tc, idx) => {
                    let statusClass = "running";
                    let icon = (
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="spinner">
                        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                      </svg>
                    );
                    if (tc.success === true) {
                      statusClass = "success";
                      icon = "✅";
                    } else if (tc.success === false) {
                      statusClass = "failed";
                      icon = "❌";
                    }
                    return (
                      <div key={idx} className={`tool-call-pill ${statusClass}`} title={tc.result_preview}>
                        <span className="tool-icon">{icon}</span>
                        <span className="tool-name">{tc.tool}</span>
                        {tc.duration_ms && <span className="tool-duration">{Math.round(tc.duration_ms)}ms</span>}
                      </div>
                    );
                  })}
                </div>
              )}
              {msg.tokens && (
                <div className="message-meta">Tokens: {msg.tokens}</div>
              )}
              {msg.showSearchButton && showSearchInternet && (
                <SearchInternetButton
                  query={lastQuery}
                  folderPath={folderPath}
                  chatId={chatId}
                  onSearchComplete={() => {
                    setShowSearchInternet(false);
                  }}
                />
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
                                {source.source || source.filename || "Unknown Source"}
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
        {loading && !messages.some(msg => msg.is_streaming) && (
          <div className="message message-assistant loading-indicator">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="message-role">assistant</div>
              <div className="loading-text">
                {useAgent ? "Agent is coordinating tools..." : "Generating response..."}
              </div>
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

      <form onSubmit={handleSendMessage} className="message-input-form">
        <div className="input-wrapper">
          <VoiceButton
            onTranscript={handleVoiceTranscript}
            speakText={lastAssistantMessage}
            disabled={loading}
            size="medium"
            showTTSButton={true}
          />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type or speak a message..."
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
