import { useState } from 'react'

const API_BASE = 'http://localhost:8000'

function ChatInterface() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const send = async () => {
    const question = input.trim()
    if (!question || loading) return

    setMessages(prev => [...prev, { role: 'user', text: question }])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      const data = await res.json()
      setMessages(prev => [
        ...prev,
        { role: 'assistant', text: data.answer, sources: data.sources },
      ])
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', text: 'Error: could not reach the backend.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', overflow: 'hidden' }}>
      <div style={{
        padding: '1rem',
        minHeight: '400px',
        background: '#f9fafb',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        overflowY: 'auto',
      }}>
        {messages.length === 0 && (
          <p style={{ color: '#9ca3af', fontSize: '0.95rem', margin: 0 }}>
            Ask a question about your ingested documents...
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth: '80%',
              padding: '0.6rem 0.9rem',
              borderRadius: '8px',
              background: msg.role === 'user' ? '#2563eb' : '#fff',
              color: msg.role === 'user' ? '#fff' : '#111',
              border: msg.role === 'assistant' ? '1px solid #e5e7eb' : 'none',
              fontSize: '0.9rem',
              lineHeight: '1.6',
            }}>
              <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{msg.text}</p>
              {msg.sources?.length > 0 && (
                <p style={{ margin: '0.4rem 0 0', fontSize: '0.75rem', color: '#6b7280' }}>
                  Sources: {msg.sources.join(', ')}
                </p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              padding: '0.6rem 0.9rem',
              borderRadius: '8px',
              background: '#fff',
              border: '1px solid #e5e7eb',
              color: '#9ca3af',
              fontSize: '0.9rem',
            }}>
              Thinking...
            </div>
          </div>
        )}
      </div>

      <div style={{
        display: 'flex',
        gap: '0.5rem',
        padding: '0.75rem',
        borderTop: '1px solid #e5e7eb',
        background: '#fff',
      }}>
        <input
          style={{
            flex: 1,
            padding: '0.5rem 0.75rem',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            fontSize: '0.95rem',
            outline: 'none',
          }}
          placeholder="Type your research question..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={loading}
        />
        <button
          style={{
            padding: '0.5rem 1.25rem',
            background: loading ? '#93c5fd' : '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 500,
          }}
          onClick={send}
          disabled={loading}
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  )
}

export default ChatInterface
