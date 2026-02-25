import { useState, useRef, useEffect, useCallback } from "react";
import "./PersistentVoicePanel.css";

/**
 * PersistentVoicePanel Component
 *
 * A floating voice control panel for continuous conversation with GRACE.
 * Features:
 * - Persistent ON/OFF toggle
 * - Continuous voice recognition
 * - Auto TTS for responses
 * - Voice activity indicator
 * - Conversation history
 * - Settings panel
 */
export default function PersistentVoicePanel({
  onSendMessage,
  lastResponse,
  isProcessing = false,
}) {
  // Voice states
  const [isEnabled, setIsEnabled] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Transcript and conversation
  const [currentTranscript, setCurrentTranscript] = useState("");
  const [conversationLog, setConversationLog] = useState([]);

  // Settings
  const [settings, setSettings] = useState({
    voice: "en-US-AriaNeural",
    autoSpeak: false,  // Changed from true - only speak when explicitly enabled
    continuousListen: true,
    wakeWord: "grace",
    useWakeWord: false,
    speechRate: "+0%",
  });

  // Refs
  const recognitionRef = useRef(null);
  const audioRef = useRef(null);
  const _wsRef = useRef(null);

  // Available voices
  const [availableVoices, setAvailableVoices] = useState([]);

  // Fetch available voices
  useEffect(() => {
    fetchVoices();
  }, []);

  const fetchVoices = async () => {
    try {
      const response = await fetch("http://localhost:8000/voice/voices?locale=en-US");
      if (response.ok) {
        const data = await response.json();
        setAvailableVoices(data.voices || []);
      }
    } catch (err) {
      console.error("Failed to fetch voices:", err);
    }
  };

  // Initialize speech recognition
  const initRecognition = useCallback(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.error("Speech recognition not supported");
      return null;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = settings.continuousListen;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      setCurrentTranscript(interimTranscript || finalTranscript);

      if (finalTranscript) {
        handleFinalTranscript(finalTranscript);
      }
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      if (event.error !== "no-speech") {
        setIsListening(false);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      // Restart if continuous mode is enabled
      if (isEnabled && settings.continuousListen) {
        setTimeout(() => {
          startListening();
        }, 100);
      }
    };

    return recognition;
  }, [settings.continuousListen, isEnabled]);

  // Handle final transcript
  const handleFinalTranscript = async (text) => {
    const trimmedText = text.trim().toLowerCase();

    // Check wake word if enabled
    if (settings.useWakeWord) {
      if (!trimmedText.includes(settings.wakeWord.toLowerCase())) {
        return; // Ignore if wake word not detected
      }
      // Remove wake word from text
      text = text.replace(new RegExp(settings.wakeWord, "gi"), "").trim();
    }

    if (!text) return;

    // Add to conversation log
    setConversationLog((prev) => [
      ...prev,
      { role: "user", text, timestamp: new Date().toISOString() },
    ]);

    setCurrentTranscript("");

    // Send to chat
    if (onSendMessage) {
      onSendMessage(text);
    }
  };

  // Start listening
  const startListening = useCallback(() => {
    try {
      if (!recognitionRef.current) {
        recognitionRef.current = initRecognition();
      }
      if (recognitionRef.current && !isListening) {
        recognitionRef.current.start();
      }
    } catch (err) {
      console.error("Failed to start listening:", err);
    }
  }, [initRecognition, isListening]);

  // Stop listening
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsListening(false);
  }, []);

  // Toggle voice mode
  const toggleVoiceMode = () => {
    if (isEnabled) {
      // Turning off
      stopListening();
      stopSpeaking();
      setIsEnabled(false);
    } else {
      // Turning on
      setIsEnabled(true);
      startListening();
    }
  };

  // Text-to-Speech
  const speak = useCallback(async (text) => {
    if (!text || isSpeaking || !settings.autoSpeak) return;

    setIsSpeaking(true);

    try {
      const response = await fetch("http://localhost:8000/voice/tts/base64", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text,
          voice: settings.voice,
          rate: settings.speechRate,
          pitch: "+0Hz",
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const audioBlob = base64ToBlob(data.audio, "audio/mpeg");
        const audioUrl = URL.createObjectURL(audioBlob);

        const audio = new Audio(audioUrl);
        audioRef.current = audio;

        audio.onended = () => {
          setIsSpeaking(false);
          URL.revokeObjectURL(audioUrl);
          // Resume listening after speaking
          if (isEnabled && settings.continuousListen) {
            startListening();
          }
        };

        // Pause listening while speaking
        stopListening();
        audio.play();
      } else {
        throw new Error("TTS request failed");
      }
    } catch (err) {
      console.error("TTS error:", err);
      // Fallback to browser TTS
      fallbackSpeak(text);
    }
  }, [isSpeaking, settings, isEnabled, startListening, stopListening]);

  // Browser fallback TTS
  const fallbackSpeak = (text) => {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-US";
      utterance.rate = 1.0;
      utterance.onend = () => {
        setIsSpeaking(false);
        if (isEnabled && settings.continuousListen) {
          startListening();
        }
      };
      utterance.onerror = () => setIsSpeaking(false);

      stopListening();
      window.speechSynthesis.speak(utterance);
    } else {
      setIsSpeaking(false);
    }
  };

  // Stop speaking
  const stopSpeaking = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
  };

  // Handle new response from GRACE
  useEffect(() => {
    if (lastResponse && isEnabled && settings.autoSpeak) {
      setConversationLog((prev) => [
        ...prev,
        { role: "assistant", text: lastResponse, timestamp: new Date().toISOString() },
      ]);
      speak(lastResponse);
    }
  }, [lastResponse, isEnabled, settings.autoSpeak, speak]);

  // Update recognition when settings change
  useEffect(() => {
    if (recognitionRef.current) {
      recognitionRef.current.continuous = settings.continuousListen;
    }
  }, [settings.continuousListen]);

  // Cleanup
  useEffect(() => {
    return () => {
      stopListening();
      stopSpeaking();
    };
  }, [stopListening]);

  // Helper to convert base64 to Blob
  const base64ToBlob = (base64, mimeType) => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  };

  return (
    <>
      {/* Main toggle button - always visible */}
      <button
        className={`voice-toggle-btn ${isEnabled ? "active" : ""} ${isListening ? "listening" : ""} ${isSpeaking ? "speaking" : ""}`}
        onClick={() => setIsPanelOpen(!isPanelOpen)}
        title={isEnabled ? "Voice mode active" : "Voice mode off"}
      >
        <VoiceIcon />
        {isEnabled && (
          <span className="voice-status-indicator">
            {isListening && <span className="status-dot listening"></span>}
            {isSpeaking && <span className="status-dot speaking"></span>}
            {isProcessing && <span className="status-dot processing"></span>}
          </span>
        )}
      </button>

      {/* Expanded panel */}
      {isPanelOpen && (
        <div className="persistent-voice-panel">
          <div className="voice-panel-header">
            <h3>Voice Mode</h3>
            <div className="voice-panel-actions">
              <button
                className="settings-btn"
                onClick={() => setShowSettings(!showSettings)}
                title="Settings"
              >
                <SettingsIcon />
              </button>
              <button
                className="close-btn"
                onClick={() => setIsPanelOpen(false)}
                title="Close"
              >
                <CloseIcon />
              </button>
            </div>
          </div>

          {/* Main controls */}
          <div className="voice-main-control">
            <button
              className={`power-btn ${isEnabled ? "on" : "off"}`}
              onClick={toggleVoiceMode}
            >
              <PowerIcon />
              <span>{isEnabled ? "ON" : "OFF"}</span>
            </button>

            {/* Status display */}
            <div className="voice-status-display">
              {!isEnabled && <span className="status-text">Voice mode disabled</span>}
              {isEnabled && isListening && (
                <span className="status-text listening">
                  <span className="pulse"></span>
                  Listening...
                </span>
              )}
              {isEnabled && isSpeaking && (
                <span className="status-text speaking">Speaking...</span>
              )}
              {isEnabled && isProcessing && (
                <span className="status-text processing">Processing...</span>
              )}
              {isEnabled && !isListening && !isSpeaking && !isProcessing && (
                <span className="status-text ready">Ready</span>
              )}
            </div>
          </div>

          {/* Current transcript */}
          {currentTranscript && (
            <div className="current-transcript">
              <span className="transcript-label">You:</span>
              <span className="transcript-text">{currentTranscript}</span>
            </div>
          )}

          {/* Conversation log */}
          {conversationLog.length > 0 && (
            <div className="conversation-log">
              {conversationLog.slice(-5).map((entry, idx) => (
                <div key={idx} className={`log-entry ${entry.role}`}>
                  <span className="log-role">
                    {entry.role === "user" ? "You" : "GRACE"}:
                  </span>
                  <span className="log-text">{entry.text}</span>
                </div>
              ))}
            </div>
          )}

          {/* Settings panel */}
          {showSettings && (
            <div className="voice-settings">
              <div className="setting-group">
                <label>Voice</label>
                <select
                  value={settings.voice}
                  onChange={(e) =>
                    setSettings({ ...settings, voice: e.target.value })
                  }
                >
                  {availableVoices.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="setting-group">
                <label>
                  <input
                    type="checkbox"
                    checked={settings.autoSpeak}
                    onChange={(e) =>
                      setSettings({ ...settings, autoSpeak: e.target.checked })
                    }
                  />
                  Auto-speak responses
                </label>
              </div>

              <div className="setting-group">
                <label>
                  <input
                    type="checkbox"
                    checked={settings.continuousListen}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        continuousListen: e.target.checked,
                      })
                    }
                  />
                  Continuous listening
                </label>
              </div>

              <div className="setting-group">
                <label>
                  <input
                    type="checkbox"
                    checked={settings.useWakeWord}
                    onChange={(e) =>
                      setSettings({ ...settings, useWakeWord: e.target.checked })
                    }
                  />
                  Use wake word
                </label>
                {settings.useWakeWord && (
                  <input
                    type="text"
                    value={settings.wakeWord}
                    onChange={(e) =>
                      setSettings({ ...settings, wakeWord: e.target.value })
                    }
                    placeholder="Wake word..."
                    className="wake-word-input"
                  />
                )}
              </div>

              <div className="setting-group">
                <label>Speech Rate</label>
                <select
                  value={settings.speechRate}
                  onChange={(e) =>
                    setSettings({ ...settings, speechRate: e.target.value })
                  }
                >
                  <option value="-20%">Slow</option>
                  <option value="+0%">Normal</option>
                  <option value="+20%">Fast</option>
                  <option value="+40%">Very Fast</option>
                </select>
              </div>
            </div>
          )}

          {/* Quick actions */}
          <div className="voice-quick-actions">
            {isSpeaking && (
              <button className="action-btn" onClick={stopSpeaking}>
                Stop Speaking
              </button>
            )}
            {conversationLog.length > 0 && (
              <button
                className="action-btn secondary"
                onClick={() => setConversationLog([])}
              >
                Clear History
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
}

// Icons
const VoiceIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const PowerIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
    <line x1="12" y1="2" x2="12" y2="12" />
  </svg>
);

const SettingsIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
);

const CloseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);
