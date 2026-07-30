import { useStore } from "../store/useStore"

export const sendMessageStream = async (content, conversationId, onStatus, onToken, onCitations, onDone, onError) => {
  const token = useStore.getState().token

  try {
    const response = await fetch("http://localhost:8000/api/chat/message", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        content: content
      })
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
          console.warn("Parse error:", e, line)
        }
      }
    }
  } catch (err) {
    onError && onError(err.message || "Failed to communicate with AI service")
  }
}
