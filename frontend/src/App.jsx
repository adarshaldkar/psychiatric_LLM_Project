import React, { useEffect, useState } from "react"
import { useStore } from "./store/useStore"
import Sidebar from "./components/Sidebar"
import ChatWindow from "./components/ChatWindow"
import InputBar from "./components/InputBar"
import AuthModal from "./components/AuthModal"
import DocumentPanel from "./components/DocumentPanel"
import MemoryPanel from "./components/MemoryPanel"
import { getConversations, createConversation, getConversationDetail, deleteConversation } from "./api/conversations"
import { sendMessageStream } from "./api/chat"

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [documentsOpen, setDocumentsOpen] = useState(false)
  const [memoryOpen, setMemoryOpen] = useState(false)

  const {
    token,
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
    removeConversation
  } = useStore()

  useEffect(() => {
    if (token) {
      getConversations()
        .then((data) => {
          setConversations(data)
          if (data.length > 0 && !currentConversationId) {
            handleSelectConversation(data[0].id)
          }
        })
        .catch((err) => console.error("Failed to load conversations:", err))
    }
  }, [token])

  const handleSelectConversation = async (convId) => {
    setCurrentConversationId(convId)
    try {
      const detail = await getConversationDetail(convId)
      setMessages(detail.messages || [])
    } catch (err) {
      console.error("Failed to load conversation details:", err)
    }
  }

  const handleNewChat = async () => {
    try {
      const newConv = await createConversation("New Conversation")
      addConversation(newConv)
      setCurrentConversationId(newConv.id)
      setMessages([])
    } catch (err) {
      console.error("Failed to create conversation:", err)
    }
  }

  const handleDeleteConversation = async (convId) => {
    try {
      await deleteConversation(convId)
      removeConversation(convId)
      if (currentConversationId === convId) {
        setCurrentConversationId(null)
        setMessages([])
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

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "var(--bg-primary)" }}>
      {!token && <AuthModal />}

      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onOpenDocuments={() => setDocumentsOpen(true)}
        onOpenMemory={() => setMemoryOpen(true)}
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
        <InputBar onSend={handleSendMessage} onOpenDocuments={() => setDocumentsOpen(true)} />
      </main>
    </div>
  )
}
