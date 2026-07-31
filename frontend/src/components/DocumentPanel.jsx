import React, { useState, useEffect, useRef } from "react"
import { useStore } from "../store/useStore"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

const STATUS_DOT_COLOR = {
  ready:      "#10b981",
  chat_ready: "#f59e0b",
  failed:     "#ef4444",
  uploaded:   "#8b5cf6",
  validating: "#8b5cf6",
  extracting: "#3b82f6",
  ocr:        "#3b82f6",
  cleaning:   "#3b82f6",
  chunking:   "#f59e0b",
}

/* Animated shimmer for the progress bar fill */
const SHIMMER_STYLE = `
  @keyframes shimmer {
    0%   { background-position: -200% 0; }
    100% { background-position:  200% 0; }
  }
  .progress-fill {
    background: linear-gradient(90deg, #7c6aff 0%, #a78bfa 50%, #7c6aff 100%);
    background-size: 200% 100%;
    animation: shimmer 1.8s linear infinite;
  }
`

function DocStatusBadge({ doc }) {
  const isOptimizing = doc.status === "chat_ready"
  const isReady      = doc.status === "ready"
  const isFailed     = doc.status === "failed"
  const progress     = doc.embedding_progress ?? 0
  const label        = doc.status_label || doc.status

  return (
    <div style={{ marginTop: 6 }}>
      {/* Status label row */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: isOptimizing ? 5 : 0 }}>
        <span style={{
          width: 7, height: 7, borderRadius: "50%", flexShrink: 0,
          background: STATUS_DOT_COLOR[doc.status] || "var(--text-muted)"
        }} />
        <span style={{
          fontSize: 11,
          color: isReady ? "#10b981" : isFailed ? "#ef4444" : "var(--text-secondary)",
          fontWeight: 500
        }}>
          {label}
        </span>
        {isOptimizing && (
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: "auto" }}>
            {progress}%
          </span>
        )}
      </div>

      {/* Progress bar — only during chat_ready */}
      {isOptimizing && (
        <div style={{
          height: 4, borderRadius: 99, background: "var(--bg-tertiary)",
          overflow: "hidden", width: "100%"
        }}>
          <div
            className="progress-fill"
            style={{
              height: "100%",
              width: `${Math.max(progress, 4)}%`,
              borderRadius: 99,
              transition: "width 0.8s ease"
            }}
          />
        </div>
      )}

      {/* Quality indicator text */}
      {isOptimizing && (
        <div style={{ fontSize: 10, color: "#f59e0b", marginTop: 3 }}>
          Learning this book... semantic search improving
        </div>
      )}
      {isReady && (
        <div style={{ fontSize: 10, color: "#10b981", marginTop: 2 }}>
          Optimized
        </div>
      )}
    </div>
  )
}


