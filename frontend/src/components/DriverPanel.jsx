import { useEffect, useState } from 'react'
import { Truck, Clock, User, Radio } from 'lucide-react'

export default function DriverPanel({ session = null }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!session?.connectedAt) { setElapsed(0); return }
    const t = setInterval(() => {
      setElapsed(Math.floor((Date.now() - session.connectedAt) / 1000))
    }, 1000)
    return () => clearInterval(t)
  }, [session?.connectedAt])

  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  if (!session) {
    return (
      <div style={styles.container}>
        <span className="section-label">Active Session</span>
        <div style={styles.empty}>
          <Radio size={20} color="var(--text-muted)" style={{ opacity: 0.4 }} />
          <span>No active session</span>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <div style={styles.headerRow}>
        <span className="section-label">Active Session</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div className="dot-live" />
          <span style={{ color: 'var(--accent-green)', fontSize: 11, fontWeight: 600 }}>LIVE</span>
        </div>
      </div>

      <div style={styles.card} className="glass-card">
        <div style={styles.row}>
          <div style={styles.iconBox}>
            <User size={16} color="var(--accent-blue)" />
          </div>
          <div>
            <div style={styles.label}>Driver</div>
            <div style={styles.value}>{session.driverName || 'Unknown'}</div>
          </div>
        </div>

        <div style={styles.divider} className="divider" />

        <div style={styles.row}>
          <div style={{ ...styles.iconBox, background: 'rgba(139,92,246,0.12)' }}>
            <Truck size={16} color="var(--accent-violet)" />
          </div>
          <div>
            <div style={styles.label}>Mode</div>
            <div>
              <span className={`badge ${session.mode === 'logistics' ? 'badge-blue' : 'badge-violet'}`}>
                {session.mode || 'logistics'}
              </span>
            </div>
          </div>
        </div>

        <div style={styles.divider} className="divider" />

        <div style={styles.row}>
          <div style={{ ...styles.iconBox, background: 'rgba(20,217,196,0.1)' }}>
            <Clock size={16} color="var(--accent-teal)" />
          </div>
          <div>
            <div style={styles.label}>Duration</div>
            <div style={{ ...styles.value, fontFamily: 'monospace', color: 'var(--accent-teal)' }}>
              {formatTime(elapsed)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const styles = {
  container: {
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: 14,
  },
  headerRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
    padding: '20px 0',
    color: 'var(--text-muted)',
    fontSize: 12,
  },
  card: {
    padding: '14px 16px',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  iconBox: {
    width: 34,
    height: 34,
    borderRadius: 10,
    background: 'rgba(79,143,255,0.12)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  label: {
    fontSize: 10,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    fontWeight: 600,
    marginBottom: 2,
  },
  value: {
    color: 'var(--text-primary)',
    fontWeight: 600,
    fontSize: 14,
  },
  divider: { margin: '10px 0' },
}
