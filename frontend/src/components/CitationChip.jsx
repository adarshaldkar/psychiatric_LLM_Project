import React from "react"

export default function CitationChip({ citation }) {
  const { document_name, chapter, section, page_number, page_range, is_global } = citation

  const locationParts = []
  if (chapter) locationParts.push(chapter)
  if (section) locationParts.push(section)
  if (page_range) locationParts.push(`pp.${page_range}`)
  else if (page_number) locationParts.push(`p.${page_number}`)

  const locationStr = locationParts.join(" · ")

  return (
    <div style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      background: "rgba(124, 106, 255, 0.08)",
      border: "1px solid rgba(124, 106, 255, 0.2)",
      borderRadius: 6,
      padding: "4px 8px",
      fontSize: 11,
      color: "var(--accent)",
      marginTop: 6,
      marginRight: 6,
      maxWidth: "100%",
      wordBreak: "break-word"
    }}>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>

      <span style={{ fontWeight: 600 }}>{document_name}</span>
      {locationStr && <span style={{ opacity: 0.8 }}>({locationStr})</span>}
      {is_global && (
        <span style={{
          background: "var(--accent)",
          color: "white",
          borderRadius: 3,
          padding: "1px 4px",
          fontSize: 9,
          fontWeight: 700,
          textTransform: "uppercase"
        }}>
          Global
        </span>
      )}
    </div>
  )
}
