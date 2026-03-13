import { useState } from 'react'
import { Phone, LayoutDashboard } from 'lucide-react'
import Widget from './components/Widget'
import Dashboard from './components/Dashboard'

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

      {/* View content */}
      <div style={styles.content}>
        {view === 'widget' && <Widget />}
        {view === 'dashboard' && <Dashboard />}
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
    borderRadius: 14,
    background: 'rgba(10,10,18,0.9)',
    border: '1px solid var(--border)',
    backdropFilter: 'blur(20px)',
  },
  content: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
  },
}
