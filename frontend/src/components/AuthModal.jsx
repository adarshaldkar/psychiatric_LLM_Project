import React, { useState } from "react"
import { loginUser, registerUser } from "../api/auth"
import { useStore } from "../store/useStore"

export default function AuthModal() {
  const [mode, setMode] = useState("register")   // Default to register for trial conversion
  const [form, setForm] = useState({ full_name: "", email: "", password: "" })
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const {
    isGuest,
    guestTrialExpired,
    authModalReason,
    setAuth,
    closeAuthModal
  } = useStore()

  const isTrialLock = guestTrialExpired || authModalReason === "trial_expired"
  const canClose = !isTrialLock

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

        {/* Optional close button if not locked */}
        {canClose && (
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
        )}

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

          {isTrialLock ? (
            <>
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                padding: "4px 12px", borderRadius: 20,
                background: "rgba(245, 158, 11, 0.12)", border: "1px solid rgba(245, 158, 11, 0.3)",
                color: "#f59e0b", fontSize: 12, fontWeight: 600, marginBottom: 10
              }}>
                <span>⏳</span> Free Guest Preview Limit Reached
              </div>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.3px", margin: "4px 0" }}>
                Save Your Chat & Keep Going
              </h2>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4, lineHeight: 1.45 }}>
                Sign in or create a free account to continue your consultation and save your complete conversation history.
              </p>
            </>
          ) : authModalReason === "feature_locked" ? (
            <>
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                padding: "4px 12px", borderRadius: 20,
                background: "rgba(59, 130, 246, 0.12)", border: "1px solid rgba(59, 130, 246, 0.3)",
                color: "#3b82f6", fontSize: 12, fontWeight: 600, marginBottom: 10
              }}>
                <span>🔒</span> Account Feature
              </div>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.3px", margin: "4px 0" }}>
                Unlock Full Clinical Toolkit
              </h2>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
                Document RAG ingestion and longitudinal clinical memory require an authenticated account.
              </p>
            </>
          ) : (
            <>
              <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.3px" }}>
                MindCare AI
              </h1>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
                Psychiatric & Mental Health Clinical Knowledge Assistant
              </p>
            </>
          )}
        </div>

        {/* Benefits list on trial lock */}
        {isTrialLock && (
          <div style={{
            background: "var(--bg-primary)",
            borderRadius: 12, padding: "12px 16px",
            marginBottom: 20, border: "1px solid var(--border)",
            display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 12, color: "var(--text-secondary)"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ color: "#10b981", fontWeight: "bold" }}>✓</span> Unlimited AI Chats
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ color: "#10b981", fontWeight: "bold" }}>✓</span> Save Full History
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ color: "#10b981", fontWeight: "bold" }}>✓</span> Medical Doc RAG
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ color: "#10b981", fontWeight: "bold" }}>✓</span> 100% Free Access
            </div>
          </div>
        )}

        {/* Tab switcher */}
        <div style={{
          display: "flex", background: "var(--bg-primary)",
          borderRadius: 10, padding: 4, marginBottom: 20, gap: 4
        }}>
          {["register", "login"].map(m => (
            <button key={m} onClick={() => { setMode(m); setError("") }} style={{
              flex: 1, padding: "9px 0", borderRadius: 8, border: "none",
              fontSize: 13, fontWeight: 600, cursor: "pointer",
              transition: "all 0.2s",
              background: mode === m ? "var(--bg-secondary)" : "transparent",
              color: mode === m ? "var(--text-primary)" : "var(--text-secondary)",
              boxShadow: mode === m ? "0 2px 8px rgba(0,0,0,0.35)" : "none"
            }}>
              {m === "register" ? "Create Free Account" : "Sign In"}
            </button>
          ))}
        </div>

        {/* Error message */}
        {error && (
          <div style={{
            background: "rgba(248,113,113,0.12)", border: "1px solid rgba(248,113,113,0.3)",
            borderRadius: 10, padding: "10px 14px", marginBottom: 16,
            fontSize: 13, color: "var(--danger)", display: "flex", alignItems: "center", gap: 8
          }}>
            <span>⚠️</span> {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {mode === "register" && (
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
                Full Name
              </label>
              <input
                type="text" placeholder="Dr. Jane Doe / Alex Smith" value={form.full_name}
                onChange={e => update("full_name", e.target.value)}
                required={mode === "register"}
                style={inputStyle}
              />
            </div>
          )}
          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
              Email Address
            </label>
            <input
              type="email" placeholder="you@example.com" value={form.email}
              onChange={e => update("email", e.target.value)} required
              style={inputStyle}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
              Password
            </label>
            <input
              type="password" placeholder="At least 8 characters" value={form.password}
              onChange={e => update("password", e.target.value)} required
              style={inputStyle}
            />
          </div>
          <button type="submit" disabled={loading} style={{
            width: "100%", padding: "12px 0", marginTop: 8,
            background: loading ? "var(--bg-tertiary)" : "linear-gradient(135deg, var(--accent) 0%, #2563eb 100%)",
            color: "white", border: "none", borderRadius: 10,
            fontSize: 14, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
            transition: "opacity 0.2s, transform 0.1s", letterSpacing: "0.2px",
            boxShadow: "0 4px 14px rgba(37, 99, 235, 0.3)"
          }}>
            {loading ? "Authenticating..." : mode === "register" ? "Create Free Account" : "Sign In"}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: 11, color: "var(--text-muted)", marginTop: 20, lineHeight: 1.4 }}>
          MindCare AI is an educational clinical assistant tool. Not a substitute for emergency medical care.
        </p>
      </div>
    </div>
  )
}

const inputStyle = {
  width: "100%", padding: "10px 14px",
  background: "var(--bg-primary)", border: "1px solid var(--border)",
  borderRadius: 10, fontSize: 13, color: "var(--text-primary)",
  outline: "none", transition: "border 0.15s, box-shadow 0.15s",
  fontFamily: "inherit", boxSizing: "border-box"
}
