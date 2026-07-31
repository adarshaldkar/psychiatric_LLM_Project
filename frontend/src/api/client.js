import axios from "axios"
import { useStore } from "../store/useStore"

const API_BASE_URL = `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api`

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json"
  }
})

// Attach JWT token to every request
apiClient.interceptors.request.use((config) => {
  const token = useStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-logout on 401 (expired/invalid token) anywhere in the app
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const { logout } = useStore.getState()
      logout()   // clears localStorage + resets store → shows AuthModal
    }
    return Promise.reject(error)
  }
)
