import { Package, MapPin, CheckCircle2, AlertTriangle, XCircle, Clock } from 'lucide-react'

const STATUS_CONFIG = {
  pending:          { icon: Clock,         color: 'var(--text-muted)',     badge: 'badge-violet', label: 'Pending' },
  in_transit:       { icon: MapPin,        color: 'var(--accent-blue)',    badge: 'badge-blue',   label: 'In Transit' },
  out_for_delivery: { icon: Package,       color: 'var(--accent-teal)',    badge: 'badge-blue',   label: 'Out for Delivery' },
  delivered:        { icon: CheckCircle2,  color: 'var(--accent-green)',   badge: 'badge-green',  label: 'Delivered' },
  failed:           { icon: XCircle,       color: 'var(--accent-red)',     badge: 'badge-red',    label: 'Failed' },
  damaged:          { icon: AlertTriangle, color: 'var(--accent-orange)',  badge: 'badge-orange', label: 'Damaged' },
  returned:         { icon: XCircle,       color: 'var(--accent-amber)',   badge: 'badge-amber',  label: 'Returned' },
}

function ShipmentCard({ shipment, isNew }) {
  const cfg = STATUS_CONFIG[shipment.status] || STATUS_CONFIG.pending
  const Icon = cfg.icon

  return (
    <div
      style={{
        ...styles.card,
        animation: isNew ? 'status-pop 0.4s ease forwards' : 'none',
        borderColor: isNew ? cfg.color : undefined,
      }}
      className="glass-card card-3d"
    >
      <div style={styles.cardTop}>
        <div style={styles.trackingRow}>
          <Icon size={14} color={cfg.color} />
          <span style={{ color: cfg.color, fontWeight: 700, fontSize: 13, fontFamily: 'monospace' }}>
            {shipment.tracking_number || shipment.shipment_id || '—'}
          </span>
        </div>
        <span className={`badge ${cfg.badge}`}>{cfg.label}</span>
      </div>

      {(shipment.destination || shipment.recipient_name) && (
        <div style={styles.cardMeta}>
          {shipment.destination && (
            <div style={styles.metaRow}>
              <MapPin size={11} color="var(--text-muted)" />
              <span className="truncate" style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                {shipment.destination}
              </span>
            </div>
          )}
          {shipment.recipient_name && (
            <div style={styles.metaRow}>
              <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>→ {shipment.recipient_name}</span>
            </div>
          )}
        </div>
      )}

      {shipment.priority_flag && (
        <div style={styles.priorityTag}>
          <AlertTriangle size={10} color="var(--accent-amber)" />
          <span style={{ color: 'var(--accent-amber)', fontSize: 10, fontWeight: 600 }}>PRIORITY</span>
        </div>
      )}
    </div>
  )
}

export default function ShipmentTracker({ shipments = {}, newIds = new Set() }) {
  const entries = Object.values(shipments)

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span className="section-label">Shipment Tracker</span>
        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{entries.length} active</span>
      </div>

      <div style={styles.list}>
        {entries.length === 0 && (
          <div style={styles.empty}>
            <Package size={20} color="var(--text-muted)" style={{ opacity: 0.4 }} />
            <span>No shipment updates yet</span>
          </div>
        )}
        {entries.map((s) => (
          <ShipmentCard
            key={s.shipment_id || s.tracking_number}
            shipment={s}
            isNew={newIds.has(s.shipment_id)}
          />
        ))}
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
  list: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    paddingRight: 4,
  },
  card: {
    padding: '12px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  cardTop: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  trackingRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  cardMeta: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  metaRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
  },
  priorityTag: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    marginTop: 2,
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
    padding: '24px 0',
    color: 'var(--text-muted)',
    fontSize: 12,
  },
}
