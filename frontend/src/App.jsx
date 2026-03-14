import { useState } from 'react'
import { Phone, LayoutDashboard } from 'lucide-react'
import Widget from './components/Widget'
import Dashboard from './components/Dashboard'

/**
 * ✅ FIXED: Previously used conditional rendering ({view === 'widget' && <Widget />})
 * which UNMOUNTS the Widget when switching to Dashboard, killing the voice WebSocket.
 * 
 * Now both components are ALWAYS mounted — we toggle visibility with CSS display.
 * This keeps the voice session alive while viewing the dashboard.
 */
export default function App() {
  const [view, setView] = useState('widget') // 'widget' | 'dashboard'

  return (
    <div style={styles.root}>
      {/* View switcher */}
      <nav style={styles.nav}>
        <button
          id="nav-widget"
          className={`btn ${view === 'widget' ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => setView('widget')}
          style={{ padding: '8px 16px', fontSize: 13 }}
        >
          <Phone size={14} />
          Driver Widget
        </button>
        <button
          id="nav-dashboard"
          className={`btn ${view === 'dashboard' ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => setView('dashboard')}
          style={{ padding: '8px 16px', fontSize: 13 }}
        >
          <LayoutDashboard size={14} />
          Dashboard
        </button>
      </nav>

      {/* Both views always mounted — toggle with display to keep WS connections alive */}
      <div style={{ ...styles.content, display: view === 'widget' ? 'flex' : 'none' }}>
        <Widget />
      </div>
      <div style={{ ...styles.content, display: view === 'dashboard' ? 'flex' : 'none' }}>
        <Dashboard />
      </div>
    </div>
  )
}

const styles = {
  root: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--bg-deep)',
  },
  nav: {
    position: 'fixed',
    top: 16,
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 100,
    display: 'flex',
    gap: 8,
    padding: '6px',
    borderRadius: 16,
    background: 'rgba(8,8,26,0.85)',
    border: '1px solid rgba(79,143,255,0.12)',
    backdropFilter: 'blur(24px) saturate(1.5)',
    boxShadow: `
      0 4px 20px rgba(0,0,0,0.5),
      0 8px 40px rgba(0,0,0,0.3),
      0 0 1px rgba(79,143,255,0.2),
      inset 0 1px 0 rgba(255,255,255,0.04)
    `,
  },
  content: {
    flex: 1,
    flexDirection: 'column',
  },
}
