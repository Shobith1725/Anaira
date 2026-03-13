import { useRef, useState, useCallback, useEffect } from 'react'

const SIGNALING_URL = 'http://localhost:8000/rtc/offer'
const RECONNECT_DELAY_MS = 4000

export function useWebRTC({ enabled = false, onAudioTrack, onMessage }) {
  const pcRef = useRef(null)
  const localStream = useRef(null)
  const reconnectTimer = useRef(null)
  const mountedRef = useRef(true)
  const [status, setStatus] = useState('idle')
  // idle | connecting | connected | error

  // ── Safe state setter (prevents update after unmount) ────────────────────
  const safeSetStatus = useCallback((s) => {
    if (mountedRef.current) setStatus(s)
  }, [])

  // ── Tear down peer connection and mic stream completely ───────────────────
  const closePeer = useCallback(() => {
    clearTimeout(reconnectTimer.current)
    if (pcRef.current) {
      pcRef.current.onconnectionstatechange = null
      pcRef.current.ontrack = null
      pcRef.current.ondatachannel = null
      pcRef.current.onicecandidate = null
      pcRef.current.onicegatheringstatechange = null
      pcRef.current.close()
      pcRef.current = null
    }
    if (localStream.current) {
      localStream.current.getTracks().forEach(t => t.stop())
      localStream.current = null
    }
  }, [])

  // ── Main connect function ─────────────────────────────────────────────────
  const connect = useCallback(async () => {
    if (!enabled || !mountedRef.current) return

    closePeer()
    safeSetStatus('connecting')

    try {
      // 1. Grab microphone
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
        video: false,
      })

      if (!mountedRef.current) {
        stream.getTracks().forEach(t => t.stop())
        return
      }
      localStream.current = stream

      // 2. Create peer connection
      const pc = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' },
        ],
      })
      pcRef.current = pc

      // 3. Add mic track → backend
      stream.getAudioTracks().forEach(track => pc.addTrack(track, stream))

      // 4. Receive TTS audio track ← backend
      pc.ontrack = (event) => {
        console.log('[WebRTC] received remote audio track')
        if (event.streams?.[0]) {
          onAudioTrack?.(event.streams[0])
        }
      }

      // 5. Receive JSON control messages over data channel
      //    Backend creates the channel so we listen via ondatachannel
      pc.ondatachannel = (event) => {
        console.log('[WebRTC] data channel opened:', event.channel.label)
        event.channel.onmessage = (e) => {
          try {
            const parsed = JSON.parse(e.data)
            onMessage?.(parsed)
          } catch {
            onMessage?.(e.data)
          }
        }
        event.channel.onerror = (e) => {
          console.error('[WebRTC] data channel error:', e)
        }
      }

      // 6. Handle connection state changes
      pc.onconnectionstatechange = () => {
        const state = pc.connectionState
        console.log('[WebRTC] connection state:', state)

        if (state === 'connected') {
          safeSetStatus('connected')
        }
        if (state === 'failed' || state === 'disconnected') {
          safeSetStatus('error')
          if (enabled && mountedRef.current) {
            console.log(`[WebRTC] reconnecting in ${RECONNECT_DELAY_MS}ms…`)
            closePeer()
            reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS)
          }
        }
        if (state === 'closed') {
          safeSetStatus('idle')
        }
      }

      // 7. Create offer and wait for ALL ICE candidates before sending.
      //    aiortc does not support trickle ICE — all candidates must be
      //    inside the initial SDP or the connection silently fails.
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)

      await new Promise((resolve) => {
        if (pc.iceGatheringState === 'complete') {
          resolve()
          return
        }

        const timeout = setTimeout(() => {
          console.warn('[WebRTC] ICE gathering timed out — sending what we have')
          resolve()
        }, 5000)

        pc.onicegatheringstatechange = () => {
          if (pc.iceGatheringState === 'complete') {
            clearTimeout(timeout)
            resolve()
          }
        }

        // null candidate = gathering complete
        pc.onicecandidate = (e) => {
          if (e.candidate === null) {
            clearTimeout(timeout)
            resolve()
          }
        }
      })

      if (!mountedRef.current) return

      // 8. POST fully gathered SDP offer to backend signaling endpoint
      const res = await fetch(SIGNALING_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: pc.localDescription.sdp,   // post-ICE — contains all candidates
          type: pc.localDescription.type,
        }),
      })

      if (!res.ok) {
        const body = await res.text()
        throw new Error(`Signaling HTTP ${res.status}: ${body}`)
      }

      const answer = await res.json()
      console.log('[WebRTC] received SDP answer from backend')

      if (!mountedRef.current) return

      await pc.setRemoteDescription(new RTCSessionDescription(answer))
      console.log('[WebRTC] SDP exchange complete — waiting for connection…')

    } catch (err) {
      console.error('[WebRTC] connect error:', err)
      closePeer()             // tear down any half-open peer or live mic stream
      safeSetStatus('error')
      if (enabled && mountedRef.current) {
        console.log(`[WebRTC] retrying in ${RECONNECT_DELAY_MS}ms…`)
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }
  }, [enabled, onAudioTrack, onMessage, closePeer, safeSetStatus])

  // ── Full disconnect (called from Widget when user ends call) ─────────────
  const disconnect = useCallback(() => {
    closePeer()
    safeSetStatus('idle')
  }, [closePeer, safeSetStatus])

  // ── React to enabled flag changing ───────────────────────────────────────
  useEffect(() => {
    if (enabled) connect()
    else disconnect()
  }, [enabled])   // intentionally exclude connect/disconnect to avoid infinite loop

  // ── Cleanup on unmount ────────────────────────────────────────────────────
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      closePeer()
    }
  }, [])

  return { status, disconnect }
}