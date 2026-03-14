"""
Main WebSocket endpoint.
Receives complete 3-second webm audio files from browser,
runs the full AI pipeline, streams voice back.

SESSION MODEL (v2):
- No REST /session/start call required.
- Backend auto-creates session when WS connects.
- Queries Supabase for the first active driver on shift.
- Sends { type: 'session', session_id, driver_id } as the very first frame.

✅ FIXED: removed CHUNK_THRESHOLD accumulation loop.
Frontend now sends one complete self-contained webm file every 3 seconds
(with header intact). No need to buffer multiple chunks — process each
received binary frame directly.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import uuid
from datetime import datetime

from services.deepgram_stt import transcribe
from services.groq         import respond
from services.cartesia_tts import synthesize
from empathy               import get_neutral_directive
from dashboard_ws          import broadcast
from tools                 import execute_tool
from memory                import store_session, get_session, update_session
from config                import settings

router = APIRouter(tags=["voice"])


# ── Shared pipeline function (called by both WS and WebRTC) ───────────────────
async def process_audio_chunk(
    audio_buffer: bytes,
    session_id:   str,
    session:      dict,
    send_text_fn=None,   # async fn(dict) — sends JSON back to client
    send_bytes_fn=None,  # async fn(bytes) — sends audio back to client
) -> None:
    """
    Runs the full AI pipeline for one audio segment:
    Parallel STT + Emotion → EmpathyOS → Groq LLM → Cartesia TTS

    send_text_fn  and send_bytes_fn are injected by the caller
    (WebSocket handler or WebRTC peer) so this function stays transport-agnostic.
    """
    driver_name = session.get("driver_name", "Driver")
    driver_id   = session.get("driver_id")
    mode        = session.get("mode", "logistics")

    # ── Step 1: STT ────────────────────────────────────────────
    stt_result = {}
    try:
        stt_result = await transcribe(audio_buffer)
    except Exception as e:
        print(f"[STT ERROR] {e}")
        return

    transcript = stt_result.get("transcript", "").strip()

    # Skip silence or noise
    if not transcript or len(transcript) < 3:
        return

    print(f"[STT]     {driver_name}: {transcript}")

    await broadcast({
        "type":       "transcript",
        "speaker":    "driver",
        "text":       transcript,
        "language":   "en",
        "session_id": session_id,
    })

    await broadcast({
        "type":       "thought",
        "text":       f"Heard: \"{transcript}\" — processing...",
        "session_id": session_id,
    })

    # ── Step 2: Neutral tone (Hume removed for speed) ─────────
    emotion_directive, tts_params = get_neutral_directive()

    # ── Step 3: Session-aware tool executor ───────────────────
    async def _tool_executor_with_session(tool_name: str, args: dict) -> str:
        if tool_name in ("get_next_stop", "identify_shipment"):
            if not args.get("driver_id"):
                args["driver_id"] = driver_id

        if not args.get("shipment_id"):
            active = session.get("active_shipments", [])
            if active:
                args["shipment_id"] = active[0]["id"]

        await broadcast({
            "type":       "thought",
            "text":       f"Calling tool: {tool_name}",
            "session_id": session_id,
        })

        result = await execute_tool(tool_name, args)

        await broadcast({
            "type":       "tool_call",
            "tool_name":  tool_name,
            "result":     result,
            "session_id": session_id,
        })

        return result

    # ── Step 4: Groq LLM ──────────────────────────────────────
    session_fresh = get_session(session_id)

    await broadcast({
        "type":       "thought",
        "text":       "Analyzing intent and generating response...",
        "session_id": session_id,
    })

    try:
        response_text, updated_history = await respond(
            transcript        = transcript,
            emotion_directive = emotion_directive,
            driver_name       = driver_name,
            driver_id         = driver_id,
            detected_language = "en",
            turn_history      = session_fresh.get("turn_history", []),
            active_shipments  = session_fresh.get("active_shipments", []),
            current_route     = session_fresh.get("current_route"),
            mode              = mode,
            tool_executor     = _tool_executor_with_session,
        )
    except Exception as e:
        print(f"[GROQ ERROR] {e}")
        response_text   = "Sorry, I had trouble with that. Could you repeat?"
        updated_history = session_fresh.get("turn_history", [])

    print(f"[ANAIRA]  {response_text}")

    update_session(session_id, {"turn_history": updated_history})

    await broadcast({
        "type":       "transcript",
        "speaker":    "anaira",
        "text":       response_text,
        "session_id": session_id,
    })

    # Send response text to client
    if send_text_fn:
        try:
            await send_text_fn({"type": "response", "text": response_text})
        except Exception:
            pass

    # ── Step 5: TTS → stream audio back ───────────────────────
    await broadcast({
        "type":       "thought",
        "text":       f"Responding: \"{response_text[:60]}{'...' if len(response_text) > 60 else ''}\" — generating voice...",
        "session_id": session_id,
    })
    try:
        audio_bytes = await synthesize(
            text      = response_text,
            stability = tts_params["stability"],
            speed     = tts_params["speed"],
        )
        if send_bytes_fn:
            await send_bytes_fn(audio_bytes)

    except Exception as e:
        print(f"[TTS ERROR] {e}")
        try:
            from services.deepgram_tts import synthesize_fallback
            audio_bytes = await synthesize_fallback(response_text)
            if send_bytes_fn:
                await send_bytes_fn(audio_bytes)
            print("[TTS] Fell back to DeepGram Aura successfully")
        except Exception as e2:
            print(f"[TTS FALLBACK ERROR] {e2}")
            if send_text_fn:
                await send_text_fn({"type": "tts_fallback", "text": response_text})

    if send_text_fn:
        try:
            await send_text_fn({"type": "done"})
        except Exception:
            pass


# ── WebSocket endpoint (unchanged behaviour) ──────────────────────────────────
@router.websocket("/ws/voice")
async def voice_stream(ws: WebSocket):
    await ws.accept()

    session_id = None

    try:
        # ── Auto-create session ────────────────────────────────
        session_id = str(uuid.uuid4())
        now        = datetime.utcnow().isoformat()

        driver_id        = None
        driver_name      = "Driver"
        mode             = "logistics" if settings.LOGISTICS_MODE else "receptionist"
        active_shipments = []
        current_route    = None

        try:
            from services.supabase_client import (
                get_active_shipments_for_driver,
                get_route_for_driver,
                _db,
            )
            sb = _db()  # reuse singleton — no duplicate client

            result = (
                sb.table("drivers")
                  .select("id, driver_code, caller_id, callers(name, preferred_lang)")
                  .eq("active_shift", True)
                  .limit(1)
                  .execute()
            )
            if result.data:
                row              = result.data[0]
                driver_id        = row["id"]
                caller_info      = row.get("callers") or {}
                driver_name      = caller_info.get("name", "Driver")
                active_shipments = await get_active_shipments_for_driver(driver_id)
                current_route    = await get_route_for_driver(driver_id)

        except Exception as e:
            print(f"[PIPELINE] Supabase lookup failed, using defaults: {e}")

        session = {
            "session_id":       session_id,
            "created_at":       now,
            "turn_history":     [],
            "detected_lang":    "en",
            "mode":             mode,
            "driver_id":        driver_id,
            "driver_name":      driver_name,
            "active_shipments": active_shipments,
            "current_route":    current_route,
        }
        store_session(session_id, session)

        print(f"[PIPELINE] WebSocket open — {driver_name} (session: {session_id})")

        # ── Send session info to frontend as first frame ───────
        await ws.send_text(json.dumps({
            "type":        "session",
            "session_id":  session_id,
            "driver_id":   driver_id,
            "driver_name": driver_name,
            "mode":        mode,
        }))

        await broadcast({
            "type":        "session",
            "session_id":  session_id,
            "driver_id":   driver_id,
            "driver_name": driver_name,
            "mode":        mode,
        })

        # Send neutral emotion defaults so EmotionMeter renders on connect
        await broadcast({
            "type":        "emotion",
            "frustration": 0.0,
            "joy":         0.1,
            "stress":      0.0,
            "confusion":   0.0,
            "session_id":  session_id,
        })

        # ── Injected transport functions for this WS connection ─
        async def ws_send_text(payload: dict):
            await ws.send_text(json.dumps(payload))

        async def ws_send_bytes(data: bytes):
            await ws.send_bytes(data)

        # ── Audio streaming loop ───────────────────────────────
        while True:
            raw = await ws.receive()

            if raw["type"] == "websocket.disconnect":
                break

            if raw["type"] == "websocket.receive":
                raw_bytes = raw.get("bytes") or raw.get("data")
                if isinstance(raw_bytes, bytes) and len(raw_bytes) > 500:
                    session = get_session(session_id)
                    if not session:
                        break
                    await process_audio_chunk(
                        audio_buffer  = raw_bytes,
                        session_id    = session_id,
                        session       = session,
                        send_text_fn  = ws_send_text,
                        send_bytes_fn = ws_send_bytes,
                    )
                    continue

                text = raw.get("text")
                if isinstance(text, str):
                    try:
                        msg = json.loads(text)
                        if msg.get("type") == "end_session":
                            print(f"[PIPELINE] end_session for {session_id}")
                            break
                    except json.JSONDecodeError:
                        pass

    except WebSocketDisconnect:
        print(f"[PIPELINE] Client disconnected: {session_id}")
    except Exception as e:
        print(f"[PIPELINE ERROR] {e}")
        try:
            await ws.send_text(json.dumps({
                "type":    "error",
                "message": "Pipeline error. Please reconnect.",
            }))
        except Exception:
            pass