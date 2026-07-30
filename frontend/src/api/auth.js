import { apiClient } from "./client"

export const loginUser = async (email, password) => {
  const response = await apiClient.post("/auth/login", { email, password })
  return response.data
}

export const registerUser = async (email, password, fullName) => {
  const response = await apiClient.post("/auth/register", { email, password, full_name: fullName })
  return response.data
}

export const getCurrentUser = async () => {
  const response = await apiClient.get("/auth/me")
  return response.data
}
