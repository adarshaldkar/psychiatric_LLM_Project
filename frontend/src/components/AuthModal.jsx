import React, { useState } from "react"
import { loginUser, registerUser } from "../api/auth"
import { useStore } from "../store/useStore"

export default function AuthModal() {
  const [mode, setMode] = useState("login")   // "login" | "register"
  const [form, setForm] = useState({ full_name: "", email: "", password: "" })
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const { setAuth } = useStore()

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
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 50,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: "rgba(10,12,18,0.92)", backdropFilter: "blur(12px)"
    }}>
      <div style={{
        width: "100%", maxWidth: 400,
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
        borderRadius: 16, padding: "40px 36px",
        boxShadow: "0 24px 64px rgba(0,0,0,0.5)"
      }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 12, margin: "0 auto 16px",
            background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center"
          }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.44l-1.01-1.01A2.5 2.5 0 0 1 4.5 16V9A2.5 2.5 0 0 1 7 6.5" />
              <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.44l1.01-1.01A2.5 2.5 0 0 0 19.5 16V9A2.5 2.5 0 0 0 17 6.5" />
            </svg>
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", letterSpacing: "-0.3px" }}>
            MindCare AI
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 6 }}>
            Psychiatric & Mental Health Knowledge Assistant
          </p>
        </div>

        {/* Tab switcher */}
        <div style={{
          display: "flex", background: "var(--bg-primary)",
          borderRadius: 8, padding: 3, marginBottom: 24, gap: 3
        }}>
          {["login", "register"].map(m => (
            <button key={m} onClick={() => { setMode(m); setError("") }} style={{
              flex: 1, padding: "8px 0", borderRadius: 6, border: "none",
              fontSize: 13, fontWeight: 500, cursor: "pointer",
              transition: "all 0.15s",
              background: mode === m ? "var(--bg-secondary)" : "transparent",
              color: mode === m ? "var(--text-primary)" : "var(--text-secondary)",
              boxShadow: mode === m ? "0 1px 4px rgba(0,0,0,0.3)" : "none"
            }}>
              {m === "login" ? "Sign In" : "Register"}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.25)",
            borderRadius: 8, padding: "10px 14px", marginBottom: 16,
            fontSize: 13, color: "var(--danger)"
          }}>{error}</div>
        )}

        {/* Form */}
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {mode === "register" && (
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Full Name</label>
              <input
                type="text" placeholder="Your name" value={form.full_name}
                onChange={e => update("full_name", e.target.value)}
                required={mode === "register"}
                style={inputStyle}
              />
            </div>
          )}
          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Email</label>
            <input
              type="email" placeholder="you@example.com" value={form.email}
              onChange={e => update("email", e.target.value)} required
              style={inputStyle}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Password</label>
            <input
              type="password" placeholder="••••••••" value={form.password}
              onChange={e => update("password", e.target.value)} required
              style={inputStyle}
            />
          </div>
          <button type="submit" disabled={loading} style={{
            width: "100%", padding: "11px 0", marginTop: 8,
            background: loading ? "var(--bg-tertiary)" : "var(--accent)",
            color: "white", border: "none", borderRadius: 8,
            fontSize: 14, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
            transition: "background 0.15s", letterSpacing: "0.1px"
          }}>
            {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: 12, color: "var(--text-muted)", marginTop: 20 }}>
          By signing in you agree this is an educational AI tool, not medical advice.
        </p>
      </div>
    </div>
  )
}

const inputStyle = {
  width: "100%", padding: "10px 12px",
  background: "var(--bg-primary)", border: "1px solid var(--border)",
  borderRadius: 8, fontSize: 13, color: "var(--text-primary)",
  outline: "none", transition: "border 0.15s",
  fontFamily: "inherit"
}
