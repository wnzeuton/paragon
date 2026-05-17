import React, { useState } from 'react'

const SANS = "'Geist', sans-serif"
const MONO = "'IBM Plex Mono', monospace"

function scoreColor(score) {
  if (score >= 0.7) return '#4ade80'
  if (score >= 0.4) return '#facc15'
  return '#f87171'
}

function BreakdownPanel({ breakdown }) {
  const rows = [
    { label: 'semantic',  value: breakdown.semantic },
    { label: 'lexical',   value: breakdown.lexical },
    { label: 'attribute', value: breakdown.attribute },
  ]
  return (
    <div style={{ borderTop: '1px solid #1e1e2a', paddingTop: 14, marginTop: 12 }}>
      {rows.map(({ label, value }, i) => (
        <div key={label} style={{
          display: 'flex', alignItems: 'center', gap: 10,
          marginBottom: i < rows.length - 1 ? 8 : 0,
        }}>
          <span style={{ fontFamily: MONO, fontSize: 11, color: '#3a3a5a', width: 70, flexShrink: 0 }}>
            {label}
          </span>
          <div style={{ flex: 1, height: 3, background: '#1e1e2a', borderRadius: 2 }}>
            <div style={{
              width: `${Math.round(value * 100)}%`,
              height: '100%',
              background: 'rgba(91, 91, 246, 0.7)',
              borderRadius: 2,
            }} />
          </div>
          <span style={{ fontFamily: MONO, fontSize: 11, color: '#4a4a6a', width: 32, textAlign: 'right', flexShrink: 0 }}>
            {Math.round(value * 100)}%
          </span>
        </div>
      ))}
    </div>
  )
}

function ResultCard({ result, rank, isFirst }) {
  const [open, setOpen]       = useState(false)
  const [hovered, setHovered] = useState(false)

  const pct   = Math.round(result.score * 100)
  const color = scoreColor(result.score)

  return (
    <div
      onClick={() => setOpen(o => !o)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background:   isFirst ? '#14141f' : '#13131a',
        border:       `1px solid ${hovered ? '#2e2e42' : isFirst ? '#2a2a4a' : '#1e1e2a'}`,
        borderRadius: 12,
        padding:      '20px 22px',
        cursor:       'pointer',
        transition:   'border-color 0.15s',
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', flex: 1, minWidth: 0 }}>
          <span style={{ fontFamily: MONO, fontSize: 10, color: '#3a3a4a', paddingTop: 3, flexShrink: 0 }}>
            {String(rank).padStart(2, '0')}
          </span>
          <span style={{ fontFamily: SANS, fontSize: 15, fontWeight: 600, color: '#e8e8f5', lineHeight: 1.3 }}>
            {result.title}
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0, marginLeft: 16 }}>
          <span style={{ fontFamily: MONO, fontSize: 18, fontWeight: 500, color }}>
            {pct}%
          </span>
          <div style={{ width: 48, height: 3, background: '#1e1e2a', borderRadius: 2 }}>
            <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2 }} />
          </div>
        </div>
      </div>

      {/* SKU */}
      <div style={{ fontFamily: MONO, fontSize: 11, color: '#3a3a4a', letterSpacing: '0.05em', marginTop: 10 }}>
        {result.sku}
      </div>

      {/* Tags */}
      {result.highlights.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
          {result.highlights.map(h => (
            <span key={h} style={{
              fontFamily: MONO, fontSize: 11,
              background: '#1a1a26', border: '1px solid #2a2a3a',
              color: '#7070a0', borderRadius: 5, padding: '3px 8px',
            }}>
              {h}
            </span>
          ))}
        </div>
      )}

      {/* Warnings */}
      {result.notes.length > 0 && (
        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {result.notes.map((n, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: MONO, fontSize: 12, color: '#a07030' }}>
              <span>⚠</span><span>{n}</span>
            </div>
          ))}
        </div>
      )}

      {/* Breakdown toggle */}
      <button
        onClick={e => { e.stopPropagation(); setOpen(o => !o) }}
        onMouseEnter={e => e.currentTarget.style.color = '#6060a0'}
        onMouseLeave={e => e.currentTarget.style.color = '#3a3a5a'}
        style={{
          marginTop: 12, fontFamily: MONO, fontSize: 11, color: '#3a3a5a',
          background: 'none', border: 'none', cursor: 'pointer', padding: 0,
          transition: 'color 0.15s',
        }}
      >
        breakdown{' '}
        <span style={{
          display: 'inline-block',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s',
        }}>▾</span>
      </button>

      {open && <BreakdownPanel breakdown={result.breakdown} />}
    </div>
  )
}

