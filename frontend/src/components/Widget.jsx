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
      setStatusMsg('Listening…')
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
        }
        break
      case 'processing':
        setStatusMsg('🧠 Thinking…')
        break
      case 'response':
        // Show ANAIRA's response text immediately
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
  wrapper: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    overflow: 'hidden',
    perspective: '1200px',
  },
  bgGlow: {
    position: 'absolute',
    width: 500,
    height: 500,
    borderRadius: '50%',
    background: `
      radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 50%),
      radial-gradient(circle at 30% 70%, rgba(79,143,255,0.1) 0%, transparent 50%)
    `,
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    pointerEvents: 'none',
    filter: 'blur(40px)',
  },
  card: {
    width: 380,
    padding: '32px',
    position: 'relative',
    zIndex: 1,
    boxShadow: `
      0 8px 32px rgba(0,0,0,0.5),
      0 20px 60px rgba(0,0,0,0.3),
      0 0 1px rgba(139,92,246,0.3),
      inset 0 1px 0 rgba(255,255,255,0.06)
    `,
    borderImage: 'linear-gradient(180deg, rgba(139,92,246,0.3), rgba(79,143,255,0.1), transparent) 1',
    borderWidth: 1,
    borderStyle: 'solid',
    borderColor: 'rgba(139,92,246,0.15)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  logo: {
    width: 38,
    height: 38,
    borderRadius: 12,
    background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-violet))',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    fontSize: 18,
    color: 'white',
    boxShadow: '0 4px 15px rgba(79,143,255,0.3), inset 0 1px 0 rgba(255,255,255,0.2)',
  },
  logoText: {
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    fontSize: 16,
    color: 'var(--text-primary)',
    letterSpacing: '0.05em',
    textShadow: '0 0 20px rgba(79,143,255,0.2)',
  },
  modeTag: { flexShrink: 0 },
  divider: { margin: '16px 0' },
  orbContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    height: 180,
    margin: '12px 0',
  },
  pulseRing: {
    position: 'absolute',
    width: 140,
    height: 140,
    borderRadius: '50%',
    border: '2px solid rgba(20,217,196,0.4)',
    animation: 'pulse-ring 2s ease-out infinite',
  },
  orb: {
    width: 110,
    height: 110,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    position: 'relative',
    zIndex: 1,
    boxShadow: 'inset 0 -4px 12px rgba(0,0,0,0.3), inset 0 2px 6px rgba(255,255,255,0.1)',
  },
  statusArea: {
    textAlign: 'center',
    minHeight: 60,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '8px 0',
  },
  statusText: {
    color: 'var(--text-secondary)',
    fontSize: 14,
  },
  errorBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 14px',
    borderRadius: 12,
    background: 'rgba(239,68,68,0.08)',
    border: '1px solid rgba(239,68,68,0.2)',
    color: 'var(--accent-red)',
    fontSize: 13,
    marginBottom: 12,
    boxShadow: '0 2px 10px rgba(239,68,68,0.1)',
  },
  controls: { marginTop: 12 },
  footer: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    justifyContent: 'center',
    marginTop: 20,
    fontSize: 12,
  },
}