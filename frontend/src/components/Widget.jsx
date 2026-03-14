import { useState, useCallback, useRef, useEffect } from 'react'
import { Mic, Phone, PhoneOff, Wifi, WifiOff, AlertCircle } from 'lucide-react'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { useAudioPlayer } from '../hooks/useAudioPlayer'

// WebSocket via Vite proxy → backend on port 8000
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/voice`

const STATE = {
  IDLE: 'idle',
  CONNECTING: 'connecting',
  LIVE: 'live',
  ENDING: 'ending',
}

export default function Widget() {
  const [callState, setCallState] = useState(STATE.IDLE)
  const [sessionId, setSessionId] = useState(null)
  const [driverName, setDriverName] = useState(null)
  const [mode, setMode] = useState(null)
  const [statusMsg, setStatusMsg] = useState('')
  const [error, setError] = useState(null)

  const wsRef = useRef(null)
  const startTimeRef = useRef(null)
  const [elapsed, setElapsed] = useState(0)

  // Refs to recorder controls so audio player callbacks don't cause stale closures
  const pauseRecordingRef = useRef(null)
  const resumeRecordingRef = useRef(null)

  // ── Audio player with playback callbacks to pause/resume recorder ──
  const { playChunk, stop: stopPlayer } = useAudioPlayer({
    onPlaybackStart: () => {
      // Pause mic while ANAIRA is speaking (prevents feedback loop)
      pauseRecordingRef.current?.()
    },
    onPlaybackEnd: () => {
      // Resume mic after ANAIRA finishes speaking
      resumeRecordingRef.current?.()
    },
  })

  useEffect(() => {
    if (callState !== STATE.LIVE) { setElapsed(0); return }
    startTimeRef.current = Date.now()
    const t = setInterval(
      () => setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000)),
      1000
    )
    return () => clearInterval(t)
  }, [callState])

  const formatTime = (s) =>
    `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  const handleChunk = useCallback((buffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(buffer)
    }
  }, [])

  const {
    isRecording, startRecording, stopRecording, pauseRecording, resumeRecording, error: micError,
  } = useAudioRecorder({ onChunk: handleChunk })

  // Keep refs in sync so audio player callbacks always see latest
  useEffect(() => { pauseRecordingRef.current = pauseRecording }, [pauseRecording])
  useEffect(() => { resumeRecordingRef.current = resumeRecording }, [resumeRecording])

  // endCall via ref so handleMessage never gets stale closure
  const endCallRef = useRef(null)

  const endCall = useCallback(() => {
    setCallState(STATE.ENDING)
    stopRecording()
    stopPlayer()
    if (wsRef.current) {
      wsRef.current.close(1000, 'User ended call')
      wsRef.current = null
    }
    setSessionId(null)
    setDriverName(null)
    setMode(null)
    setStatusMsg('')
    setCallState(STATE.IDLE)
  }, [stopRecording, stopPlayer])

  useEffect(() => { endCallRef.current = endCall }, [endCall])

  const handleMessage = useCallback((evt) => {
    if (evt.data instanceof ArrayBuffer) {
      playChunk(evt.data)
      return
    }
    let msg
    try { msg = JSON.parse(evt.data) } catch { return }

    switch (msg.type) {
      case 'session':
        setSessionId(msg.session_id)
        setDriverName(msg.driver_name || msg.driver_id || 'Driver')
        setMode(msg.mode || 'logistics')
        setCallState(STATE.LIVE)
        setStatusMsg('Listening…')
        startRecording()
        break
      case 'transcript':
        if (msg.speaker === 'driver') {
          setStatusMsg(`You: ${msg.text}`)
        } else {
          setStatusMsg(`ANAIRA: ${msg.text}`)
        }
        break
      case 'response':
        setStatusMsg(`ANAIRA: ${msg.text}`)
        break
      case 'audio': {
        try {
          const binary = atob(msg.data)
          const bytes = new Uint8Array(binary.length)
          for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
          playChunk(bytes.buffer)
        } catch (e) { console.error('[Widget] audio decode error', e) }
        break
      }
      case 'tool_call':
        setStatusMsg(`⚙ ${msg.tool_name}…`)
        break
      case 'error':
        setError(msg.message || 'Pipeline error')
        endCallRef.current?.()
        break
      case 'done':
        setStatusMsg('Listening…')
        break
      default:
        break
    }
  }, [playChunk, startRecording])

  const startCall = useCallback(() => {
    setError(null)
    setCallState(STATE.CONNECTING)
    setStatusMsg('Connecting…')
    const ws = new WebSocket(WS_URL)
    ws.binaryType = 'arraybuffer'
    wsRef.current = ws
    ws.onopen = () => setStatusMsg('Waiting for session…')
    ws.onmessage = handleMessage
    ws.onerror = () => { setError('Connection failed. Is the backend running on port 8000?'); setCallState(STATE.IDLE) }
    ws.onclose = () => { if (wsRef.current !== null) { setCallState(STATE.IDLE); setStatusMsg('') } }
  }, [handleMessage])

  useEffect(() => {
    return () => { wsRef.current?.close(1000, 'Widget unmounted') }
  }, [])

  const isLive = callState === STATE.LIVE

  return (
    <div style={styles.wrapper}>
      <div style={styles.bgGlow} />
      <div style={styles.card} className="glass-card glow-violet card-3d">
        <div style={styles.header}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={styles.logo}>A</div>
            <div>
              <div style={styles.logoText}>ANAIRA</div>
              <div className="section-label">Voice Dispatch</div>
            </div>
          </div>
          <div style={styles.modeTag}>
            {mode ? <span className="badge badge-blue">{mode}</span> : <span className="badge badge-violet">v2.0</span>}
          </div>
        </div>

        <div style={styles.divider} className="divider" />

        <div style={styles.orbContainer}>
          {isLive && <div style={styles.pulseRing} />}
          {isLive && <div style={{ ...styles.pulseRing, animationDelay: '0.4s', opacity: 0.5 }} />}
          <div style={{
            ...styles.orb,
            animation: isLive ? 'orb-listening 2s ease-in-out infinite' : 'orb-breathe 3s ease-in-out infinite',
            background: isLive
              ? 'radial-gradient(circle at 35% 35%, #14d9c4, #0a9e93)'
              : 'radial-gradient(circle at 35% 35%, #6fa8ff, #3b6fd4)',
          }}>
            {isLive ? <Mic size={32} color="white" /> : <Phone size={32} color="white" />}
          </div>
        </div>

        <div style={styles.statusArea}>
          {callState === STATE.IDLE && <p style={styles.statusText}>Tap to start a voice session</p>}
          {callState === STATE.CONNECTING && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'center' }}>
              <div className="dot-live" /><p style={styles.statusText}>Connecting…</p>
            </div>
          )}
          {isLive && (
            <div style={{ textAlign: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'center', marginBottom: 4 }}>
                <div className="dot-live" />
                <span style={{ color: 'var(--accent-teal)', fontWeight: 600 }}>{driverName || 'Driver'}</span>
              </div>
              <div style={{ color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: 18, fontWeight: 600 }}>
                {formatTime(elapsed)}
              </div>
              {statusMsg && <p style={{ ...styles.statusText, fontSize: 12, marginTop: 6 }}>{statusMsg}</p>}
            </div>
          )}
          {callState === STATE.ENDING && <p style={styles.statusText}>Ending session…</p>}
        </div>

        {(error || micError) && (
          <div style={styles.errorBox}>
            <AlertCircle size={14} /><span>{error || micError}</span>
          </div>
        )}

        <div style={styles.controls}>
          {callState === STATE.IDLE && (
            <button id="start-call-btn" className="btn btn-primary" onClick={startCall} style={{ width: '100%', padding: '14px' }}>
              <Phone size={18} />Start Voice Session
            </button>
          )}
          {(callState === STATE.CONNECTING || callState === STATE.ENDING) && (
            <button className="btn btn-ghost" disabled style={{ width: '100%', padding: '14px' }}>
              <div className="dot-live" style={{ background: 'var(--accent-blue)' }} />
              {callState === STATE.CONNECTING ? 'Connecting…' : 'Ending…'}
            </button>
          )}
          {isLive && (
            <button id="end-call-btn" className="btn btn-danger" onClick={endCall} style={{ width: '100%', padding: '14px' }}>
              <PhoneOff size={18} />End Call
            </button>
          )}
        </div>

        <div style={styles.footer}>
          {isLive
            ? <><Wifi size={12} color="var(--accent-green)" /><span style={{ color: 'var(--accent-green)' }}>Live</span></>
            : <><WifiOff size={12} color="var(--text-muted)" /><span style={{ color: 'var(--text-muted)' }}>Offline</span></>
          }
        </div>
      </div>
    </div>
  )
}

const styles = {
  wrapper: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-deep)', position: 'relative', overflow: 'hidden' },
  bgGlow: { position: 'absolute', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(139,92,246,0.12) 0%, transparent 70%)', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', pointerEvents: 'none' },
  card: { width: 360, padding: '28px', position: 'relative', zIndex: 1 },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
  logo: { width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-violet))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'white' },
  logoText: { fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, color: 'var(--text-primary)', letterSpacing: '0.05em' },
  modeTag: { flexShrink: 0 },
  divider: { margin: '16px 0' },
  orbContainer: { display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', height: 160, margin: '8px 0' },
  pulseRing: { position: 'absolute', width: 120, height: 120, borderRadius: '50%', border: '2px solid rgba(20,217,196,0.5)', animation: 'pulse-ring 2s ease-out infinite' },
  orb: { width: 100, height: 100, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', position: 'relative', zIndex: 1 },
  statusArea: { textAlign: 'center', minHeight: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px 0' },
  statusText: { color: 'var(--text-secondary)', fontSize: 14 },
  errorBox: { display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderRadius: 10, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--accent-red)', fontSize: 13, marginBottom: 12 },
  controls: { marginTop: 8 },
  footer: { display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center', marginTop: 16, fontSize: 12 },
}