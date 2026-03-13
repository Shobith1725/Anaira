import { useRef, useEffect } from 'react'
import { Bot, User } from 'lucide-react'

export default function Transcript({ messages = [] }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span className="section-label">Live Transcript</span>
        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{messages.length} turns</span>
      </div>

      <div style={styles.feed}>
        {messages.length === 0 && (
          <div style={styles.empty}>
            <div style={styles.emptyDots}>
              {[0, 1, 2].map(i => (
                <span key={i} style={{ ...styles.emptyDot, animationDelay: `${i * 0.2}s` }} />
              ))}
            </div>
            <span>Waiting for voice…</span>
          </div>
        )}

        {messages.map((msg, i) => {
          const isDriver = msg.speaker === 'driver'
          return (
            <div
              key={i}
              style={{
                ...styles.bubble,
                flexDirection: isDriver ? 'row' : 'row-reverse',
                animation: 'fadeInUp 0.3s ease forwards',
              }}
            >
              <div style={{
                ...styles.avatar,
                background: isDriver
                  ? 'rgba(79,143,255,0.15)'
                  : 'rgba(139,92,246,0.15)',
                border: `1px solid ${isDriver ? 'rgba(79,143,255,0.3)' : 'rgba(139,92,246,0.3)'}`,
              }}>
                {isDriver
                  ? <User size={14} color="var(--accent-blue)" />
                  : <Bot size={14} color="var(--accent-violet)" />
                }
              </div>
              <div style={{
                ...styles.text,
                background: isDriver
                  ? 'rgba(79,143,255,0.08)'
                  : 'rgba(139,92,246,0.08)',
                border: `1px solid ${isDriver ? 'rgba(79,143,255,0.15)' : 'rgba(139,92,246,0.15)'}`,
                borderRadius: isDriver ? '4px 14px 14px 14px' : '14px 4px 14px 14px',
              }}>
                <div style={styles.speakerLabel}>
                  <span style={{ color: isDriver ? 'var(--accent-blue)' : 'var(--accent-violet)', fontWeight: 600, fontSize: 10 }}>
                    {isDriver ? (msg.language ? `Driver · ${msg.language.toUpperCase()}` : 'Driver') : 'ANAIRA'}
                  </span>
                </div>
                <p style={styles.textContent}>{msg.text}</p>
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

const styles = {
  container: {
    padding: '20px',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexShrink: 0,
  },
  feed: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    paddingRight: 4,
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 12,
    padding: '24px 0',
    color: 'var(--text-muted)',
    fontSize: 12,
  },
  emptyDots: {
    display: 'flex',
    gap: 6,
  },
  emptyDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: 'var(--text-muted)',
    display: 'inline-block',
    animation: 'dot-pulse 1.4s ease-in-out infinite',
  },
  bubble: {
    display: 'flex',
    gap: 10,
    alignItems: 'flex-start',
  },
  avatar: {
    width: 28,
    height: 28,
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    marginTop: 2,
  },
  text: {
    maxWidth: '80%',
    padding: '10px 14px',
  },
  speakerLabel: {
    marginBottom: 4,
  },
  textContent: {
    color: 'var(--text-primary)',
    fontSize: 13,
    lineHeight: 1.5,
  },
}
