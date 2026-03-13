import { useMemo } from 'react'

const EMOTIONS = [
  { key: 'frustration', label: 'Frustration', color: 'var(--emo-frustration)', glow: 'rgba(239,68,68,0.4)' },
  { key: 'stress',      label: 'Stress',      color: 'var(--emo-stress)',       glow: 'rgba(249,115,22,0.4)' },
  { key: 'confusion',   label: 'Confusion',   color: 'var(--emo-confusion)',    glow: 'rgba(245,158,11,0.4)' },
  { key: 'joy',         label: 'Joy',         color: 'var(--emo-joy)',          glow: 'rgba(34,197,94,0.4)' },
]

function ArcMeter({ value = 0, color, glow, label }) {
  const r = 38
  const cx = 50
  const cy = 54
  const startAngle = 200
  const endAngle = 340
  const totalAngle = endAngle - startAngle

  const degToRad = (d) => (d * Math.PI) / 180

  const arcPath = (angleDeg) => {
    const angle = degToRad(angleDeg)
    const x = cx + r * Math.cos(angle)
    const y = cy + r * Math.sin(angle)
    return { x, y }
  }

  const clampedValue = Math.min(1, Math.max(0, value))
  const fillAngle = startAngle + totalAngle * clampedValue

  const bgStart = arcPath(startAngle)
  const bgEnd = arcPath(endAngle)
  const fgEnd = arcPath(fillAngle)
  const largeArcBg = totalAngle > 180 ? 1 : 0
  const largeArcFg = totalAngle * clampedValue > 180 ? 1 : 0

  const bgPath = `M ${bgStart.x} ${bgStart.y} A ${r} ${r} 0 ${largeArcBg} 1 ${bgEnd.x} ${bgEnd.y}`
  const fgPath = clampedValue > 0
    ? `M ${bgStart.x} ${bgStart.y} A ${r} ${r} 0 ${largeArcFg} 1 ${fgEnd.x} ${fgEnd.y}`
    : null

  const pct = Math.round(clampedValue * 100)

  return (
    <div style={styles.arcWrapper}>
      <svg width="100" height="80" viewBox="0 0 100 80" style={{ overflow: 'visible' }}>
        {/* Background track */}
        <path
          d={bgPath}
          fill="none"
          stroke="rgba(255,255,255,0.07)"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Filled arc */}
        {fgPath && (
          <path
            d={fgPath}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            style={{
              filter: `drop-shadow(0 0 8px ${glow})`,
              transition: 'all 0.6s cubic-bezier(0.34,1.56,0.64,1)',
            }}
          />
        )}
        {/* Center value */}
        <text
          x={cx}
          y={cy - 8}
          textAnchor="middle"
          fill={pct > 0 ? color : 'var(--text-muted)'}
          fontSize="14"
          fontWeight="700"
          fontFamily="Space Grotesk, sans-serif"
          style={{ transition: 'all 0.4s' }}
        >
          {pct}%
        </text>
      </svg>
      <span style={{ ...styles.arcLabel, color: pct > 50 ? color : 'var(--text-secondary)' }}>
        {label}
      </span>
    </div>
  )
}

export default function EmotionMeter({ scores = {} }) {
  const dominant = useMemo(() => {
    const entries = EMOTIONS.map(e => ({ ...e, score: scores[e.key] || 0 }))
    return entries.sort((a, b) => b.score - a.score)[0]
  }, [scores])

  const hasData = EMOTIONS.some(e => scores[e.key] > 0)

  return (
    <div style={styles.container}>
      <div style={styles.titleRow}>
        <span className="section-label">Emotion Analysis</span>
        {hasData && dominant.score > 0 && (
          <span className={`badge badge-${
            dominant.key === 'frustration' ? 'red' :
            dominant.key === 'stress' ? 'orange' :
            dominant.key === 'confusion' ? 'amber' : 'green'
          }`}>
            {dominant.label}
          </span>
        )}
      </div>

      <div style={styles.grid}>
        {EMOTIONS.map(e => (
          <ArcMeter
            key={e.key}
            value={scores[e.key] || 0}
            color={e.color}
            glow={e.glow}
            label={e.label}
          />
        ))}
      </div>

      {!hasData && (
        <div style={styles.empty}>
          <span>Awaiting voice input…</span>
        </div>
      )}
    </div>
  )
}

const styles = {
  container: {
    padding: '20px',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px 0',
    justifyItems: 'center',
  },
  arcWrapper: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 2,
  },
  arcLabel: {
    fontSize: 11,
    fontWeight: 500,
    transition: 'color 0.4s',
  },
  empty: {
    color: 'var(--text-muted)',
    fontSize: 12,
    textAlign: 'center',
    padding: '8px 0',
  },
}
