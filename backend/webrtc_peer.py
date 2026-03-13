# backend/webrtc_peer.py
# Bridges WebRTC audio frames into the existing voice_pipeline.process_audio_chunk()

import asyncio
import json
import uuid
from datetime import datetime

from aiortc import AudioStreamTrack
from av import AudioFrame

from voice_pipeline import process_audio_chunk
from memory import store_session, get_session
from config import settings


class ANAIRAAudioTrack(AudioStreamTrack):
    """
    Receives raw PCM frames from the browser mic via WebRTC.
    Batches ~3 seconds of audio, then calls process_audio_chunk()
    — the exact same function the WebSocket handler uses.
    Sends TTS audio back to the browser as a WebRTC audio track.
    Sends JSON control events back via the WebRTC data channel.
    """
    kind = "audio"

    def __init__(self, source_track, control_channel=None):
        super().__init__()
        self._source  = source_track
        self._channel = control_channel
        self._out_q   = asyncio.Queue()   # queues decoded AudioFrames for recv()

        # Bootstrap a session identical to the WebSocket flow
        self._session_id = str(uuid.uuid4())
        self._session    = self._init_session()

        asyncio.ensure_future(self._consume())

    def _init_session(self) -> dict:
        """
        Create an in-memory session and attempt Supabase driver lookup —
        mirrors exactly what voice_stream() does on WebSocket connect.
        """
        now  = datetime.utcnow().isoformat()
        mode = "logistics" if settings.LOGISTICS_MODE else "receptionist"

        session = {
            "session_id":       self._session_id,
            "created_at":       now,
            "turn_history":     [],
            "detected_lang":    "en",
            "mode":             mode,
            "driver_id":        None,
            "driver_name":      "Driver",
            "active_shipments": [],
            "current_route":    None,
        }

        # Supabase lookup (best-effort — failure uses defaults above)
        try:
            from supabase import create_client
            from services.supabase_client import (
                get_active_shipments_for_driver,
                get_route_for_driver,
            )
            sb     = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            result = (
                sb.table("drivers")
                  .select("id, driver_code, caller_id, callers(name, preferred_lang)")
                  .eq("active_shift", True)
                  .limit(1)
                  .execute()
            )
            if result.data:
                row                       = result.data[0]
                session["driver_id"]      = row["id"]
                caller_info               = row.get("callers") or {}
                session["driver_name"]    = caller_info.get("name", "Driver")
                # Note: async calls can't run here; shipments loaded lazily below
        except Exception as e:
            print(f"[WebRTC peer] Supabase lookup failed: {e}")

        store_session(self._session_id, session)

        # Send session event to frontend over data channel
        self._send_json({
            "type":        "session",
            "session_id":  self._session_id,
            "driver_id":   session["driver_id"],
            "driver_name": session["driver_name"],
            "mode":        mode,
        })

        print(f"[WebRTC peer] session created — {session['driver_name']} ({self._session_id})")
        return session

    def _send_json(self, payload: dict):
        """Send a JSON control message to the frontend via the WebRTC data channel."""
        if self._channel and self._channel.readyState == "open":
            try:
                self._channel.send(json.dumps(payload))
            except Exception as e:
                print(f"[WebRTC peer] data channel send error: {e}")

    async def _consume(self):
        """
        Read raw PCM frames from the browser mic, batch them to ~3 s,
        then call process_audio_chunk() — same as the WebSocket pipeline.
        """
        buffer       = []
        sample_count = 0
        TARGET       = 16000 * 3   # 3 seconds at 16 kHz, mono

        while True:
            try:
                frame: AudioFrame = await self._source.recv()
                buffer.append(bytes(frame.planes[0]))
                sample_count += frame.samples

                if sample_count >= TARGET:
                    audio_bytes          = b"".join(buffer)
                    buffer, sample_count = [], 0

                    session = get_session(self._session_id)
                    if not session:
                        break

                    # Inject transport functions that write back through WebRTC
                    async def rtc_send_text(payload: dict):
                        self._send_json(payload)

                    async def rtc_send_bytes(mp3_bytes: bytes):
                        """Decode MP3 → AudioFrames and queue them for recv()."""
                        try:
                            import av
                            codec   = av.CodecContext.create("mp3", "r")
                            packets = codec.parse(mp3_bytes)
                            frames  = [f for p in packets for f in codec.decode(p)]
                            for f in frames:
                                await self._out_q.put(f)
                        except Exception as e:
                            print(f"[WebRTC peer] mp3 decode error: {e}")

                    await process_audio_chunk(
                        audio_buffer  = audio_bytes,
                        session_id    = self._session_id,
                        session       = session,
                        send_text_fn  = rtc_send_text,
                        send_bytes_fn = rtc_send_bytes,
                    )

            except Exception as e:
                print(f"[WebRTC peer] consume loop error: {e}")
                break

    async def recv(self) -> AudioFrame:
        """
        Called by aiortc to get the next audio frame to send back to the browser.
        Blocks until a TTS frame is available in the queue.
        Falls back to a silent frame after 50 ms to keep the track alive.
        """
        try:
            frame = await asyncio.wait_for(self._out_q.get(), timeout=0.05)
            return frame
        except asyncio.TimeoutError:
            # Return silence so the track stays open between TTS chunks
            silent = AudioFrame(format="s16", layout="mono", samples=960)
            for plane in silent.planes:
                plane.update(bytes(plane.buffer_size))
            return silent