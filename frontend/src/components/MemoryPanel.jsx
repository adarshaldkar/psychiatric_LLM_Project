import React, { useState, useEffect } from "react"
import { Brain, Trash2, Pin, Info, X, ShieldAlert } from "lucide-react"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

export default function MemoryPanel({ isOpen, onClose }) {
  const [memories, setMemories] = useState([])
  const [loading, setLoading] = useState(false)
  const [explainingId, setExplainingId] = useState(null)

  useEffect(() => {
    if (isOpen) {
      fetchMemories()
    }
  }, [isOpen])

  const fetchMemories = async () => {
    setLoading(true)
    console.log("[MEMORY UI] Fetching long-term memories...")
    try {
      const token = localStorage.getItem("mindcare_token")
      const res = await fetch(`${API_BASE}/api/memory/long-term?t=${Date.now()}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-cache"
      })
      console.log("[MEMORY UI] HTTP Response Status:", res.status)
      if (res.ok) {
        const data = await res.json()
        console.log("[MEMORY UI] Raw JSON Payload Received:", data)
        const list = Array.isArray(data) ? data : (data.memories || data.data || [])
        console.log("[MEMORY UI] Parsed memories list length:", list.length)
        setMemories(list)
      } else {
        console.error("[MEMORY UI] Non-200 HTTP response:", res.status)
      }
    } catch (err) {
      console.error("[MEMORY UI] Failed to fetch memories:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      const token = localStorage.getItem("mindcare_token")
      const res = await fetch(`${API_BASE}/api/memory/long-term/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setMemories(memories.filter((m) => m.id !== id))
      }
    } catch (err) {
      console.error("Failed to delete memory:", err)
    }
  }

  const togglePin = (id) => {
    setMemories(memories.map(m => m.id === id ? { ...m, isPinned: !m.isPinned } : m))
  }

  if (!isOpen) return null

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 100,
      background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)",
      display: "flex", alignItems: "center", justifyContent: "center", padding: 16
    }}>
      <div style={{
        background: "#1e1e1e", border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: 12, width: "100%", maxWidth: 640, maxHeight: "80vh",
        display: "flex", flexDirection: "column", overflow: "hidden",
        boxShadow: "0 8px 32px rgba(0,0,0,0.5)"
      }}>
        {/* Header */}
        <div style={{
          padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.08)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          background: "#242424"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Brain size={20} color="var(--accent)" />
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "#fff" }}>
              Long-Term Memory Management
            </h3>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#888", cursor: "pointer" }}>
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: 20, overflowY: "auto", flex: 1 }}>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 0, marginBottom: 16 }}>
            MindCare AI remembers persistent facts across sessions to personalize clinical discussions. You have full control to view, pin, delete, or inspect why memories exist.
          </p>

          {loading ? (
            <div style={{ padding: 40, textAlign: "center", color: "#888", fontSize: 13 }}>
              Loading memories...
            </div>
          ) : memories.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", color: "#666", fontSize: 13 }}>
              No long-term memories stored yet. Mention your clinical background or study topics in chat to seed memories!
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {memories.map((mem) => (
                <div key={mem.id} style={{
                  background: mem.isPinned ? "rgba(16, 163, 127, 0.08)" : "#262626",
                  border: mem.isPinned ? "1px solid rgba(16, 163, 127, 0.3)" : "1px solid rgba(255,255,255,0.06)",
                  borderRadius: 8, padding: 14, transition: "all 0.15s ease"
                }}>
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
                    <div style={{ flex: 1 }}>
                      <p style={{ margin: 0, fontSize: 14, color: "#ececec", lineHeight: 1.5 }}>
                        "{mem.content}"
                      </p>
                      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8, fontSize: 11, color: "#888" }}>
                        <span>Type: {mem.memory_type || "semantic"}</span>
                        <span>Confidence: {Math.round((mem.confidence_score || 0.8) * 100)}%</span>
                        {mem.created_at && <span>Added: {new Date(mem.created_at).toLocaleDateString()}</span>}
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <button
                        onClick={() => setExplainingId(explainingId === mem.id ? null : mem.id)}
                        title="Why do you remember this?"
                        style={{
                          background: "rgba(255,255,255,0.05)", border: "none",
                          borderRadius: 4, padding: 6, color: "#aaa", cursor: "pointer"
                        }}
                      >
                        <Info size={15} />
                      </button>
                      <button
                        onClick={() => togglePin(mem.id)}
                        title={mem.isPinned ? "Unpin memory" : "Pin memory"}
                        style={{
                          background: mem.isPinned ? "var(--accent)" : "rgba(255,255,255,0.05)",
                          border: "none", borderRadius: 4, padding: 6,
                          color: mem.isPinned ? "#fff" : "#aaa", cursor: "pointer"
                        }}
                      >
                        <Pin size={15} />
                      </button>
                      <button
                        onClick={() => handleDelete(mem.id)}
                        title="Delete memory"
                        style={{
                          background: "rgba(239, 68, 68, 0.1)", border: "none",
                          borderRadius: 4, padding: 6, color: "#ef4444", cursor: "pointer"
                        }}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>

                  {/* Explain Drawer */}
                  {explainingId === mem.id && (
                    <div style={{
                      marginTop: 10, paddingTop: 10, borderTop: "1px solid rgba(255,255,255,0.08)",
                      fontSize: 12, color: "#aaa", lineHeight: 1.5, background: "rgba(0,0,0,0.2)",
                      padding: 10, borderRadius: 6
                    }}>
                      💡 <strong>Why MindCare AI remembers this:</strong> This fact was extracted during a past conversation turn because it represents high-importance personal background context.
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
