import React, { useState } from "react"
import { loginUser, registerUser } from "../api/auth"
import { useStore } from "../store/useStore"

export default function AuthModal() {
  const [mode, setMode] = useState("register")
  const [form, setForm] = useState({ full_name: "", email: "", password: "" })
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const {
    setAuth,
    closeAuthModal
  } = useStore()

  const update = (k, v) => setForm(p => ({ ...p, [k]: v }))

  const submit = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const data = mode === "register"
        ? await registerUser(form.email, form.password, form.full_name)
        : await loginUser(form.email, form.password)
      setAuth(data.access_token, data.user)
      closeAuthModal()
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 100,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: "rgba(8, 10, 16, 0.88)", backdropFilter: "blur(14px)",
      padding: "20px",
      animation: "fadeIn 0.2s ease-out"
    }}>
      <div style={{
        width: "100%", maxWidth: 440,
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
        borderRadius: 20, padding: "36px 32px",
        boxShadow: "0 28px 72px rgba(0, 0, 0, 0.65)",
        position: "relative",
        overflow: "hidden"
      }}>
        {/* Top ambient glow banner */}
        <div style={{
          position: "absolute", top: 0, left: "15%", right: "15%", height: 3,
          background: "linear-gradient(90deg, transparent, var(--accent), transparent)",
          borderRadius: "0 0 8px 8px"
        }} />

        {/* Close button */}
        <button
          onClick={closeAuthModal}
          aria-label="Close"
          style={{
            position: "absolute", top: 18, right: 18,
            background: "transparent", border: "none",
            color: "var(--text-muted)", cursor: "pointer",
            fontSize: 18, padding: 6, borderRadius: 8,
            display: "flex", alignItems: "center", justifyContent: "center"
          }}
        >
          ✕
        </button>

        {/* Logo & Header */}
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div style={{
            width: 52, height: 52, borderRadius: 14, margin: "0 auto 14px",
            background: "linear-gradient(135deg, var(--accent) 0%, #2563eb 100%)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 8px 24px rgba(37, 99, 235, 0.35)"
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.44l-1.01-1.01A2.5 2.5 0 0 1 4.5 16V9A2.5 2.5 0 0 1 7 6.5" />
              <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.44l1.01-1.01A2.5 2.5 0 0 0 19.5 16V9A2.5 2.5 0 0 0 17 6.5" />
            </svg>
          </div>

          <h2 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 6px", color: "var(--text-primary)", letterSpacing: "-0.5px" }}>
            {mode === "register" ? "Create Free Account" : "Welcome Back"}
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
            {mode === "register"
              ? "Save your chat history, custom documents, and clinical memories."
              : "Sign in to access your saved consultations and documents."}
          </p>
        </div>

        {/* Tab switcher */}
        <div style={{
          display: "flex", background: "var(--bg-primary)",
          borderRadius: 10, padding: 4, marginBottom: 24,
          border: "1px solid var(--border)"
        }}>
          <button
            type="button"
            onClick={() => { setMode("register"); setError("") }}
            style={{
              flex: 1, padding: "8px 0", borderRadius: 7, border: "none",
              fontSize: 13, fontWeight: 600, cursor: "pointer",
              transition: "all 0.15s ease",
              background: mode === "register" ? "var(--bg-card)" : "transparent",
              color: mode === "register" ? "var(--text-primary)" : "var(--text-muted)",
              boxShadow: mode === "register" ? "0 2px 8px rgba(0,0,0,0.3)" : "none"
            }}
          >
            Create Free Account
          </button>
          <button
            type="button"
            onClick={() => { setMode("login"); setError("") }}
            style={{
              flex: 1, padding: "8px 0", borderRadius: 7, border: "none",
              fontSize: 13, fontWeight: 600, cursor: "pointer",
              transition: "all 0.15s ease",
              background: mode === "login" ? "var(--bg-card)" : "transparent",
              color: mode === "login" ? "var(--text-primary)" : "var(--text-muted)",
              boxShadow: mode === "login" ? "0 2px 8px rgba(0,0,0,0.3)" : "none"
            }}
          >
            Sign In
          </button>
        </div>

        {/* Error message banner */}
        {error && (
          <div style={{
            padding: "10px 14px", borderRadius: 8, marginBottom: 18,
            background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.25)",
            color: "#f87171", fontSize: 13, display: "flex", alignItems: "center", gap: 8
          }}>
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {mode === "register" && (
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>
                Full Name
              </label>
              <input
                type="text"
                placeholder="Dr. Jane Doe / Alex Smith"
                value={form.full_name}
                onChange={e => update("full_name", e.target.value)}
                style={inputStyle}
              />
            </div>
          )}

          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>
              Email Address
            </label>
            <input
              type="email"
              required
              placeholder="you@example.com"
              value={form.email}
              onChange={e => update("email", e.target.value)}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>
              Password
            </label>
            <input
              type="password"
              required
              placeholder="At least 8 characters"
              value={form.password}
              onChange={e => update("password", e.target.value)}
              style={inputStyle}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%", padding: "12px", borderRadius: 10, border: "none",
              background: "linear-gradient(135deg, var(--accent) 0%, #2563eb 100%)",
              color: "#fff", fontSize: 14, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
              marginTop: 4, opacity: loading ? 0.7 : 1,
              boxShadow: "0 4px 16px rgba(37, 99, 235, 0.4)",
              transition: "transform 0.1s ease"
            }}
          >
            {loading ? "Processing..." : mode === "register" ? "Create Free Account" : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  )
}

const inputStyle = {
  width: "100%",
  padding: "10px 14px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg-primary)",
  color: "var(--text-primary)",
  fontSize: 14,
  outline: "none",
  boxSizing: "border-box",
  fontFamily: "inherit"
}
