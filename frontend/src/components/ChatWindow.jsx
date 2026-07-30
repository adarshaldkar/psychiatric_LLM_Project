import React, { useEffect, useRef } from "react"
import MessageItem from "./MessageItem"
import { useStore } from "../store/useStore"

const HamburgerIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="3" y1="6" x2="21" y2="6"/>
    <line x1="3" y1="12" x2="21" y2="12"/>
    <line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
)

const suggestions = [
  { icon: "🧠", title: "Anxiety", prompt: "What are the DSM-5 criteria for Generalized Anxiety Disorder?" },
  { icon: "💊", title: "Medications", prompt: "How do SSRIs work and what are common side effects?" },
  { icon: "🌙", title: "Sleep", prompt: "What is the relationship between sleep disorders and depression?" },
  { icon: "🫁", title: "Trauma", prompt: "Explain the difference between acute stress disorder and PTSD." },
]

function StatusBar({ streaming, messages }) {
  if (streaming) return (
    <div style={{ padding: "6px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 6, background: "var(--bg-secondary)" }}>
      <div className="pulse-dot" style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--accent)", flexShrink: 0 }} />
      <span style={{ fontSize: 12, color: "var(--accent)" }}>MindCare is thinking…</span>
    </div>
  )
  if (messages.length > 0) return (
    <div style={{ padding: "6px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 6, background: "var(--bg-secondary)" }}>
      <div style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--success)", flexShrink: 0 }} />
      <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Ready · {messages.length} message{messages.length !== 1 ? "s" : ""}</span>
    </div>
  )
  return null
}

export default function ChatWindow({ onSendSuggestion, onOpenSidebar, onToggleSidebar }) {
  const { messages, isStreaming } = useStore()
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Mark last assistant message as streaming for blinking cursor
  const allMessages = messages.map((msg, i) => {
    const isLast = i === messages.length - 1
    return (isLast && isStreaming && msg.role === "assistant")
      ? { ...msg, _streaming: true }
      : msg
  })

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "var(--bg-primary)", overflow: "hidden" }}>
      {/* Header */}
      <div style={{
        padding: "12px 16px", borderBottom: "1px solid var(--border)",
        background: "var(--bg-secondary)",
        display: "flex", alignItems: "center", gap: 10
      }}>
        {/* Toggle Sidebar Button */}
        <button
          className="sidebar-toggle-btn"
          onClick={onToggleSidebar || onOpenSidebar}
          title="Toggle sidebar"
        >
          <HamburgerIcon />
        </button>

        <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--success)", flexShrink: 0 }} />
        <span style={{ fontSize: 14, fontWeight: 500, color: "var(--text-primary)" }}>MindCare AI</span>
        <span style={{
          fontSize: 11, color: "var(--text-muted)", background: "var(--bg-primary)",
          padding: "2px 8px", borderRadius: 99, border: "1px solid var(--border)",
          whiteSpace: "nowrap"
        }}>Psychiatric Knowledge</span>

        <div style={{ flex: 1 }} />

        {/* GitHub Repository Star Badge */}
        <a 
          href="https://github.com/adarshaldkar/psychiatric_LLM_Project" 
          target="_blank" 
          rel="noopener noreferrer"
          style={{
            display: "flex", alignItems: "center", gap: 6,
            background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 20, padding: "5px 12px", fontSize: 12, fontWeight: 500,
            color: "var(--text-primary)", textDecoration: "none", transition: "all 0.15s"
          }}
          onMouseEnter={e => { e.currentTarget.style.background = "rgba(255, 255, 255, 0.12)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.25)" }}
          onMouseLeave={e => { e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)" }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
            <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
          </svg>
          <span>GitHub</span>
          <span style={{ 
            background: "rgba(16, 163, 127, 0.2)", border: "1px solid rgba(16, 163, 127, 0.4)",
            padding: "1px 6px", borderRadius: 10, fontSize: 10, color: "#2dd4bf", fontWeight: 600
          }}>98%</span>
        </a>
      </div>

      {/* Status bar */}
      <StatusBar streaming={isStreaming} messages={messages} />

      {/* Messages / Welcome */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 12px" }}>
        {allMessages.length === 0 ? (
          <WelcomeScreen onSelect={onSendSuggestion} />
        ) : (
          <div style={{ maxWidth: 840, width: "100%", margin: "0 auto", display: "flex", flexDirection: "column", gap: 16, padding: "0 16px" }}>
            {allMessages.map((msg, i) => (
              <MessageItem key={i} message={msg} isStreaming={msg._streaming} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>
    </div>
  )
}

function WelcomeScreen({ onSelect }) {
  return (
    <div style={{ maxWidth: 720, width: "100%", margin: "0 auto", paddingTop: 40, textAlign: "center", padding: "40px 16px 0" }}>
      {/* Icon */}
      <div style={{
        width: 48, height: 48, borderRadius: "50%",
        background: "var(--accent-dim)", border: "1px solid var(--border-subtle)",
        display: "flex", alignItems: "center", justifyContent: "center",
        margin: "0 auto 16px"
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.44l-1.01-1.01A2.5 2.5 0 0 1 4.5 16V9A2.5 2.5 0 0 1 7 6.5" />
          <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.44l1.01-1.01A2.5 2.5 0 0 0 19.5 16V9A2.5 2.5 0 0 0 17 6.5" />
        </svg>
      </div>

      <h2 style={{ fontSize: 22, fontWeight: 600, color: "#ffffff", letterSpacing: "-0.4px", marginBottom: 8 }}>
        What can I help you understand?
      </h2>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: 24 }}>
        Ask about conditions, treatments, therapies, medications, or emotional wellbeing.
      </p>

      {/* Suggestions Grid */}
      <div className="suggestion-grid">
        {suggestions.map((s, i) => (
          <button key={i} onClick={() => onSelect(s.prompt)} style={{
            padding: "16px 18px", borderRadius: 14,
            background: "var(--bg-secondary)", border: "1px solid var(--border)",
            cursor: "pointer", textAlign: "left", transition: "all 0.2s", fontFamily: "inherit",
            display: "flex", flexDirection: "column", gap: 4
          }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.2)"; e.currentTarget.style.background = "var(--bg-tertiary)" }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.background = "var(--bg-secondary)" }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 600, color: "#ffffff" }}>
              <span>{s.icon}</span>
              <span>{s.title}</span>
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5, marginTop: 2 }}>
              {s.prompt}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
