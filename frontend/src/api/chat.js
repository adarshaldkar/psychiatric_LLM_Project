/**
 * Centralized API client module.
 * 
 * Uses VITE_API_URL environment variable for the backend base URL.
 * Set in frontend/.env:  VITE_API_URL=http://localhost:8000
 * Default fallback:      http://localhost:8000  (dev only)
 */
import { useStore } from "../store/useStore"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

/**
 * Get Authorization headers using JWT token from Zustand store.
 */
export const getAuthHeaders = () => {
  const token = useStore.getState().token
  return {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
  }
}

/**
 * Generic authenticated fetch helper.
 * Throws on non-2xx responses with a descriptive error message.
 */
export const apiFetch = async (path, options = {}) => {
  const token = useStore.getState().token

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })

  if (!response.ok) {
    const errText = await response.text().catch(() => "Unknown error")
    throw new Error(`API Error ${response.status}: ${errText}`)
  }

  // Return null for 204 No Content
  if (response.status === 204) return null
  return response.json()
}

/**
 * Streaming chat message sender.
 * Calls POST /api/chat/message and consumes the SSE token stream.
 */
export const sendMessageStream = async (
  content,
  conversationId,
  onStatus,
  onToken,
  onCitations,
  onDone,
  onError
) => {
  const token = useStore.getState().token

  try {
    const response = await fetch(`${API_BASE}/api/chat/message`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        content: content,
      }),
    })

    if (!response.ok) {
      const errText = await response.text()
      onError && onError(`Server error (${response.status}): ${errText}`)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const payload = JSON.parse(line)
          if (payload.type === "status") {
            onStatus && onStatus(payload.text)
          } else if (payload.type === "token") {
            onToken && onToken(payload.text)
          } else if (payload.type === "citations") {
            onCitations && onCitations(payload.data)
          } else if (payload.type === "done") {
            onDone && onDone()
          }
        } catch (e) {
          console.warn("Stream parse error:", e, line)
        }
      }
    }
  } catch (err) {
    onError && onError(err.message || "Failed to communicate with AI service")
  }
}

/**
 * Transcribe audio using the faster-whisper backend STT endpoint.
 * @param {Blob} audioBlob - Raw audio blob from MediaRecorder
 * @param {string} ext - File extension: 'webm', 'wav', 'mp4', etc.
 * @returns {Promise<{transcript: string, language: string, duration_s: number}>}
 */
export const transcribeAudio = async (audioBlob, ext = "webm") => {
  const token = useStore.getState().token

  const formData = new FormData()
  formData.append("file", audioBlob, `recording.${ext}`)

  const response = await fetch(`${API_BASE}/api/voice/transcribe`, {
    method: "POST",
    headers: {
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      // NOTE: Do NOT set Content-Type here — browser sets multipart boundary automatically
    },
    body: formData,
  })

  if (!response.ok) {
    const errText = await response.text().catch(() => "Transcription failed")
    throw new Error(`STT Error ${response.status}: ${errText}`)
  }

  return response.json()
}

/**
 * Check if the faster-whisper backend is available.
 * @returns {Promise<{available: boolean, model: string, loaded: boolean}>}
 */
export const getVoiceStatus = async () => {
  try {
    const token = useStore.getState().token
    const response = await fetch(`${API_BASE}/api/voice/status`, {
      headers: { ...(token ? { "Authorization": `Bearer ${token}` } : {}) }
    })
    if (!response.ok) return { available: false }
    return response.json()
  } catch {
    return { available: false }
  }
}

export { API_BASE }
