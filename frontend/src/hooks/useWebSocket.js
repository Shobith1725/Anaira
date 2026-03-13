import { useEffect, useRef, useState, useCallback } from 'react'

const RECONNECT_DELAY = 3000

/**
 * Generic reusable WebSocket hook.
 * @param {string} url - WebSocket URL to connect to
 * @param {boolean} enabled - Whether to connect
 * @param {function} onMessage - Called with each parsed message (JSON or raw)
 * @param {function} onBinary - Called with each binary message (ArrayBuffer)
 */
export function useWebSocket({ url, enabled = true, onMessage, onBinary }) {
  const wsRef = useRef(null)
  const [status, setStatus] = useState('disconnected') // disconnected | connecting | connected | error
  const reconnectTimer = useRef(null)

  const connect = useCallback(() => {
    if (!enabled || !url) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setStatus('connecting')
    const ws = new WebSocket(url)
    ws.binaryType = 'arraybuffer'
    wsRef.current = ws

    ws.onopen = () => setStatus('connected')

    ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        onBinary?.(event.data)
      } else {
        try {
          const parsed = JSON.parse(event.data)
          onMessage?.(parsed)
        } catch {
          onMessage?.(event.data)
        }
      }
    }

    ws.onerror = () => setStatus('error')

    ws.onclose = () => {
      setStatus('disconnected')
      // Auto-reconnect
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
    }
  }, [url, enabled, onMessage, onBinary])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendText = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }, [])

  const sendBinary = useCallback((buffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(buffer)
    }
  }, [])

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current)
    wsRef.current?.close()
    setStatus('disconnected')
  }, [])

  return { status, sendText, sendBinary, disconnect, wsRef }
}
