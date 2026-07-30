import { apiClient } from "./client"

export const getConversations = async () => {
  const response = await apiClient.get("/conversations")
  return response.data
}

export const createConversation = async (title = "New Conversation") => {
  const response = await apiClient.post("/conversations", { title })
  return response.data
}

export const getConversationDetail = async (id) => {
  const response = await apiClient.get(`/conversations/${id}`)
  return response.data
}

export const deleteConversation = async (id) => {
  const response = await apiClient.delete(`/conversations/${id}`)
  return response.data
}
