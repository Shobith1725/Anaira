import { useRef, useEffect } from 'react'
import {
  CheckCircle2, AlertTriangle, Clock, Truck, RefreshCw, Shield, Navigation, PhoneCall
} from 'lucide-react'

const EVENT_CONFIG = {
  status_update:    { icon: RefreshCw,    color: 'var(--accent-blue)',   label: 'Status Update' },
  proof_of_delivery:{ icon: CheckCircle2, color: 'var(--accent-green)',  label: 'Delivered' },
  delay_reported:   { icon: Clock,        color: 'var(--accent-orange)', label: 'Delay Reported' },
  damage_report:    { icon: AlertTriangle,color: 'var(--accent-red)',    label: 'Damage Report' },
  reroute_request:  { icon: Navigation,   color: 'var(--accent-amber)',  label: 'Reroute Request' },
  escalation:       { icon: PhoneCall,    color: 'var(--accent-red)',    label: 'Escalation' },
  shipment_update:  { icon: Truck,        color: 'var(--accent-blue)',   label: 'Update' },
  default:          { icon: Shield,       color: 'var(--text-secondary)',label: 'Event' },
}

function EventItem({ event }) {
  const cfg = EVENT_CONFIG[event.event || event.type] || EVENT_CONFIG.default
  const Icon = cfg.icon
  const isUrgent = event.urgent === true || event.type === 'escalation'

  const now = new Date()
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <div
      style={{
        ...styles.item,
        borderLeftColor: isUrgent ? 'var(--accent-red)' : cfg.color,
        background: isUrgent ? 'rgba(239,68,68,0.05)' : 'rgba(255,255,255,0.02)',
        animation: 'event-slide 0.3s ease forwards',
      }}
    >
      <div style={{ ...styles.iconBox, background: `${cfg.color}18` }}>
        <Icon size={13} color={cfg.color} />
      </div>
      <div style={styles.itemContent}>
        <div style={styles.itemTop}>
          <span style={{ color: cfg.color, fontSize: 12, fontWeight: 600 }}>
            {cfg.label}
          </span>
          {isUrgent && (
            <span className="badge badge-red" style={{ fontSize: 9, padding: '1px 6px' }}>URGENT</span>
          )}
          <span style={styles.time}>{timeStr}</span>
        </div>
        {event.shipment_id && (
          <span style={styles.meta}>Shipment: {event.shipment_id}</span>
        )}
        {event.status && (
          <span style={styles.meta}>→ {event.status}</span>
        )}
        {event.reason && (
          <span style={styles.meta}>{event.reason}</span>
        )}
        {event.obstacle && (
          <span style={styles.meta}>{event.obstacle}</span>
        )}
        {event.description && (
          <span style={styles.meta}>{event.description}</span>
        )}
      </div>
    </div>
  )
}

export default function LogisticsEventFeed({ events = [] }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="section-label">Event Feed</span>
          {events.length > 0 && <div className="dot-live" />}
        </div>
        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{events.length} events</span>
      </div>

      <div style={styles.feed}>
        {events.length === 0 && (
          <div style={styles.empty}>
            <Truck size={20} color="var(--text-muted)" style={{ opacity: 0.4 }} />
            <span>Events will appear here during live sessions</span>
          </div>
        )}
        {events.map((e, i) => (
          <EventItem key={i} event={e} />
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
  item: {
    display: 'flex',
    gap: 10,
    padding: '10px 12px',
    borderRadius: 10,
    borderLeft: '3px solid transparent',
  },
  iconBox: {
    width: 28,
    height: 28,
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  itemContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
  },
  itemTop: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  time: {
    color: 'var(--text-muted)',
    fontSize: 10,
    marginLeft: 'auto',
    fontFamily: 'monospace',
  },
  meta: {
    color: 'var(--text-muted)',
    fontSize: 11,
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
    padding: '24px 0',
    color: 'var(--text-muted)',
    fontSize: 12,
    textAlign: 'center',
  },
}
