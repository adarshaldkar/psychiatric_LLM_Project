import { create } from "zustand"

export const useStore = create((set, get) => ({
  token: localStorage.getItem("mindcare_token") || null,
  user: JSON.parse(localStorage.getItem("mindcare_user") || "null"),
  setAuth: (token, user) => {
    localStorage.setItem("mindcare_token", token)
    localStorage.setItem("mindcare_user", JSON.stringify(user))
    set({ token, user })
  },
  logout: () => {
    localStorage.removeItem("mindcare_token")
    localStorage.removeItem("mindcare_user")
    set({ token: null, user: null, conversations: [], currentConversationId: null, messages: [] })
  },

  conversations: [],
  currentConversationId: null,
  messages: [],
  isStreaming: false,
  streamingStatus: "",

  setConversations: (conversations) => set({ conversations }),
  setCurrentConversationId: (id) => set({ currentConversationId: id }),
  setMessages: (messages) => set({ messages }),

  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateLastMessageContent: (text) => set((state) => {
    const updated = [...state.messages]
    if (updated.length > 0 && updated[updated.length - 1].role === "assistant") {
      updated[updated.length - 1] = {
        ...updated[updated.length - 1],
        content: text
      }
    }
    return { messages: updated }
  }),

  updateLastMessageCitations: (citations) => set((state) => {
    const updated = [...state.messages]
    if (updated.length > 0 && updated[updated.length - 1].role === "assistant") {
      updated[updated.length - 1] = {
        ...updated[updated.length - 1],
        citations: citations,
        metadata_info: {
          ...(updated[updated.length - 1].metadata_info || {}),
          citations: citations
        }
      }
    }
    return { messages: updated }
  }),

  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setStreamingStatus: (streamingStatus) => set({ streamingStatus }),

  addConversation: (conv) => set((state) => ({
    conversations: [conv, ...state.conversations],
    currentConversationId: conv.id
  })),

  removeConversation: (id) => set((state) => ({
    conversations: state.conversations.filter(c => c.id !== id),
    currentConversationId: state.currentConversationId === id ? null : state.currentConversationId,
    messages: state.currentConversationId === id ? [] : state.messages
  }))
}))