export default function App() {
  const [query,   setQuery]   = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [btnDown, setBtnDown] = useState(false)

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
      setResults(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const lowConfidence = results && results.length > 0 && results[0].score < 0.4

  return (
    <div style={{ minHeight: '100vh', background: '#0d0d0f', fontFamily: SANS }}>
      <div style={{ maxWidth: 700, margin: '0 auto', borderRadius: 16, padding: '48px 40px 60px' }}>

        {/* Header */}
        <div style={{ marginBottom: 36 }}>
          <div style={{ fontFamily: SANS, fontSize: 11, fontWeight: 600, letterSpacing: '0.15em', textTransform: 'uppercase', color: '#4a4a5a', marginBottom: 6 }}>
            PARAGON
          </div>
          <div style={{ fontFamily: SANS, fontSize: 28, fontWeight: 700, color: '#f0f0f5' }}>
            Catalog Match
          </div>
        </div>

        {/* Search row */}
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10, marginBottom: 32 }}>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder='e.g. "SHCS M8 x 30mm zinc"'
            style={{
              flex: 1, background: '#16161c', border: '1px solid #2a2a38',
              borderRadius: 10, padding: '14px 18px', fontSize: 15,
              fontFamily: MONO, color: '#e0e0ec', outline: 'none', transition: 'border-color 0.15s',
            }}
            onFocus={e => e.target.style.borderColor = '#5b5bf6'}
            onBlur={e  => e.target.style.borderColor = '#2a2a38'}
          />
          <button
            type="submit"
            disabled={loading}
            onMouseDown={() => setBtnDown(true)}
            onMouseUp={() => setBtnDown(false)}
            onMouseLeave={() => setBtnDown(false)}
            onMouseEnter={e => { if (!loading) e.currentTarget.style.background = '#4545e0' }}
            style={{
              background: '#5b5bf6', border: 'none', borderRadius: 10,
              padding: '14px 24px', fontFamily: SANS, fontSize: 14, fontWeight: 600,
              color: '#fff', cursor: loading ? 'default' : 'pointer',
              transform: btnDown ? 'scale(0.98)' : 'scale(1)',
              transition: 'transform 0.1s, background 0.15s',
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? 'Searching…' : 'Search'}
          </button>
        </form>

        {/* Error */}
        {error && (
          <div style={{ fontFamily: MONO, fontSize: 12, color: '#f87171', marginBottom: 16 }}>
            ⚠ {error}
          </div>
        )}

        {/* Low confidence banner */}
        {lowConfidence && (
          <div style={{ fontFamily: MONO, fontSize: 12, color: '#a07030', marginBottom: 16 }}>
            ⚠ Low confidence — try adding thread size, material, or finish.
          </div>
        )}

        {/* Results */}
        {results && results.length > 0 && (
          <>
            <div style={{
              fontFamily: SANS, fontSize: 10, fontWeight: 600,
              letterSpacing: '0.18em', textTransform: 'uppercase',
              color: '#3a3a4a', marginBottom: 14,
            }}>
              TOP MATCHES
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {results.map((r, i) => (
                <ResultCard key={r.id + i} result={r} rank={i + 1} isFirst={i === 0} />
              ))}
            </div>
          </>
        )}

        {results && results.length === 0 && (
          <div style={{ fontFamily: MONO, fontSize: 12, color: '#3a3a4a', textAlign: 'center', padding: '40px 0' }}>
            No results — catalog may not be loaded.
          </div>
        )}

      </div>
    </div>
  )
}
