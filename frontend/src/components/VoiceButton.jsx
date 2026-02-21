import { useState, useRef, useEffect, useCallback } from "react";
import "./VoiceButton.css";

/**
 * VoiceButton Component
 *
 * Provides voice input (STT) and output (TTS) for any chat interface.
 * Uses browser's Web Speech API for STT and backend edge-tts for TTS.
 *
 * Props:
 * - onTranscript: Callback when speech is transcribed (text) => void
 * - onSpeakText: Text to speak (will trigger TTS)
 * - disabled: Disable the button
 * - size: "small" | "medium" | "large"
 * - showTTSButton: Show separate TTS button
 */
export default function VoiceButton({
  onTranscript,
  speakText,
  disabled = false,
  size = "medium",
  showTTSButton = false,
  placeholder = "Click to speak...",
}) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState(null);
  const [supported, setSupported] = useState(true);

  const recognitionRef = useRef(null);
  const audioRef = useRef(null);

  // Check browser support
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
      setError("Speech recognition not supported in this browser");
    }
  }, []);

  // Initialize speech recognition
  const initRecognition = useCallback(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) return null;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };

    recognition.onresult = (event) => {
      let interimTranscript = "";
      let finalTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      setTranscript(finalTranscript || interimTranscript);

      if (finalTranscript && onTranscript) {
        onTranscript(finalTranscript);
      }
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      setError(`Error: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    return recognition;
  }, [onTranscript]);

  // Start listening
  const startListening = useCallback(() => {
    if (!supported || disabled) return;

    try {
      if (!recognitionRef.current) {
        recognitionRef.current = initRecognition();
      }

      if (recognitionRef.current) {
        setTranscript("");
        recognitionRef.current.start();
      }
    } catch (err) {
      console.error("Failed to start recognition:", err);
      setError("Failed to start voice recognition");
    }
  }, [supported, disabled, initRecognition]);

  // Stop listening
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsListening(false);
  }, []);

  // Toggle listening
  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  // Text-to-Speech function
  const speak = useCallback(async (text) => {
    if (!text || isSpeaking) return;

    setIsSpeaking(true);

    try {
      // Try backend TTS first (higher quality)
      const response = await fetch("http://localhost:8000/voice/tts/base64", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text,
          voice: "en-US-AriaNeural",
          rate: "+0%",
          pitch: "+0Hz",
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const audioBlob = base64ToBlob(data.audio, "audio/mpeg");
        const audioUrl = URL.createObjectURL(audioBlob);

        if (audioRef.current) {
          audioRef.current.src = audioUrl;
          audioRef.current.play();
        } else {
          const audio = new Audio(audioUrl);
          audioRef.current = audio;
          audio.onended = () => {
            setIsSpeaking(false);
            URL.revokeObjectURL(audioUrl);
          };
          audio.play();
        }
      } else {
        // Fallback to browser TTS
        fallbackSpeak(text);
      }
    } catch (err) {
      console.error("TTS error:", err);
      // Fallback to browser TTS
      fallbackSpeak(text);
    }
  }, [isSpeaking]);

  // Browser fallback TTS
  const fallbackSpeak = (text) => {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-US";
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    } else {
      setIsSpeaking(false);
      setError("Text-to-speech not supported");
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

  // Manual speak function (triggered by button click)
  const handleSpeakClick = () => {
    if (isSpeaking) {
      stopSpeaking();
    } else if (speakText) {
      speak(speakText);
    }
  };

  // REMOVED: Auto-trigger on speakText change
  // This was causing automatic speech for every response
  // Now TTS is manual-only (user must click speaker button)

  // Cleanup
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (audioRef.current) {
        audioRef.current.pause();
      }
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

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

  if (!supported) {
    return (
      <div className={`voice-button-container ${size}`}>
        <button className="voice-button disabled" disabled title="Voice not supported">
          <MicOffIcon />
        </button>
      </div>
    );
  }

  return (
    <div className={`voice-button-container ${size}`}>
      {/* Microphone button */}
      <button
        type="button"
        className={`voice-button mic-button ${isListening ? "listening" : ""} ${disabled ? "disabled" : ""
          }`}
        onClick={toggleListening}
        disabled={disabled || isSpeaking}
        title={isListening ? "Stop listening" : "Start voice input"}
      >
        {isListening ? <MicActiveIcon /> : <MicIcon />}
        {isListening && <span className="pulse-ring"></span>}
      </button>

      {/* Speaker button (optional) */}
      {showTTSButton && (
        <button
          type="button"
          className={`voice-button speaker-button ${isSpeaking ? "speaking" : ""}`}
          onClick={handleSpeakClick}
          disabled={!speakText && !isSpeaking}
          title={isSpeaking ? "Stop speaking" : "Click to speak response"}
        >
          {isSpeaking ? <SpeakerActiveIcon /> : <SpeakerIcon />}
        </button>
      )}

      {/* Status indicator */}
      {(isListening || transcript) && (
        <div className="voice-status">
          {isListening && <span className="listening-text">Listening...</span>}
          {transcript && <span className="transcript-preview">{transcript}</span>}
        </div>
      )}

      {/* Error message */}
      {error && <div className="voice-error">{error}</div>}

      {/* Hidden audio element */}
      <audio ref={audioRef} onEnded={() => setIsSpeaking(false)} />
    </div>
  );
}

// Icons
const MicIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const MicActiveIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="2">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const MicOffIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="1" y1="1" x2="23" y2="23" />
    <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
    <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const SpeakerIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
  </svg>
);

const SpeakerActiveIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="2">
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
  </svg>
);
