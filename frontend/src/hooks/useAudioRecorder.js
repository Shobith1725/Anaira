import { useRef, useState, useCallback } from 'react'

const CHUNK_INTERVAL_MS = 250

/**
 * Records audio from the microphone and fires onChunk every ~250ms.
 * @param {function} onChunk - Called with (ArrayBuffer) for each audio chunk
 */
export function useAudioRecorder({ onChunk }) {
  const [isRecording, setIsRecording] = useState(false)
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)

  const startRecording = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      streamRef.current = stream

      // Prefer webm/opus for Chrome; backend reads as audio/webm
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'

      const recorder = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000,
      })
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = async (event) => {
        if (event.data && event.data.size > 0) {
          const buffer = await event.data.arrayBuffer()
          onChunk?.(buffer)
        }
      }

      recorder.onerror = (e) => {
        setError('Recorder error: ' + e.error)
        stopRecording()
      }

      // Emit chunk every CHUNK_INTERVAL_MS
      recorder.start(CHUNK_INTERVAL_MS)
      setIsRecording(true)
    } catch (err) {
      setError(err.message || 'Microphone access denied')
    }
  }, [onChunk])

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    mediaRecorderRef.current = null
    streamRef.current = null
    setIsRecording(false)
  }, [])

  return { isRecording, startRecording, stopRecording, error }
}