export default function DocumentPanel({ isOpen, onClose }) {
  const { token, logout } = useStore()
  const [documents, setDocuments]   = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [isGlobal, setIsGlobal]     = useState(false)
  const [author, setAuthor]         = useState("")
  const [tags, setTags]             = useState("")
  const [uploadError, setUploadError] = useState(null)
  const fileInputRef = useRef(null)

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/documents`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.status === 401) {
        logout()
        onClose()
        return
      }
      if (res.ok) {
        const data = await res.json()
        console.log("[DocumentPanel] Documents fetched:", data.map(d => ({
          name: d.original_name,
          status: d.status,
          status_label: d.status_label,
          progress: d.embedding_progress,
          embedded: d.embedded_chunk_count,
          total_child: d.child_chunk_count,
        })))
        setDocuments(data)
      }
    } catch (err) {
      console.error("[DocumentPanel] Failed to fetch documents:", err)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchDocuments()
    }
  }, [isOpen])

  // Poll every 3 seconds while any document is still processing
  useEffect(() => {
    if (!isOpen) return
    const hasProcessing = documents.some(
      doc => doc.status !== "ready" && doc.status !== "failed"
    )
    if (!hasProcessing) return

    const timer = setInterval(() => {
      fetchDocuments()
    }, 3000)

    return () => clearInterval(timer)
  }, [isOpen, documents])

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    console.log("[DocumentPanel] Uploading file:", file.name, `(${(file.size / 1024 / 1024).toFixed(2)} MB)`)
    setIsUploading(true)
    setUploadError(null)

    const formData = new FormData()
    formData.append("file", file)
    formData.append("is_global", isGlobal ? "true" : "false")
    if (author) formData.append("author", author)
    if (tags)   formData.append("tags", tags)

    try {
      const res = await fetch(`${API_BASE}/api/documents/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      })

      if (res.status === 401) {
        setUploadError("Session expired. Please log out and log back in.")
        logout()
        setIsUploading(false)
        return
      }

      const data = await res.json()
      if (!res.ok) {
        console.error("[DocumentPanel] Upload failed:", data)
        setUploadError(data.detail || "Upload failed")
      } else {
        console.log("[DocumentPanel] Upload accepted:", data)
        fetchDocuments()
        if (fileInputRef.current) fileInputRef.current.value = ""
        setAuthor("")
        setTags("")
      }
    } catch (err) {
      console.error("[DocumentPanel] Network error:", err)
      setUploadError("Network error uploading document")
    } finally {
      setIsUploading(false)
    }
  }

  const handleDelete = async (docId) => {
    if (!window.confirm("Are you sure you want to delete this document?")) return
    console.log("[DocumentPanel] Deleting document:", docId)

    try {
      const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        console.log("[DocumentPanel] Document deleted:", docId)
        fetchDocuments()
      } else {
        console.error("[DocumentPanel] Delete failed:", await res.json())
      }
    } catch (err) {
      console.error("[DocumentPanel] Failed to delete document:", err)
    }
  }

  if (!isOpen) return null

  return (
    <>
      <style>{SHIMMER_STYLE}</style>

      {/* Outer backdrop overlay */}
      <div style={{
        position: "fixed",
        top: 0, left: 0, right: 0, bottom: 0,
        background: "rgba(0, 0, 0, 0.7)",
        backdropFilter: "blur(4px)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16
      }}>

        {/* Inner modal card */}
        <div style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border)",
          borderRadius: 14,
          width: "100%",
          maxWidth: 650,
          maxHeight: "85vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 20px 40px rgba(0,0,0,0.5)",
          overflow: "hidden"
        }}>

          {/* Header */}
          <div style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: "var(--accent)", display: "flex",
                alignItems: "center", justifyContent: "center",
                color: "white", fontSize: 16
              }}>
                📚
              </div>
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                  Knowledge Base &amp; Uploads
                </h3>
                <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0 }}>
                  Upload psychiatric books and documents for grounded RAG answers
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              style={{
                background: "none", border: "none", color: "var(--text-muted)",
                cursor: "pointer", fontSize: 18, padding: 4
              }}
            >
              ✕
            </button>
          </div>

          {/* Scrollable content body */}
          <div style={{ padding: 20, overflowY: "auto", flex: 1 }}>

            {/* Upload Box */}
            <div style={{
              background: "var(--bg-primary)",
              border: "2px dashed var(--border)",
              borderRadius: 10,
              padding: 20,
              textAlign: "center",
              marginBottom: 20
            }}>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                style={{ display: "none" }}
                accept=".pdf,.docx,.txt,.pptx,.png,.jpg,.jpeg"
              />
              <div style={{ fontSize: 32, marginBottom: 8 }}>📄</div>
              <p style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 500, margin: "0 0 4px" }}>
                Upload Medical / Psychiatric Document
              </p>
              <p style={{ fontSize: 11, color: "var(--text-muted)", margin: "0 0 12px" }}>
                Supports PDF, DOCX, TXT, PPTX, PNG, JPG · Max 100MB
              </p>

              <div style={{
                display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center",
                alignItems: "center", marginBottom: 14
              }}>
                <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12, color: "var(--text-secondary)" }}>
                  <input
                    type="checkbox"
                    checked={isGlobal}
                    onChange={e => setIsGlobal(e.target.checked)}
                  />
                  Make Global (visible to all users)
                </label>

                <input
                  type="text"
                  placeholder="Author (optional)"
                  value={author}
                  onChange={e => setAuthor(e.target.value)}
                  style={{
                    background: "var(--bg-secondary)", border: "1px solid var(--border)",
                    borderRadius: 6, padding: "4px 8px", fontSize: 12, color: "var(--text-primary)"
                  }}
                />
              </div>

              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                style={{
                  background: "var(--accent)", color: "white", border: "none",
                  borderRadius: 8, padding: "8px 20px", fontSize: 13, fontWeight: 500,
                  cursor: isUploading ? "not-allowed" : "pointer",
                  opacity: isUploading ? 0.7 : 1
                }}
              >
                {isUploading ? "Uploading..." : "Choose Document"}
              </button>

              {uploadError && (
                <p style={{ color: "#ef4444", fontSize: 12, marginTop: 8, margin: "8px 0 0" }}>
                  {uploadError}
                </p>
              )}
            </div>

            {/* Document List */}
            <h4 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 10 }}>
              Uploaded Documents ({documents.length})
            </h4>

            {documents.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--text-muted)", textAlign: "center", padding: 20 }}>
                No documents in knowledge base yet.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {documents.map(doc => (
                  <div
                    key={doc.id}
                    style={{
                      background: "var(--bg-primary)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      padding: "12px 14px",
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      gap: 8
                    }}
                  >
                    {/* Left: doc info + status */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3, flexWrap: "wrap" }}>
                        <span style={{
                          fontSize: 13, fontWeight: 500, color: "var(--text-primary)",
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"
                        }}>
                          {doc.original_name}
                        </span>
                        {doc.is_global && (
                          <span style={{ background: "var(--accent)", color: "white", fontSize: 9, padding: "1px 6px", borderRadius: 4, fontWeight: 700, flexShrink: 0 }}>
                            GLOBAL
                          </span>
                        )}
                        {doc.version_number > 1 && (
                          <span style={{ background: "var(--bg-tertiary)", color: "var(--text-muted)", fontSize: 9, padding: "1px 5px", borderRadius: 4, flexShrink: 0 }}>
                            v{doc.version_number}
                          </span>
                        )}
                      </div>

                      <div style={{ fontSize: 11, color: "var(--text-muted)", display: "flex", gap: 12, flexWrap: "wrap" }}>
                        <span>{(doc.file_size_bytes / (1024 * 1024)).toFixed(1)} MB</span>
                        {doc.chunk_count && (
                          <span>{doc.chunk_count} chunks · {doc.total_tokens?.toLocaleString()} tokens</span>
                        )}
                        {doc.author && <span>By {doc.author}</span>}
                      </div>

                      <DocStatusBadge doc={doc} />

                      {doc.error_message && (
                        <p style={{ fontSize: 11, color: "#ef4444", margin: "4px 0 0", lineHeight: 1.4 }}>
                          {doc.error_message}
                        </p>
                      )}
                    </div>

                    {/* Right: delete button */}
                    <button
                      onClick={() => handleDelete(doc.id)}
                      style={{
                        background: "none", border: "none", cursor: "pointer",
                        color: "var(--text-muted)", fontSize: 15, flexShrink: 0,
                        padding: "2px 4px", marginTop: 1
                      }}
                      title="Delete document"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            )}

          </div>
          {/* END scrollable body */}

        </div>
        {/* END inner modal card */}

      </div>
      {/* END outer backdrop */}

    </>
  )
}
