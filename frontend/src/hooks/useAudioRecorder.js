import { useRef, useState, useCallback } from 'react'

/**
 * Records audio from the microphone.
 *
 * ✅ FIXED v2: Added pauseRecording() and resumeRecording() so the Widget
 * can pause the mic while ANAIRA is speaking (TTS playback), preventing
 * the audio feedback loop where the mic picks up its own response.
 *
 * ✅ FIXED v1: original used recorder.start(250) which emits 250ms fragments.
 * Fix: restart the MediaRecorder every CYCLE_MS so every chunk is a
 * complete, self-contained webm file with its own header.
 */

const CYCLE_MS = 1500   // 1.5s capture window — faster response loop

export function useAudioRecorder({ onChunk }) {
  const [isRecording, setIsRecording] = useState(false)
  const [error, setError] = useState(null)

  const streamRef = useRef(null)
  const recorderRef = useRef(null)
  const cycleTimer = useRef(null)
  const activeRef = useRef(false)   // stays true while recording session is live
  const pausedRef = useRef(false)   // true when paused for TTS playback

  // Pick best supported mime type
  const getMimeType = () => {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ]
    return types.find((t) => MediaRecorder.isTypeSupported(t)) || ''
  }

  // Start one recording cycle
  const startCycle = useCallback(() => {
    if (!activeRef.current || !streamRef.current || pausedRef.current) return

    const mimeType = getMimeType()
    const recorder = new MediaRecorder(streamRef.current, {
      mimeType,
      audioBitsPerSecond: 16000,   // 16kbps — enough for voice STT
    })
    recorderRef.current = recorder

    const chunks = []

    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data)
    }

    recorder.onstop = async () => {
      if (chunks.length === 0) return
      // Combine all chunks into one complete webm blob with header intact
      const blob = new Blob(chunks, { type: mimeType || 'audio/webm' })
      const buffer = await blob.arrayBuffer()
      // Only send if not paused and has enough data (skip near-silent frames)
      if (buffer.byteLength > 500 && !pausedRef.current) {
        onChunk?.(buffer)
      }
      // Immediately start next cycle if still active and not paused
      if (activeRef.current && !pausedRef.current) startCycle()
    }

    recorder.onerror = (e) => {
      console.error('[Recorder] Error:', e.error)
    }

    recorder.start()

    // Stop after CYCLE_MS to trigger onstop → send → restart
    cycleTimer.current = setTimeout(() => {
      if (recorder.state === 'recording') recorder.stop()
    }, CYCLE_MS)

  }, [onChunk])

  const startRecording = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      })
      streamRef.current = stream
      activeRef.current = true
      pausedRef.current = false
      setIsRecording(true)
      startCycle()
    } catch (err) {
      setError(err.message || 'Microphone access denied')
    }
  }, [startCycle])

  const stopRecording = useCallback(() => {
    activeRef.current = false
    pausedRef.current = false
    clearTimeout(cycleTimer.current)
    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop()
    }
    streamRef.current?.getTracks().forEach((t) => t.stop())
    recorderRef.current = null
    streamRef.current = null
    setIsRecording(false)
  }, [])

  // Pause recording (during TTS playback) — stops current cycle, won't start new ones
  const pauseRecording = useCallback(() => {
    pausedRef.current = true
    clearTimeout(cycleTimer.current)
    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop()
    }
  }, [])

  // Resume recording after TTS playback ends
  const resumeRecording = useCallback(() => {
    if (!activeRef.current) return
    pausedRef.current = false
    startCycle()
  }, [startCycle])

  return { isRecording, startRecording, stopRecording, pauseRecording, resumeRecording, error }
}