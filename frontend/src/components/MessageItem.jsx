import React from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import CitationChip from "./CitationChip"

export default function MessageItem({ message, isStreaming }) {
  const isUser = message.role === "user"
  const citations = message.metadata_info?.citations || message.metadata?.citations || message.citations || []

  if (isUser) {
    return (
      <div className="chat-row user">
        <div className="user-bubble">
          {message.content}
        </div>
      </div>
    )
  }

  // Transform inline [Source: ...] text into custom inline citation tag
  const formattedContent = (message.content || "").replace(
    /\[Source:\s*([^\]]+)\]/gi,
    '`📖 Source: $1`'
  )

  const contentText = message.content || ""
  const hasDoc = contentText.includes("📚") || contentText.includes("DSM") || contentText.includes("Source:")
  const hasWeb = contentText.includes("🌐") || contentText.includes("http://") || contentText.includes("https://")
  const hasMCP = contentText.includes("🔌") || contentText.includes("MCP")
  const hasMemory = contentText.includes("psychiatric medical resident") || contentText.includes("sleep disorders") || contentText.includes("You mentioned earlier")

  return (
    <div className="chat-row ai">
      {/* ChatGPT Emerald AI Avatar */}
      <div style={{
        width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
        background: "var(--accent)", display: "flex",
        alignItems: "center", justifyContent: "center",
        marginTop: 2, boxShadow: "0 2px 8px rgba(16, 163, 127, 0.25)"
      }}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a10 10 0 1 0 10 10H12V2z" />
          <path d="M12 12L2.5 7.5" />
          <path d="M12 12v10" />
        </svg>
      </div>

      {/* AI Assistant Content */}
      <div className="ai-container">
        {/* Live Execution Capability Badges */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
          {hasDoc && (
            <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 12, background: "rgba(16, 185, 129, 0.15)", color: "#10b981", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
              📄 Document RAG
            </span>
          )}
          {hasWeb && (
            <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 12, background: "rgba(59, 130, 246, 0.15)", color: "#3b82f6", border: "1px solid rgba(59, 130, 246, 0.3)" }}>
              🌐 Web Search
            </span>
          )}
          {hasMCP && (
            <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 12, background: "rgba(168, 85, 247, 0.15)", color: "#a855f7", border: "1px solid rgba(168, 85, 247, 0.3)" }}>
              🔌 MCP Tool
            </span>
          )}
          {hasMemory && (
            <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 12, background: "rgba(236, 72, 153, 0.15)", color: "#ec4899", border: "1px solid rgba(236, 72, 153, 0.3)" }}>
              🧠 Memory Recall
            </span>
          )}
        </div>
        <div className="markdown-body">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              hr: ({ node, ...props }) => (
                <hr style={{ border: "none", height: "1px", background: "rgba(255, 255, 255, 0.12)", margin: "22px 0" }} {...props} />
              ),
              h2: ({ node, ...props }) => (
                <div style={{ marginTop: 22, marginBottom: 12, paddingBottom: 8, borderBottom: "1px solid rgba(255,255,255,0.12)" }}>
                  <h2 style={{ fontSize: "1.12rem", fontWeight: 700, color: "#f3f4f6", margin: 0, letterSpacing: "-0.01em" }} {...props} />
                </div>
              ),
              h3: ({ node, ...props }) => (
                <div style={{ marginTop: 18, marginBottom: 10, paddingBottom: 6, borderBottom: "1px dashed rgba(255,255,255,0.09)" }}>
                  <h3 style={{ fontSize: "0.98rem", fontWeight: 600, color: "#e5e7eb", margin: 0 }} {...props} />
                </div>
              ),
              table: ({ node, ...props }) => (
                <div className="table-wrapper">
                  <table {...props} />
                </div>
              ),
              code: ({ node, inline, children, ...props }) => {
                const text = String(children)
                if (text.startsWith("📖 Source:")) {
                  return (
                    <span className="inline-source-tag">
                      {text}
                    </span>
                  )
                }
                return <code {...props}>{children}</code>
              }
            }}
          >
            {formattedContent}
          </ReactMarkdown>
          {isStreaming && <span className="cursor-blink" />}
        </div>

        {/* Citations section */}
        {citations.length > 0 && (
          <div style={{ marginTop: 14, paddingTop: 10, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", marginBottom: 8, letterSpacing: "0.5px" }}>
              📚 SOURCES & CITATIONS:
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {citations.map((cit, idx) => (
                <CitationChip key={idx} citation={cit} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
