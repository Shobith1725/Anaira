import { useRef, useCallback } from 'react'

/**
 * Plays MP3 audio binary chunks received from the backend WebSocket.
 * Uses Web AudioContext to decode and schedule playback in sequence.
 *
 * ✅ FIXED: Added onPlaybackStart / onPlaybackEnd callbacks so Widget
 * can pause the microphone recorder while ANAIRA is speaking,
 * preventing the audio feedback loop (mic picks up TTS → re-transcribes).
 */
export function useAudioPlayer({ onPlaybackStart, onPlaybackEnd } = {}) {
  const audioCtxRef = useRef(null)
  const playQueueRef = useRef([])
  const isPlayingRef = useRef(false)
  const nextStartTimeRef = useRef(0)
  const activeSourceRef = useRef(null)

  const getCtx = useCallback(() => {
    if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)()
    }
    // Resume if suspended (browser autoplay policy)
    if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume()
    }
    return audioCtxRef.current
  }, [])

  const scheduleNext = useCallback(() => {
    if (playQueueRef.current.length === 0) {
      isPlayingRef.current = false
      activeSourceRef.current = null
      onPlaybackEnd?.()
      return
    }

    const wasPlaying = isPlayingRef.current
    isPlayingRef.current = true

    if (!wasPlaying) {
      onPlaybackStart?.()
    }

    const buffer = playQueueRef.current.shift()
    const ctx = getCtx()

    ctx.decodeAudioData(buffer, (decoded) => {
      const source = ctx.createBufferSource()
      source.buffer = decoded
      source.connect(ctx.destination)
      activeSourceRef.current = source

      const now = ctx.currentTime
      const startAt = Math.max(now, nextStartTimeRef.current)
      source.start(startAt)
      nextStartTimeRef.current = startAt + decoded.duration

      source.onended = scheduleNext
    }, (err) => {
      console.error('[AudioPlayer] Decode error:', err)
      scheduleNext()
    })
  }, [getCtx, onPlaybackStart, onPlaybackEnd])

  /**
   * Enqueue an ArrayBuffer (MP3 bytes from server) for playback.
   */
  const playChunk = useCallback((arrayBuffer) => {
    // Clone the buffer — decodeAudioData consumes it
    playQueueRef.current.push(arrayBuffer.slice(0))
    if (!isPlayingRef.current) {
      scheduleNext()
    }
  }, [scheduleNext])

  const stop = useCallback(() => {
    playQueueRef.current = []
    isPlayingRef.current = false
    nextStartTimeRef.current = 0
    activeSourceRef.current = null
    audioCtxRef.current?.close()
    audioCtxRef.current = null
  }, [])

  return { playChunk, stop }
}
