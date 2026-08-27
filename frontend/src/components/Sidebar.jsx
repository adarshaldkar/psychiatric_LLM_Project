import React, { useState, useRef, useEffect } from "react"
import { useStore } from "../store/useStore"

const PlusIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
)
const BookIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
  </svg>
)
const ChatIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
)
const MoreIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>
  </svg>
)
const ShareIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
  </svg>
)
const EditIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
  </svg>
)
const PinIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14l-1.5-6V5a1.5 1.5 0 0 0-3 0v.5M7.5 5.5V5a1.5 1.5 0 0 0-3 0v6z"/>
  </svg>
)
const ArchiveIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/>
  </svg>
)
const TrashIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
  </svg>
)
const UserIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
  </svg>
)
const LogoutIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
  </svg>
)
const CloseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
)

export default function Sidebar({ isOpen, onClose, onNewChat, onSelectConversation, onDeleteConversation, onOpenDocuments, onOpenMemory }) {
  const { conversations, currentConversationId, user, logout, isGuest, openAuthModal } = useStore()
  const [hoveredId, setHoveredId] = useState(null)
  const [menuOpenId, setMenuOpenId] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [editTitle, setEditTitle] = useState("")
  const [pinnedIds, setPinnedIds] = useState([])
  const [archivedIds, setArchivedIds] = useState([])
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [showArchiveModal, setShowArchiveModal] = useState(false)
  const [toastMsg, setToastMsg] = useState("")

  const menuRef = useRef(null)
  const profileMenuRef = useRef(null)

  // Close menus on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpenId(null)
      }
      if (profileMenuRef.current && !profileMenuRef.current.contains(e.target)) {
        setShowProfileMenu(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const triggerToast = (msg) => {
    setToastMsg(msg)
    setTimeout(() => setToastMsg(""), 3000)
  }

  const handleShare = (e, conv) => {
    e.stopPropagation()
    setMenuOpenId(null)
    navigator.clipboard.writeText(`http://localhost:3000/c/${conv.id}`)
    triggerToast("🔗 Share link copied to clipboard!")
  }

  const handleRenameStart = (e, conv) => {
    e.stopPropagation()
    setMenuOpenId(null)
    setEditingId(conv.id)
    setEditTitle(conv.title)
  }

  const handleRenameSave = (convId) => {
    if (editTitle.trim()) {
      const conv = conversations.find(c => c.id === convId)
      if (conv) conv.title = editTitle.trim()
    }
    setEditingId(null)
  }

  const handlePin = (e, convId) => {
    e.stopPropagation()
    setMenuOpenId(null)
    setPinnedIds(prev =>
      prev.includes(convId) ? prev.filter(id => id !== convId) : [...prev, convId]
    )
  }

  const handleArchive = (e, convId) => {
    e.stopPropagation()
    setMenuOpenId(null)
    setArchivedIds(prev =>
      prev.includes(convId) ? prev.filter(id => id !== convId) : [...prev, convId]
    )
    triggerToast("🗃️ Conversation archived")
  }

  const activeConvs = conversations.filter(c => !archivedIds.includes(c.id))
  const pinnedConvs = activeConvs.filter(c => pinnedIds.includes(c.id))
  const recentConvs = activeConvs.filter(c => !pinnedIds.includes(c.id))

  const renderConvItem = (conv) => {
    const isActive = conv.id === currentConversationId
    const isHovered = hoveredId === conv.id
    const isMenuOpen = menuOpenId === conv.id
    const isEditing = editingId === conv.id
    const isPinned = pinnedIds.includes(conv.id)

    return (
      <div key={conv.id} style={{ position: "relative" }}>
        <div
          onClick={() => onSelectConversation(conv.id)}
          onMouseEnter={() => setHoveredId(conv.id)}
          onMouseLeave={() => setHoveredId(null)}
          style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "8px 10px", borderRadius: 7, cursor: "pointer",
            marginBottom: 2, transition: "background 0.1s",
            background: isActive ? "var(--accent-dim)" : (isHovered || isMenuOpen) ? "rgba(255,255,255,0.05)" : "transparent",
            borderLeft: isActive ? "2px solid var(--accent)" : "2px solid transparent"
          }}>
          <span style={{ color: isActive ? "var(--accent)" : "var(--text-muted)", flexShrink: 0 }}>
            {isPinned ? <PinIcon /> : <ChatIcon />}
          </span>

          {isEditing ? (
            <input
              type="text"
              value={editTitle}
              autoFocus
              onClick={e => e.stopPropagation()}
              onChange={e => setEditTitle(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter") handleRenameSave(conv.id)
                if (e.key === "Escape") setEditingId(null)
              }}
              onBlur={() => handleRenameSave(conv.id)}
              style={{
                flex: 1, background: "#111", border: "1px solid var(--accent)",
                color: "#fff", padding: "2px 6px", borderRadius: 4, fontSize: 13, outline: "none"
              }}
            />
          ) : (
            <span style={{
              flex: 1, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              color: isActive ? "var(--text-primary)" : "var(--text-secondary)"
            }}>{conv.title}</span>
          )}

          {(isHovered || isMenuOpen) && !isEditing && (
            <button
              onClick={e => {
                e.stopPropagation()
                setMenuOpenId(isMenuOpen ? null : conv.id)
              }}
              style={{
                background: "none", border: "none", cursor: "pointer",
                color: "var(--text-muted)", padding: "2px 4px", borderRadius: 4, display: "flex"
              }}
              onMouseEnter={e => e.currentTarget.style.color = "#fff"}
              onMouseLeave={e => e.currentTarget.style.color = "var(--text-muted)"}
            >
              <MoreIcon />
            </button>
          )}
        </div>

        {/* ChatGPT Style Context Menu Dropdown */}
        {isMenuOpen && (
          <div ref={menuRef} style={{
            position: "absolute", right: 8, top: 32, zIndex: 100,
            background: "#212121", border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 10, padding: "6px", width: 160,
            boxShadow: "0 10px 30px rgba(0,0,0,0.5)", display: "flex", flexDirection: "column", gap: 2
          }}>
            <button onClick={e => handleShare(e, conv)} style={contextItemStyle}>
              <ShareIcon /> Share
            </button>
            <button onClick={e => handleRenameStart(e, conv)} style={contextItemStyle}>
              <EditIcon /> Rename
            </button>
            <button onClick={e => handlePin(e, conv.id)} style={contextItemStyle}>
              <PinIcon /> {isPinned ? "Unpin chat" : "Pin chat"}
            </button>
            <button onClick={e => handleArchive(e, conv.id)} style={contextItemStyle}>
              <ArchiveIcon /> Archive
            </button>
            <div style={{ height: 1, background: "rgba(255,255,255,0.08)", margin: "4px 0" }} />
            <button onClick={e => { e.stopPropagation(); setMenuOpenId(null); onDeleteConversation(conv.id) }} style={{ ...contextItemStyle, color: "#ef4444" }}>
              <TrashIcon /> Delete
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <>
      {/* Toast Notification */}
      {toastMsg && (
        <div style={{
          position: "fixed", top: 20, right: 20, zIndex: 1000,
          background: "#10b981", color: "#fff", padding: "10px 16px",
          borderRadius: 8, fontSize: 13, fontWeight: 600, boxShadow: "0 4px 14px rgba(0,0,0,0.3)"
        }}>
          {toastMsg}
        </div>
      )}

      {/* Profile Modal */}
      {showProfileModal && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 1000, background: "rgba(0,0,0,0.7)",
          display: "flex", alignItems: "center", justifyContent: "center"
        }} onClick={() => setShowProfileModal(false)}>
          <div style={{
            background: "#212121", border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 14, padding: 24, width: 340, boxShadow: "0 20px 40px rgba(0,0,0,0.6)"
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: "#fff" }}>User Profile</h3>
              <button onClick={() => setShowProfileModal(false)} style={{ background: "none", border: "none", color: "#aaa", cursor: "pointer" }}>✕</button>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
              <div style={{ width: 48, height: 48, borderRadius: "50%", background: "#10a37f", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 700, color: "#fff" }}>
                {(user?.full_name || user?.email || "U")[0].toUpperCase()}
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15, color: "#fff" }}>{user?.full_name || "Medical Practitioner"}</div>
                <div style={{ fontSize: 12, color: "#888" }}>{user?.email || "user@mindcare.ai"}</div>
              </div>
            </div>
            <div style={{ fontSize: 13, color: "#aaa", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 12 }}>
              <div style={{ marginBottom: 6 }}><strong>Role:</strong> Psychiatric Knowledge Assistant</div>
              <div style={{ marginBottom: 6 }}><strong>Access Tier:</strong> Clinical Enterprise Master</div>
              <div><strong>Status:</strong> Active Session ✅</div>
            </div>
          </div>
        </div>
      )}

      {/* Archived Chats Modal */}
      {showArchiveModal && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 1000, background: "rgba(0,0,0,0.7)",
          display: "flex", alignItems: "center", justifyContent: "center"
        }} onClick={() => setShowArchiveModal(false)}>
          <div style={{
            background: "#212121", border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 14, padding: 24, width: 380, maxHeight: "80vh", overflowY: "auto", boxShadow: "0 20px 40px rgba(0,0,0,0.6)"
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: "#fff" }}>🗃️ Archived Chats ({archivedIds.length})</h3>
              <button onClick={() => setShowArchiveModal(false)} style={{ background: "none", border: "none", color: "#aaa", cursor: "pointer" }}>✕</button>
            </div>
            {archivedIds.length === 0 ? (
              <div style={{ padding: "20px 0", textAlign: "center", color: "#888", fontSize: 13 }}>
                No archived conversations.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {conversations.filter(c => archivedIds.includes(c.id)).map(conv => (
                  <div key={conv.id} style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "10px 12px", background: "rgba(255,255,255,0.04)", borderRadius: 8, border: "1px solid rgba(255,255,255,0.08)"
                  }}>
                    <span style={{ fontSize: 13, color: "#eee", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {conv.title}
                    </span>
                    <button
                      onClick={e => handleArchive(e, conv.id)}
                      style={{
                        background: "var(--accent-dim)", border: "1px solid var(--accent)",
                        color: "var(--accent)", padding: "4px 10px", borderRadius: 6, fontSize: 12, cursor: "pointer"
                      }}
                    >
                      Unarchive
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Mobile overlay */}
      <div className={`sidebar-overlay${isOpen ? " open" : ""}`} onClick={onClose} />

      <aside className={`sidebar ${isOpen ? "open" : "collapsed"}`}>
        {/* Brand + Close button */}
        <div style={{ padding: "20px 18px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: "var(--accent)", display: "flex",
            alignItems: "center", justifyContent: "center", flexShrink: 0
          }}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.44l-1.01-1.01A2.5 2.5 0 0 1 4.5 16V9A2.5 2.5 0 0 1 7 6.5" />
              <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.44l1.01-1.01A2.5 2.5 0 0 0 19.5 16V9A2.5 2.5 0 0 0 17 6.5" />
            </svg>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)", letterSpacing: "-0.2px" }}>MindCare AI</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 1 }}>Psychiatric Knowledge · Phase 2</div>
          </div>
          <button onClick={onClose} className="sidebar-close-btn" title="Close sidebar">
            <CloseIcon />
          </button>
        </div>

        {/* Action Buttons */}
        <div style={{ padding: "12px 12px 8px", display: "flex", flexDirection: "column", gap: 8 }}>
          <button onClick={onNewChat} style={{
            width: "100%", padding: "9px 14px",
            background: "var(--accent-dim)", border: "1px solid var(--border-accent)",
            borderRadius: 8, color: "var(--accent)", fontSize: 13, fontWeight: 500,
            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
            gap: 7, transition: "all 0.15s", fontFamily: "inherit"
          }}
            onMouseEnter={e => { e.currentTarget.style.background = "var(--accent)"; e.currentTarget.style.color = "white" }}
            onMouseLeave={e => { e.currentTarget.style.background = "var(--accent-dim)"; e.currentTarget.style.color = "var(--accent)" }}
          >
            <PlusIcon /> New Conversation
          </button>

          <button onClick={() => { onOpenDocuments && onOpenDocuments() }} style={{
            width: "100%", padding: "9px 14px",
            background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)",
            borderRadius: 8, color: "var(--text-primary)", fontSize: 13, fontWeight: 500,
            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
            gap: 7, transition: "all 0.15s", fontFamily: "inherit"
          }}
            onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.08)" }}
            onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.03)" }}
          >
            <BookIcon /> Knowledge Base
          </button>

          <button onClick={() => { onOpenMemory && onOpenMemory() }} style={{
            width: "100%", padding: "9px 14px",
            background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)",
            borderRadius: 8, color: "var(--text-primary)", fontSize: 13, fontWeight: 500,
            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
            gap: 7, transition: "all 0.15s", fontFamily: "inherit"
          }}
            onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.08)" }}
            onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.03)" }}
          >
            🧠 Memory Management
          </button>
        </div>

        {/* History Lists */}
        <div style={{ flex: 1, overflowY: "auto", padding: "4px 8px" }}>
          {activeConvs.length === 0 ? (
            <div style={{ padding: "20px 12px", textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
              No previous conversations
            </div>
          ) : (
            <>
              {/* Pinned Section */}
              {pinnedConvs.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ padding: "6px 8px", fontSize: 11, fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                    📌 Pinned
                  </div>
                  {pinnedConvs.map(renderConvItem)}
                </div>
              )}

              {/* Recent Section */}
              {recentConvs.length > 0 && (
                <div>
                  <div style={{ padding: "6px 8px", fontSize: 11, fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                    Recent
                  </div>
                  {recentConvs.map(renderConvItem)}
                </div>
              )}
            </>
          )}
        </div>

        {/* User Profile / Footer */}
        <div style={{ borderTop: "1px solid var(--border)", padding: "12px 12px", position: "relative" }}>
          {isGuest ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "8px 10px", borderRadius: 8,
                background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.25)",
                fontSize: 12, color: "#10b981"
              }}>
                <span style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 500 }}>
                  <span className="pulse-dot" style={{ width: 7, height: 7, borderRadius: "50%", background: "#10b981" }} />
                  <span>Clinical Assistant</span>
                </span>
                <span style={{ fontSize: 11, opacity: 0.85 }}>Free Access</span>
              </div>
              <button
                onClick={() => openAuthModal("manual")}
                style={{
                  width: "100%", padding: "7px 12px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.12)",
                  background: "rgba(255,255,255,0.05)",
                  color: "var(--text-secondary)", fontSize: 12, fontWeight: 500, cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                  transition: "all 0.15s"
                }}
                onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.1)"; e.currentTarget.style.color = "#fff" }}
                onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.05)"; e.currentTarget.style.color = "var(--text-secondary)" }}
              >
                <span>👤</span> Account (Optional)
              </button>
            </div>
          ) : (
            <>
              {/* User Profile Dropdown Menu */}
              {showProfileMenu && (
                <div ref={profileMenuRef} style={{
                  position: "absolute", bottom: 60, left: 12, right: 12, zIndex: 100,
                  background: "#212121", border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 10, padding: 6, boxShadow: "0 10px 30px rgba(0,0,0,0.6)",
                  display: "flex", flexDirection: "column", gap: 2
                }}>
                  <button onClick={() => { setShowProfileMenu(false); setShowProfileModal(true) }} style={contextItemStyle}>
                    <UserIcon /> Profile
                  </button>
                  <button onClick={() => { setShowProfileMenu(false); setShowArchiveModal(true) }} style={contextItemStyle}>
                    <ArchiveIcon /> Archived Chats ({archivedIds.length})
                  </button>
                  <div style={{ height: 1, background: "rgba(255,255,255,0.08)", margin: "4px 0" }} />
                  <button onClick={() => { setShowProfileMenu(false); logout() }} style={{ ...contextItemStyle, color: "#ef4444" }}>
                    <LogoutIcon /> Log out
                  </button>
                </div>
              )}

              <div
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "8px 10px", borderRadius: 8, cursor: "pointer",
                  background: "var(--bg-primary)", transition: "background 0.15s"
                }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.06)"}
                onMouseLeave={e => e.currentTarget.style.background = "var(--bg-primary)"}
              >
                <div style={{
                  width: 30, height: 30, borderRadius: 7,
                  background: "var(--bg-tertiary)", display: "flex",
                  alignItems: "center", justifyContent: "center", flexShrink: 0,
                  fontSize: 12, fontWeight: 600, color: "var(--accent)"
                }}>
                  {(user?.full_name || user?.email || "U")[0].toUpperCase()}
                </div>
                <div style={{ flex: 1, overflow: "hidden" }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {user?.full_name || "User"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {user?.email}
                  </div>
                </div>
                <MoreIcon />
              </div>
            </>
          )}
        </div>
      </aside>
    </>
  )
}

const contextItemStyle = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  width: "100%",
  padding: "8px 10px",
  background: "none",
  border: "none",
  color: "#ececec",
  fontSize: 13,
  borderRadius: 6,
  cursor: "pointer",
  textAlign: "left",
  fontFamily: "inherit",
  transition: "background 0.12s"
}
