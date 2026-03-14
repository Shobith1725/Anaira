import { useState, useEffect, useCallback, useRef } from 'react'
import { Wifi, WifiOff, LayoutDashboard } from 'lucide-react'
import EmotionMeter from './EmotionMeter'
import Transcript from './Transcript'
import ThoughtsPanel from './ThoughtsPanel'
import DriverPanel from './DriverPanel'
import ShipmentTracker from './ShipmentTracker'
import LogisticsEventFeed from './LogisticsEventFeed'

// Build WS URL from current host — proxied through Vite in dev
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_URL = `${WS_PROTOCOL}//${window.location.host}/ws/dashboard`


// Exponential backoff capped at 30s
function backoffMs(attempt) {
    return Math.min(1000 * Math.pow(2, attempt), 30_000)
}

export default function Dashboard() {
    const [wsStatus, setWsStatus] = useState('disconnected')
    const [emotionScores, setEmotionScores] = useState({})
    const [transcripts, setTranscripts] = useState([])
    const [thoughts, setThoughts] = useState([])
    const [session, setSession] = useState(null)
    const [shipments, setShipments] = useState({})
    const [newShipmentIds, setNewShipmentIds] = useState(new Set())
    const [events, setEvents] = useState([])

    const wsRef = useRef(null)
    const reconnectTimer = useRef(null)
    const reconnectAttempts = useRef(0)
    const intentionalClose = useRef(false)

    const handleEventRef = useRef(null)

    const handleEvent = useCallback((msg) => {
        switch (msg.type) {

            // ── Emotion from hume.py: {frustration, joy, stress, confusion} ──
            case 'emotion':
                // Backend sends flat keys, not nested under "scores"
                setEmotionScores({
                    frustration: msg.frustration ?? msg.scores?.frustration ?? 0,
                    joy: msg.joy ?? msg.scores?.joy ?? 0,
                    stress: msg.stress ?? msg.scores?.stress ?? 0,
                    confusion: msg.confusion ?? msg.scores?.confusion ?? 0,
                })
                break

            // ── emotion_spike from dashboard_ws.py broadcast ──────────────
            case 'emotion_spike':
                setEmotionScores(prev => ({
                    ...prev,
                    [msg.emotion]: Math.max(prev[msg.emotion] ?? 0, msg.score ?? 0),
                }))
                break

            // ── STT transcript from DeepGram ──────────────────────────────
            case 'transcript':
                setTranscripts(prev => [
                    ...prev.slice(-99),
                    {
                        speaker: msg.speaker ?? 'driver',
                        text: msg.text ?? '',
                        language: msg.language ?? 'en',
                        ts: Date.now(),
                    },
                ])
                // Use functional update to avoid closing over stale session
                if (msg.session_id) {
                    setSession(prev => prev ? prev : {
                        sessionId: msg.session_id,
                        driverName: msg.driver_name || 'Driver',
                        connectedAt: Date.now(),
                        mode: msg.mode || 'logistics',
                    })
                }
                break

            // ── LLM response text ─────────────────────────────────────────
            case 'response':
                setTranscripts(prev => [
                    ...prev.slice(-99),
                    { speaker: 'anaira', text: msg.text ?? '', ts: Date.now() },
                ])
                break

            // ── Session established (voice_pipeline.py sends this first) ──
            case 'session':
                setSession({
                    sessionId: msg.session_id,
                    driverId: msg.driver_id,
                    driverName: msg.driver_name || 'Driver',
                    connectedAt: Date.now(),
                    mode: msg.mode || 'logistics',
                })
                break

            // ── LLM thinking / chain-of-thought ──────────────────────────
            case 'thought':
                setThoughts(prev => [...prev.slice(-49), { text: msg.text, ts: Date.now() }])
                break

            // ── Tool call result from tools.py ────────────────────────────
            case 'tool_called':
            case 'tool_call':
                setEvents(prev => [...prev.slice(-99), {
                    type: 'tool_call',
                    tool_name: msg.tool_name,
                    result: msg.result,
                    ts: Date.now(),
                }])
                break

            // ── Shipment update from update_shipment_status / confirm_delivery ──
            case 'shipment_update':
            case 'delivery_confirmed': {
                const sid = msg.tracking_number ?? msg.shipment_id
                if (sid) {
                    setShipments(prev => ({ ...prev, [sid]: { ...prev[sid], ...msg } }))
                    setNewShipmentIds(prev => new Set([...prev, sid]))
                    setTimeout(() => setNewShipmentIds(prev => {
                        const next = new Set(prev)
                        next.delete(sid)
                        return next
                    }), 1500)
                }
                setEvents(prev => [...prev.slice(-99), { ...msg, ts: Date.now() }])
                break
            }

            // ── ETA update ────────────────────────────────────────────────
            case 'eta_updated': {
                const sid = msg.tracking_number
                if (sid) {
                    setShipments(prev => ({
                        ...prev,
                        [sid]: { ...prev[sid], eta: msg.new_eta, ...msg },
                    }))
                }
                setEvents(prev => [...prev.slice(-99), { ...msg, ts: Date.now() }])
                break
            }

            // ── Slot booked / incident / escalation ───────────────────────
            case 'slot_booked':
            case 'escalation':
            case 'report_incident':
                setEvents(prev => [...prev.slice(-99), { ...msg, ts: Date.now() }])
                break

            default:
                break
        }
    }, [])  // ✅ No deps — all state updates use functional form, no stale closures

    // Keep ref in sync so the stable connect callback can always see latest handleEvent
    useEffect(() => { handleEventRef.current = handleEvent }, [handleEvent])

    const connect = useCallback(() => {
        // Already open or connecting — skip
        if (
            wsRef.current?.readyState === WebSocket.OPEN ||
            wsRef.current?.readyState === WebSocket.CONNECTING
        ) return

        setWsStatus('connecting')
        intentionalClose.current = false

        const ws = new WebSocket(WS_URL)
        wsRef.current = ws

        ws.onopen = () => {
            console.log('[Dashboard WS] Connected')
            setWsStatus('connected')
            reconnectAttempts.current = 0
        }

        ws.onmessage = (evt) => {
            // Always dispatch through the ref so we never have a stale closure
            try { handleEventRef.current?.(JSON.parse(evt.data)) } catch { /* malformed frame */ }
        }

        ws.onerror = () => {
            console.warn('[Dashboard WS] Error (backend offline?)')
            setWsStatus('error')
        }

        ws.onclose = () => {
            wsRef.current = null
            if (intentionalClose.current) {
                setWsStatus('disconnected')
                return
            }
            setWsStatus('disconnected')
            const delay = backoffMs(reconnectAttempts.current)
            reconnectAttempts.current += 1
            console.log(`[Dashboard WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`)
            reconnectTimer.current = setTimeout(connect, delay)
        }
    }, [])  // ✅ Stable — no deps so this never causes useEffect to rerun

    // ✅ FIXED: was useCallback with no call (dead code) — now a proper useEffect
    useEffect(() => {
        connect()
        return () => {
            intentionalClose.current = true
            clearTimeout(reconnectTimer.current)
            wsRef.current?.close(1000, 'Dashboard unmounted')
        }
    }, [connect])

    const isConnected = wsStatus === 'connected'

    return (
        <div style={styles.wrapper}>
            <div style={styles.meshBg} />

            {/* Top bar */}
            <header style={styles.header}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={styles.logo}>A</div>
                    <div>
                        <div style={styles.logoText}>ANAIRA</div>
                        <div className="section-label">Warehouse Dashboard</div>
                    </div>
                </div>
                <div style={styles.headerRight}>
                    <div style={styles.connectionPill}>
                        {isConnected ? (
                            <>
                                <div className="dot-live" />
                                <Wifi size={13} color="var(--accent-green)" />
                                <span style={{ color: 'var(--accent-green)', fontSize: 12 }}>Live</span>
                            </>
                        ) : wsStatus === 'connecting' || wsStatus === 'disconnected' ? (
                            <>
                                <div className="dot-live" style={{ background: 'var(--accent-amber)' }} />
                                <span style={{ color: 'var(--accent-amber)', fontSize: 12 }}>
                                    {wsStatus === 'connecting' ? 'Connecting…' : 'Reconnecting…'}
                                </span>
                            </>
                        ) : (
                            <>
                                <WifiOff size={13} color="var(--text-muted)" />
                                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Error</span>
                            </>
                        )}
                    </div>
                    <LayoutDashboard size={16} color="var(--text-muted)" />
                </div>
            </header>

            {/* Grid layout */}
            <main style={styles.grid}>

                {/* Column 1: Driver + Emotion */}
                <div style={styles.col}>
                    <div style={{ ...styles.panel, flex: '0 0 auto' }} className="glass-card">
                        <DriverPanel session={session} />
                    </div>
                    <div style={{ ...styles.panel, flex: 1 }} className="glass-card">
                        <EmotionMeter scores={emotionScores} />
                    </div>
                </div>

                {/* Column 2: Transcript */}
                <div style={{ ...styles.panel, flex: 1 }} className="glass-card">
                    <Transcript messages={transcripts} />
                </div>

                {/* Column 3: Thoughts */}
                <div style={{ ...styles.panel, flex: 1 }} className="glass-card">
                    <ThoughtsPanel thoughts={thoughts} />
                </div>

                {/* Column 4: Shipments + Events */}
                <div style={styles.col}>
                    <div style={{ ...styles.panel, flex: 1 }} className="glass-card">
                        <ShipmentTracker shipments={shipments} newIds={newShipmentIds} />
                    </div>
                    <div style={{ ...styles.panel, flex: 1 }} className="glass-card">
                        <LogisticsEventFeed events={events} />
                    </div>
                </div>

            </main>
        </div>
    )
}

