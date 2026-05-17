import React, { useState, useRef } from 'react'

const CONF_GREEN  = '#16a34a'
const CONF_AMBER  = '#d97706'
const CONF_RED    = '#dc2626'
const CONF_BG_GREEN = '#f0fdf4'
const CONF_BG_AMBER = '#fffbeb'
const CONF_BG_RED   = '#fef2f2'

function confidenceColor(score) {
  if (score >= 0.7) return { text: CONF_GREEN, bg: CONF_BG_GREEN }
  if (score >= 0.4) return { text: CONF_AMBER, bg: CONF_BG_AMBER }
  return { text: CONF_RED, bg: CONF_BG_RED }
}

function BreakdownBar({ label, value }) {
  const pct = Math.round(value * 100)
  return (
    <div style={{ marginBottom: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#6b7280', marginBottom: 2 }}>
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <div style={{ background: '#e5e7eb', borderRadius: 3, height: 5 }}>
        <div style={{ width: `${pct}%`, background: '#6366f1', borderRadius: 3, height: 5, transition: 'width 0.3s' }} />
      </div>
    </div>
  )
}

function ResultCard({ result, rank }) {
  const [open, setOpen] = useState(false)
  const { text: cText, bg: cBg } = confidenceColor(result.score)
  const pct = Math.round(result.score * 100)

  return (
    <div style={{
      border: '1px solid #e5e7eb',
      borderRadius: 10,
      padding: '16px 18px',
      marginBottom: 12,
      background: '#fff',
      boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ flex: 1 }}>
          <span style={{ fontSize: 11, color: '#9ca3af', marginRight: 6 }}>#{rank}</span>
          <span style={{ fontWeight: 600, fontSize: 14, color: '#111827' }}>{result.title}</span>
        </div>
        <div style={{
          flexShrink: 0,
          background: cBg,
          color: cText,
          fontWeight: 700,
          fontSize: 15,
          padding: '4px 10px',
          borderRadius: 20,
          border: `1px solid ${cText}33`,
        }}>
          {pct}%
        </div>
      </div>

      <div style={{ marginTop: 6, fontSize: 12, color: '#6b7280', fontFamily: 'monospace' }}>
        {result.sku}
      </div>

      {result.highlights.length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {result.highlights.map(h => (
            <span key={h} style={{
              background: '#f3f4f6', color: '#374151',
              fontSize: 11, padding: '2px 6px', borderRadius: 4,
            }}>{h}</span>
          ))}
        </div>
      )}

      {result.notes.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {result.notes.map((n, i) => (
            <div key={i} style={{ fontSize: 11, color: '#92400e', fontStyle: 'italic' }}>⚠ {n}</div>
          ))}
        </div>
      )}

      <button
        onClick={() => setOpen(o => !o)}
        style={{
          marginTop: 10, fontSize: 11, color: '#6366f1', background: 'none',
          border: 'none', cursor: 'pointer', padding: 0,
        }}
      >
        {open ? '▲ Hide breakdown' : '▼ Show breakdown'}
      </button>

      {open && (
        <div style={{ marginTop: 8, padding: '10px 12px', background: '#f9fafb', borderRadius: 6 }}>
          <BreakdownBar label="Semantic"  value={result.breakdown.semantic} />
          <BreakdownBar label="Lexical"   value={result.breakdown.lexical} />
          <BreakdownBar label="Attribute" value={result.breakdown.attribute} />
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [query, setQuery]     = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const inputRef = useRef(null)

  async function handleSearch(e) {
    e.preventDefault()
    const q = query.trim()
    if (!q) return
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const res = await fetch(`/search?q=${encodeURIComponent(q)}&n=3`)
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const lowConfidence = results && results.length > 0 && results[0].score < 0.4

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '40px 20px' }}>

        <div style={{ marginBottom: 32, textAlign: 'center' }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: '#111827', margin: 0 }}>Catalog Match</h1>
          <p style={{ color: '#6b7280', marginTop: 6, fontSize: 14 }}>
            Describe what you need — we'll find the closest catalog items.
          </p>
        </div>

        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder='e.g. "SHCS M8 x 30mm zinc" or "3/8 hex nut stainless"'
            style={{
              flex: 1, padding: '10px 14px', fontSize: 14, border: '1px solid #d1d5db',
              borderRadius: 8, outline: 'none',
            }}
            onFocus={e => { e.target.style.borderColor = '#6366f1' }}
            onBlur={e  => { e.target.style.borderColor = '#d1d5db' }}
          />
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '10px 20px', background: loading ? '#a5b4fc' : '#6366f1',
              color: '#fff', border: 'none', borderRadius: 8,
              fontSize: 14, fontWeight: 600, cursor: loading ? 'default' : 'pointer',
            }}
          >
            {loading ? 'Searching…' : 'Search'}
          </button>
        </form>

        {error && (
          <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 8, padding: '12px 16px', marginBottom: 16, color: '#b91c1c', fontSize: 13 }}>
            {error}
          </div>
        )}

        {lowConfidence && (
          <div style={{ background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8, padding: '12px 16px', marginBottom: 16, color: '#92400e', fontSize: 13 }}>
            <strong>Low confidence</strong> — try adding thread size, material, or finish.
            <br />
            <span style={{ color: '#78350f' }}>Example: <em>"M8 socket head cap screw steel zinc 30mm"</em></span>
          </div>
        )}

        {results && results.length === 0 && (
          <div style={{ textAlign: 'center', color: '#6b7280', padding: '40px 0' }}>
            No results — catalog may not be loaded yet.
          </div>
        )}

        {results && results.map((r, i) => (
          <ResultCard key={r.id + i} result={r} rank={i + 1} />
        ))}

      </div>
    </div>
  )
}
