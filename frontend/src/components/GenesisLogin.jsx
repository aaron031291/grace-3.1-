import { useState, useEffect } from "react";
import "./GenesisLogin.css";

export default function GenesisLogin({ onLogin }) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [genesisId, setGenesisId] = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null);

  const API_BASE = "http://localhost:8000";

  // Check if user already has Genesis ID on mount
  useEffect(() => {
    checkExistingSession();
  }, []);

  const checkExistingSession = async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/whoami`, {
        credentials: "include", // Include cookies
      });

      if (response.ok) {
        const data = await response.json();
        if (data.genesis_id) {
          setGenesisId(data.genesis_id);
          loadSessionInfo();
          if (onLogin) {
            onLogin(data.genesis_id);
          }
        }
      }
    } catch (err) {
      console.log("No existing session found");
    }
  };

  const loadSessionInfo = async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/session`, {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        setSessionInfo(data);
      }
    } catch (err) {
      console.error("Failed to load session info:", err);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include", // Include cookies
        body: JSON.stringify({
          username: username || undefined,
          email: email || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error("Login failed");
      }

      const data = await response.json();
      setGenesisId(data.genesis_id);

      // Load session info
      await loadSessionInfo();

      // Notify parent component
      if (onLogin) {
        onLogin(data.genesis_id);
      }

      // Show welcome message
      alert(data.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });

      setGenesisId(null);
      setSessionInfo(null);
      setUsername("");
      setEmail("");
    } catch (err) {
      console.error("Logout failed:", err);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  // If already logged in, show session info
  if (genesisId && sessionInfo) {
    return (
      <div className="genesis-session-info">
        <div className="session-header">
          <h3>🔑 Genesis Session Active</h3>
          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>

        <div className="session-details">
          <div className="detail-row">
            <span className="detail-label">Genesis ID:</span>
            <span className="detail-value genesis-id-display">
              {sessionInfo.genesis_id}
            </span>
          </div>

          <div className="detail-row">
            <span className="detail-label">Username:</span>
            <span className="detail-value">{sessionInfo.username}</span>
          </div>

          <div className="detail-row">
            <span className="detail-label">Session ID:</span>
            <span className="detail-value">{sessionInfo.session_id}</span>
          </div>

          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-value">{sessionInfo.total_actions}</div>
              <div className="stat-label">Actions</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{sessionInfo.total_errors}</div>
              <div className="stat-label">Errors</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{sessionInfo.total_fixes}</div>
              <div className="stat-label">Fixes</div>
            </div>
          </div>

          <div className="detail-row">
            <span className="detail-label">First Seen:</span>
            <span className="detail-value">
              {formatDate(sessionInfo.first_seen)}
            </span>
          </div>

          <div className="detail-row">
            <span className="detail-label">Last Seen:</span>
            <span className="detail-value">
              {formatDate(sessionInfo.last_seen)}
            </span>
          </div>

          <div className="tracking-notice">
            ✅ All your inputs and outputs are being tracked with Genesis Keys
            and auto-saved to knowledge_base/layer_1/genesis_key/{sessionInfo.genesis_id}/
          </div>
        </div>
      </div>
    );
  }

  // Login form
  return (
    <div className="genesis-login">
      <div className="login-header">
        <h2>🔑 Genesis Key Login</h2>
        <p className="subtitle">
          Get your unique Genesis ID to track all your activity
        </p>
      </div>

      <form onSubmit={handleLogin} className="login-form">
        <div className="form-group">
          <label htmlFor="username">Username (optional)</label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter a username or leave blank"
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="email">Email (optional)</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email or leave blank"
            disabled={loading}
          />
        </div>

        {error && <div className="error-message">{error}</div>}

        <button type="submit" className="login-button" disabled={loading}>
          {loading ? "Getting Genesis ID..." : "Get Genesis ID & Start Tracking"}
        </button>

        <div className="login-info">
          <p>
            <strong>What happens:</strong>
          </p>
          <ul>
            <li>You'll receive a unique Genesis ID (GU-prefix)</li>
            <li>All your inputs & outputs will be tracked</li>
            <li>Data auto-saves to knowledge_base/layer_1/genesis_key/</li>
            <li>Complete history from your first login</li>
            <li>Track: what, where, when, why, who, and how</li>
          </ul>
        </div>
      </form>
    </div>
  );
}