const styles = {
    wrapper: {
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-deep)',
        position: 'relative',
        overflow: 'hidden',
    },
    meshBg: {
        position: 'fixed',
        inset: 0,
        background: `
      radial-gradient(ellipse 60% 40% at 10% 20%, rgba(79,143,255,0.06) 0%, transparent 60%),
      radial-gradient(ellipse 50% 50% at 90% 80%, rgba(139,92,246,0.06) 0%, transparent 60%),
      radial-gradient(ellipse 40% 40% at 50% 50%, rgba(20,217,196,0.03) 0%, transparent 70%)
    `,
        pointerEvents: 'none',
        zIndex: 0,
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 24px',
        borderBottom: '1px solid var(--border)',
        background: 'rgba(5,5,8,0.8)',
        backdropFilter: 'blur(20px)',
        position: 'relative',
        zIndex: 10,
        flexShrink: 0,
    },
    logo: {
        width: 34,
        height: 34,
        borderRadius: 10,
        background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-violet))',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-display)',
        fontWeight: 700,
        fontSize: 16,
        color: 'white',
    },
    logoText: {
        fontFamily: 'var(--font-display)',
        fontWeight: 700,
        fontSize: 15,
        letterSpacing: '0.06em',
    },
    headerRight: {
        display: 'flex',
        alignItems: 'center',
        gap: 12,
    },
    connectionPill: {
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '5px 12px',
        borderRadius: 999,
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid var(--border)',
    },
    grid: {
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '260px 1fr 1fr 280px',
        gap: 16,
        padding: 20,
        minHeight: 0,
        position: 'relative',
        zIndex: 1,
    },
    col: {
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        minHeight: 0,
    },
    panel: {
        minHeight: 0,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
    },
}