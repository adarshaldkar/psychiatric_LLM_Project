import React, { useEffect, useState, useCallback, useRef } from "react"
import { Routes, Route, Navigate, useNavigate, useParams } from "react-router-dom"
import { useStore } from "./store/useStore"
import Sidebar from "./components/Sidebar"
import ChatWindow from "./components/ChatWindow"
import InputBar from "./components/InputBar"
import AuthModal from "./components/AuthModal"
import DocumentPanel from "./components/DocumentPanel"
import MemoryPanel from "./components/MemoryPanel"
import { getConversations, createConversation, getConversationDetail, deleteConversation } from "./api/conversations"
import { sendMessageStream } from "./api/chat"
import { createGuestSession } from "./api/auth"

// ── Inner layout component (receives route params) ───────────────────────────
function ChatLayout() {
  const { convId } = useParams()   // from /chat/:convId
  const navigate = useNavigate()

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [documentsOpen, setDocumentsOpen] = useState(false)
  const [memoryOpen, setMemoryOpen] = useState(false)

  const {
    token,
    showAuthModal,
    setConversations,
    currentConversationId,
    setCurrentConversationId,
    setMessages,
    addMessage,
    updateLastMessageContent,
    updateLastMessageCitations,
    isStreaming,
    setIsStreaming,
    setStreamingStatus,
    addConversation,
    removeConversation,
    setGuestAuth,
    openAuthModal,
  } = useStore()

  // 1. Silent Background Session Auto-Provisioning (ensures instant chat access with no login modal)
  useEffect(() => {
    if (!token) {
      createGuestSession()
        .then((data) => {
          setGuestAuth(data.access_token, data.user)
        })
        .catch((err) => {
          console.warn("Could not start session automatically:", err)
        })
    }
  }, [token, setGuestAuth])

  // 3. Load conversations list on mount / login
  useEffect(() => {
    if (!token) return
    getConversations()
      .then((data) => {
        setConversations(data)
        // If a specific conv is in the URL, verify it exists in user's conversations
        if (convId && data.some(c => c.id === convId)) {
          handleSelectConversation(convId)
        } else if (data.length > 0) {
          // Default: open most recent conversation
          handleSelectConversation(data[0].id)
          navigate(`/chat/${data[0].id}`, { replace: true })
        } else {
          setCurrentConversationId(null)
          setMessages([])
          if (convId) navigate("/chat", { replace: true })
        }
      })
      .catch((err) => console.error("Failed to load conversations:", err))
  }, [token])

  // 4. If convId URL param changes (browser back/forward), load it
  useEffect(() => {
    if (convId && token && convId !== currentConversationId) {
      handleSelectConversation(convId)
    }
  }, [convId])

  const handleSelectConversation = useCallback(async (selectedId) => {
    if (!selectedId) return
    setCurrentConversationId(selectedId)
    try {
      const detail = await getConversationDetail(selectedId)
      setMessages(detail.messages || [])
      navigate(`/chat/${selectedId}`, { replace: false })
    } catch (err) {
      console.warn("Conversation not accessible or expired, opening fresh chat:", err)
      setCurrentConversationId(null)
      setMessages([])
      navigate("/chat", { replace: true })
    }
  }, [navigate, setCurrentConversationId, setMessages])

  const handleNewChat = async () => {
    try {
      const newConv = await createConversation("New Conversation")
      addConversation(newConv)
      setCurrentConversationId(newConv.id)
      setMessages([])
      navigate(`/chat/${newConv.id}`)
    } catch (err) {
      console.error("Failed to create conversation:", err)
    }
  }

  const handleDeleteConversation = async (id) => {
    try {
      await deleteConversation(id)
      removeConversation(id)
      if (currentConversationId === id) {
        setCurrentConversationId(null)
        setMessages([])
        navigate("/chat", { replace: true })
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err)
    }
  }

  const handleSendMessage = async (text) => {
    if (!text.trim() || isStreaming) return

    let activeConvId = currentConversationId
    if (!activeConvId) {
      try {
        const newConv = await createConversation(text.slice(0, 30))
        addConversation(newConv)
        setCurrentConversationId(newConv.id)
        activeConvId = newConv.id
        navigate(`/chat/${newConv.id}`)
      } catch (err) {
        console.error("Failed to create conversation:", err)
        return
      }
    }

    addMessage({ role: "user", content: text })
    addMessage({ role: "assistant", content: "" })

    setIsStreaming(true)
    setStreamingStatus("Thinking...")

    let accumulated = ""

    sendMessageStream(
      text,
      activeConvId,
      (statusText) => setStreamingStatus(statusText),
      (tokenText) => {
        accumulated += tokenText
        updateLastMessageContent(accumulated)
      },
      (citationsData) => {
        updateLastMessageCitations(citationsData)
      },
      () => {
        updateLastMessageContent(accumulated)
        setIsStreaming(false)
        setStreamingStatus("")
        getConversations().then(setConversations).catch(() => {})
      },
      (errorText) => {
        setIsStreaming(false)
        setStreamingStatus("")
        updateLastMessageContent(`⚠️ ${errorText}`)
      }
    )
  }

  const handleOpenDocuments = () => {
    setDocumentsOpen(true)
  }

  const handleOpenMemory = () => {
    setMemoryOpen(true)
  }

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "var(--bg-primary)" }}>
      {/* Show AuthModal whenever requested or when trial has expired */}
      {showAuthModal && <AuthModal />}

      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onOpenDocuments={handleOpenDocuments}
        onOpenMemory={handleOpenMemory}
      />

      <DocumentPanel
        isOpen={documentsOpen}
        onClose={() => setDocumentsOpen(false)}
      />

      <MemoryPanel
        isOpen={memoryOpen}
        onClose={() => setMemoryOpen(false)}
      />

      <main style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden", minWidth: 0 }}>
        <ChatWindow
          onSendSuggestion={handleSendMessage}
          onOpenSidebar={() => setSidebarOpen(true)}
          onToggleSidebar={() => setSidebarOpen(prev => !prev)}
        />
        <InputBar onSend={handleSendMessage} onOpenDocuments={handleOpenDocuments} />
      </main>
    </div>
  )
}

// ── Root App with React Router routes ────────────────────────────────────────
export default function App() {
  return (
    <Routes>
      {/* Redirect root → /chat */}
      <Route path="/" element={<Navigate to="/chat" replace />} />

      {/* Main chat view — with optional conversation ID in URL */}
      <Route path="/chat" element={<ChatLayout />} />
      <Route path="/chat/:convId" element={<ChatLayout />} />

      {/* Catch-all: unknown paths redirect to /chat */}
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  )
}
