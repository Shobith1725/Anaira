import { useRef, useEffect } from 'react'
import { Brain, Zap } from 'lucide-react'

export default function ThoughtsPanel({ thoughts = [] }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [thoughts])

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Brain size={14} color="var(--accent-violet)" />
          <span className="section-label">AI Thoughts</span>
        </div>
        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{thoughts.length}</span>
      </div>

      <div style={styles.feed}>
        {thoughts.length === 0 && (
          <div style={styles.empty}>
            <Brain size={20} color="var(--text-muted)" style={{ opacity: 0.4 }} />
            <span>Reasoning will appear here during calls</span>
          </div>
        )}

        {thoughts.map((t, i) => (
          <div
            key={i}
            style={{
              ...styles.thought,
              animation: 'thought-in 0.35s ease forwards',
              animationDelay: '0ms',
            }}
          >
            <div style={styles.thoughtIcon}>
              <Zap size={11} color="var(--accent-violet)" />
            </div>
            <p style={styles.thoughtText}>{t.text}</p>
          </div>
        ))}
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
    gap: 8,
    paddingRight: 4,
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
    padding: '20px 0',
    color: 'var(--text-muted)',
    fontSize: 12,
    textAlign: 'center',
  },
  thought: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
    padding: '10px 12px',
    borderRadius: 10,
    background: 'rgba(139,92,246,0.06)',
    border: '1px solid rgba(139,92,246,0.12)',
  },
  thoughtIcon: {
    width: 20,
    height: 20,
    borderRadius: 6,
    background: 'rgba(139,92,246,0.15)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    marginTop: 1,
  },
  thoughtText: {
    color: 'var(--text-secondary)',
    fontSize: 12,
    lineHeight: 1.5,
    flex: 1,
  },
}
