import { useRef, useState, useCallback } from 'react'

/**
 * Records audio from the microphone.
 *
 * ✅ FIXED: original used recorder.start(250) which emits 250ms fragments.
 * Only the FIRST fragment has the webm container header — all subsequent
 * fragments are headerless and DeepGram cannot decode them, causing empty
 * transcripts after the first response.
 *
 * Fix: restart the MediaRecorder every CYCLE_MS (3000ms) so every chunk
 * sent to the backend is a complete, self-contained webm file with its
 * own header. This matches voice_pipeline.py's CHUNK_THRESHOLD of 12×250ms.
 */

const CYCLE_MS = 3000   // collect 3s then send — matches backend CHUNK_THRESHOLD

export function useAudioRecorder({ onChunk }) {
  const [isRecording, setIsRecording] = useState(false)
  const [error, setError] = useState(null)

  const streamRef = useRef(null)
  const recorderRef = useRef(null)
  const cycleTimer = useRef(null)
  const activeRef = useRef(false)   // stays true while recording session is live

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

  // Start one 3-second recording cycle
  const startCycle = useCallback(() => {
    if (!activeRef.current || !streamRef.current) return

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
      if (buffer.byteLength > 500) {   // skip near-silent frames
        onChunk?.(buffer)
      }
      // Immediately start next cycle if still active
      if (activeRef.current) startCycle()
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
        },
        video: false,
      })
      streamRef.current = stream
      activeRef.current = true
      setIsRecording(true)
      startCycle()
    } catch (err) {
      setError(err.message || 'Microphone access denied')
    }
  }, [startCycle])

  const stopRecording = useCallback(() => {
    activeRef.current = false
    clearTimeout(cycleTimer.current)
    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop()
    }
    streamRef.current?.getTracks().forEach((t) => t.stop())
    recorderRef.current = null
    streamRef.current = null
    setIsRecording(false)
  }, [])

  return { isRecording, startRecording, stopRecording, error }
}