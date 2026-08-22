import { create } from "zustand"

const savedUser = JSON.parse(localStorage.getItem("mindcare_user") || "null")

export const useStore = create((set, get) => ({
  token: localStorage.getItem("mindcare_token") || null,
  user: savedUser,
  isGuest: Boolean(savedUser?.is_guest),
  guestMessageCount: parseInt(localStorage.getItem("mindcare_guest_msg_count") || "0", 10),
  guestTrialExpired: localStorage.getItem("mindcare_guest_expired") === "true",
  showAuthModal: false,
  authModalReason: "manual", // "manual" | "trial_expired" | "feature_locked"

  setAuth: (token, user) => {
    localStorage.setItem("mindcare_token", token)
    localStorage.setItem("mindcare_user", JSON.stringify(user))
    const isGuest = Boolean(user?.is_guest)
    if (!isGuest) {
      localStorage.removeItem("mindcare_guest_expired")
      localStorage.removeItem("mindcare_guest_msg_count")
    }
    set({
      token,
      user,
      isGuest,
      showAuthModal: false,
      guestTrialExpired: isGuest ? get().guestTrialExpired : false
    })
  },

  setGuestAuth: (token, user) => {
    localStorage.setItem("mindcare_token", token)
    localStorage.setItem("mindcare_user", JSON.stringify(user))
    set({
      token,
      user,
      isGuest: true,
      showAuthModal: false
    })
  },

  incrementGuestMessage: () => {
    const current = get().guestMessageCount + 1
    localStorage.setItem("mindcare_guest_msg_count", current.toString())
    set({ guestMessageCount: current })
    return current
  },

  expireGuestTrial: (reason = "trial_expired") => {
    localStorage.setItem("mindcare_guest_expired", "true")
    set({
      guestTrialExpired: true,
      showAuthModal: true,
      authModalReason: reason
    })
  },

  openAuthModal: (reason = "manual") => {
    set({ showAuthModal: true, authModalReason: reason })
  },

  closeAuthModal: () => {
    // Only allow closing if trial hasn't strictly expired or if user is already logged in
    if (!get().guestTrialExpired || !get().isGuest) {
      set({ showAuthModal: false })
    }
  },

  logout: () => {
    localStorage.removeItem("mindcare_token")
    localStorage.removeItem("mindcare_user")
    localStorage.removeItem("mindcare_guest_msg_count")
    localStorage.removeItem("mindcare_guest_expired")
    set({
      token: null,
      user: null,
      isGuest: false,
      guestMessageCount: 0,
      guestTrialExpired: false,
      showAuthModal: true,
      authModalReason: "manual",
      conversations: [],
      currentConversationId: null,
      messages: []
    })
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

