import { useRef, useCallback } from 'react'

/**
 * Plays MP3 audio binary chunks received from the backend WebSocket.
 * Uses Web AudioContext to decode and schedule playback in sequence.
 */
export function useAudioPlayer() {
  const audioCtxRef = useRef(null)
  const playQueueRef = useRef([])
  const isPlayingRef = useRef(false)
  const nextStartTimeRef = useRef(0)

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
      return
    }

    isPlayingRef.current = true
    const buffer = playQueueRef.current.shift()
    const ctx = getCtx()

    ctx.decodeAudioData(buffer, (decoded) => {
      const source = ctx.createBufferSource()
      source.buffer = decoded
      source.connect(ctx.destination)

      const now = ctx.currentTime
      const startAt = Math.max(now, nextStartTimeRef.current)
      source.start(startAt)
      nextStartTimeRef.current = startAt + decoded.duration

      source.onended = scheduleNext
    }, (err) => {
      console.error('[AudioPlayer] Decode error:', err)
      scheduleNext()
    })
  }, [getCtx])

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
    audioCtxRef.current?.close()
    audioCtxRef.current = null
  }, [])

  return { playChunk, stop }
}
