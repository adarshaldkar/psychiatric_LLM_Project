import React, { useRef, useEffect, useState, useCallback } from "react"
import { useStore } from "../store/useStore"

/* ── Icons ───────────────────────────────────────────────────────── */
const PlusIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
)

const SendIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
)

const MicIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
    <line x1="12" y1="19" x2="12" y2="23"/>
    <line x1="8" y1="23" x2="16" y2="23"/>
  </svg>
)

/* Audio wave bars — animated when recording */
const WaveIcon = ({ active }) => (
  <svg width="20" height="16" viewBox="0 0 20 16" fill="none">
    {[3,7,11,15,19].map((cx, i) => (
      <rect
        key={i}
        x={cx - 1.2}
        y={active ? 0 : 4}
        width={2.4}
        rx={1.2}
        height={active ? 16 : 8}
        fill="currentColor"
        style={{
          transformOrigin: `${cx}px 8px`,
          animation: active ? `wave-bar 0.8s ease-in-out ${i * 0.12}s infinite alternate` : "none",
          opacity: active ? 1 : 0.4,
          transition: "all 0.2s"
        }}
      />
    ))}
  </svg>
)

export default function InputBar({ onSend, onOpenDocuments }) {
  const [text, setText] = useState("")
  const [isRecording, setIsRecording] = useState(false)
  const [micAvailable, setMicAvailable] = useState(false)
  const { isStreaming } = useStore()
  const textareaRef = useRef(null)
  const recognitionRef = useRef(null)
  const maxRows = 5

  /* Check mic availability */
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    setMicAvailable(!!SpeechRecognition)
  }, [])

  /* Auto-resize textarea */
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = "auto"
    const lineH = 22
    const max = lineH * maxRows + 24
    ta.style.height = Math.min(ta.scrollHeight, max) + "px"
  }, [text])

  const handleSend = () => {
    const msg = text.trim()
    if (!msg || isStreaming) return
    onSend(msg)
    setText("")
    if (textareaRef.current) textareaRef.current.style.height = "auto"
  }

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  /* Mic toggle using Web Speech API */
  const toggleMic = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) return

    if (isRecording) {
      recognitionRef.current?.stop()
      setIsRecording(false)
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = "en-US"
    recognition.continuous = false
    recognition.interimResults = true

    recognition.onstart = () => setIsRecording(true)

    recognition.onresult = (e) => {
      const transcript = Array.from(e.results)
        .map(r => r[0].transcript)
        .join("")
      setText(transcript)
    }

    recognition.onend = () => {
      setIsRecording(false)
      // Auto-send if we got text
      setTimeout(() => {
        const ta = textareaRef.current
        const finalText = ta?.value?.trim()
        if (finalText) {
          onSend(finalText)
          setText("")
        }
      }, 300)
    }

    recognition.onerror = () => setIsRecording(false)

    recognitionRef.current = recognition
    recognition.start()
  }, [isRecording, onSend])

  const canSend = text.trim().length > 0 && !isStreaming

  return (
    <>
      {/* Wave bar animation keyframes */}
      <style>{`
        @keyframes wave-bar {
          from { transform: scaleY(0.3); }
          to   { transform: scaleY(1); }
        }
        .pill-input-wrap {
          position: relative;
          max-width: 840px;
          margin: 0 auto;
          display: flex;
          align-items: flex-end;
          gap: 0;
          background: #2f2f2f;
          border: 1px solid rgba(255,255,255,0.15);
          border-radius: 26px;
          padding: 8px 10px 8px 16px;
          transition: border-color 0.2s, box-shadow 0.2s;
          box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }
        .pill-input-wrap:focus-within {
          border-color: rgba(255,255,255,0.3);
          box-shadow: 0 4px 28px rgba(0,0,0,0.5);
        }
        .pill-action-btn {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border: none;
          background: transparent;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #b4b4b4;
          transition: background 0.15s, color 0.15s;
          flex-shrink: 0;
        }
        .pill-action-btn:hover {
          background: rgba(255,255,255,0.1);
          color: #ffffff;
        }
        .pill-send-btn {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border: none;
          background: #ffffff;
          color: #000000;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.15s;
          flex-shrink: 0;
        }
        .pill-send-btn:hover {
          background: #ececec;
          transform: scale(1.04);
        }
        .pill-send-btn:disabled {
          background: rgba(255, 255, 255, 0.15);
          color: rgba(255, 255, 255, 0.3);
          cursor: not-allowed;
          transform: none;
        }
        .pill-mic-btn-active {
          background: rgba(239,68,68,0.18) !important;
          color: #ef4444 !important;
        }
        .pill-mic-btn-active:hover {
          background: rgba(239,68,68,0.28) !important;
        }
        .recording-ring {
          position: absolute;
          inset: -3px;
          border-radius: 50%;
          border: 2px solid #ef4444;
          animation: rec-pulse 1s ease-in-out infinite;
        }
        @keyframes rec-pulse {
          0%,100% { opacity: 1; transform: scale(1); }
          50%      { opacity: 0.4; transform: scale(1.15); }
        }
      `}</style>

      <div style={{
        padding: "12px 16px 16px",
        background: "var(--bg-primary)",
      }}>
        <div className="pill-input-wrap">

          {/* Left: + / attach button */}
          <button
            className="pill-action-btn"
            title="Open Knowledge Base"
            onClick={onOpenDocuments}
            style={{ marginRight: 4 }}
          >
            <PlusIcon />
          </button>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={handleKey}
            placeholder={isRecording ? "Listening…" : "Ask about mental health, psychiatry, therapy…"}
            rows={1}
            disabled={isStreaming}
            style={{
              flex: 1,
              background: "none",
              border: "none",
              outline: "none",
              color: isRecording ? "#ef4444" : "var(--text-primary)",
              fontSize: 14,
              lineHeight: "22px",
              fontFamily: "inherit",
              padding: "5px 0",
              overflowY: "auto",
              maxHeight: `${22 * maxRows + 24}px`,
              opacity: isStreaming ? 0.5 : 1,
              resize: "none",
              minWidth: 0,
            }}
          />

          {/* Right buttons cluster */}
          <div style={{ display: "flex", alignItems: "center", gap: 4, marginLeft: 6 }}>

            {/* Mic button */}
            {micAvailable && (
              <div style={{ position: "relative" }}>
                {isRecording && <div className="recording-ring" />}
                <button
                  className={`pill-action-btn${isRecording ? " pill-mic-btn-active" : ""}`}
                  title={isRecording ? "Stop recording" : "Voice input"}
                  onClick={toggleMic}
                  disabled={isStreaming}
                >
                  {isRecording
                    ? <WaveIcon active={true} />
                    : <MicIcon />
                  }
                </button>
              </div>
            )}

            {/* Send button */}
            <button
              className="pill-send-btn"
              onClick={handleSend}
              disabled={!canSend}
              title="Send (Enter)"
              style={{
                background: canSend ? "var(--accent)" : "rgba(255,255,255,0.06)",
                color: canSend ? "white" : "var(--text-muted)",
                cursor: canSend ? "pointer" : "not-allowed",
              }}
              onMouseEnter={e => canSend && (e.currentTarget.style.background = "var(--accent-hover)")}
              onMouseLeave={e => canSend && (e.currentTarget.style.background = "var(--accent)")}
            >
              {isStreaming
                ? <div className="pulse-dot" style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--text-muted)" }} />
                : <SendIcon />
              }
            </button>
          </div>
        </div>

        {/* Sub-hint */}
        <p style={{ textAlign: "center", fontSize: 11, color: "var(--text-muted)", marginTop: 10, letterSpacing: "0.01em" }}>
          {isRecording
            ? "🔴 Recording… speak now, auto-sends when done"
            : "Enter to send · Shift+Enter for new line · Emergencies: call 112 / 988"
          }
        </p>
      </div>
    </>
  )
}
