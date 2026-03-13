"""
Main WebSocket endpoint.
Receives raw audio from browser (250ms chunks),
runs the full AI pipeline, streams voice back.

SESSION MODEL (v2):
- No REST /session/start call required.
- Backend auto-creates session when WS connects.
- Queries Supabase for the first active driver on shift.
- Sends { type: 'session', session_id, driver_id } as the very first frame.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import uuid
from datetime import datetime

from services.deepgram_stt import transcribe
from services.hume         import analyze_emotion
from services.groq         import respond
from services.cartesia_tts import synthesize
from empathy               import get_emotion_directive
from dashboard_ws          import broadcast
from tools                 import execute_tool
from memory                import store_session, get_session, update_session
from config                import settings

router = APIRouter(tags=["voice"])

# 12 chunks × 250ms = 3 seconds of audio per processing cycle
CHUNK_THRESHOLD = 12


@router.websocket("/ws/voice")
async def voice_stream(ws: WebSocket):
    await ws.accept()

    session_id   = None
    audio_buffer = b""
    chunk_count  = 0

    try:
        # ── Auto-create session ────────────────────────────────
        session_id = str(uuid.uuid4())
        now        = datetime.utcnow().isoformat()

        # Load the first active driver from Supabase (real data)
        driver_id   = None
        driver_name = "Driver"
        mode        = "logistics" if settings.LOGISTICS_MODE else "receptionist"
        active_shipments = []
        current_route    = None

        try:
            from services.supabase_client import (
                get_active_shipments_for_driver,
                get_route_for_driver,
            )
            from supabase import create_client
            sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

            # Grab the first driver on an active shift
            result = (
                sb.table("drivers")
                  .select("id, driver_code, caller_id, callers(name, preferred_lang)")
                  .eq("active_shift", True)
                  .limit(1)
                  .execute()
            )
            if result.data:
                row         = result.data[0]
                driver_id   = row["id"]
                caller_info = row.get("callers") or {}
                driver_name = caller_info.get("name", "Driver")

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
            "type":       "session",
            "session_id": session_id,
            "driver_id":  driver_id,
            "driver_name": driver_name,
            "mode":       mode,
        }))

        # ── Broadcast session start to dashboard ───────────────
        await broadcast({
            "type":       "session",
            "session_id": session_id,
            "driver_id":  driver_id,
            "driver_name": driver_name,
        })

        # ── Audio streaming loop ───────────────────────────────
        while True:
            raw = await ws.receive()

            if raw["type"] == "websocket.disconnect":
                break

            audio_data = None

            if raw["type"] == "websocket.receive":
                raw_bytes = raw.get("bytes") or raw.get("data")
                if isinstance(raw_bytes, bytes) and len(raw_bytes) > 0:
                    audio_data = raw_bytes
                elif isinstance(raw.get("text"), str):
                    try:
                        msg = json.loads(raw["text"])
                        if msg.get("type") == "end_session":
                            print(f"[PIPELINE] end_session received for {session_id}")
                            break
                    except json.JSONDecodeError:
                        pass

            if audio_data:
                audio_buffer += audio_data
                chunk_count  += 1

                if chunk_count < CHUNK_THRESHOLD:
                    continue

                audio_to_process = audio_buffer
                audio_buffer     = b""
                chunk_count      = 0

                session = get_session(session_id)
                if not session:
                    break

                await _process_audio(
                    ws           = ws,
                    session_id   = session_id,
                    session      = session,
                    audio_buffer = audio_to_process,
                )

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


async def _process_audio(
    ws:           WebSocket,
    session_id:   str,
    session:      dict,
    audio_buffer: bytes,
):
    """
    Runs the full AI pipeline for one 3-second audio segment:
    Parallel STT + Emotion → EmpathyOS → Groq LLM → Cartesia TTS
    """
    driver_name = session.get("driver_name", "Driver")
    driver_id   = session.get("driver_id")
    mode        = session.get("mode", "logistics")

    # ── Step 1: Parallel STT + Emotion ────────────────────────
    stt_result     = {}
    emotion_scores = {}
    try:
        async with asyncio.TaskGroup() as tg:
            t_stt = tg.create_task(transcribe(audio_buffer))
            t_emo = tg.create_task(analyze_emotion(audio_buffer))

        stt_result     = t_stt.result()
        emotion_scores = t_emo.result()

    except* Exception as eg:
        print(f"[STT/EMOTION ERROR] {eg.exceptions}")
        stt_result     = {}
        emotion_scores = {}

    transcript = stt_result.get("transcript", "").strip()
    language   = stt_result.get("language", "en")

    # Skip silence or noise
    if not transcript or len(transcript) < 3:
        return

    print(f"[STT]     {driver_name}: {transcript}")
    print(f"[EMOTION] {emotion_scores}")

    update_session(session_id, {"detected_lang": language})

    await broadcast({
        "type":       "transcript",
        "speaker":    "driver",
        "text":       transcript,
        "language":   language,
        "session_id": session_id,
    })

    await broadcast({
        "type":       "emotion",
        "scores":     emotion_scores,
        "session_id": session_id,
    })

    # also send flat emotion keys for the updated Dashboard handler
    await broadcast({
        "type":        "emotion",
        "frustration": emotion_scores.get("frustration", 0),
        "joy":         emotion_scores.get("joy", 0),
        "stress":      emotion_scores.get("stress", 0),
        "confusion":   emotion_scores.get("confusion", 0),
        "session_id":  session_id,
    })

    # ── Step 2: EmpathyOS ─────────────────────────────────────
    emotion_directive, tts_params = get_emotion_directive(emotion_scores)

    if emotion_scores:
        dominant_emotion = max(emotion_scores, key=emotion_scores.get)
        await broadcast({
            "type":       "thought",
            "text":       f"Detected: {dominant_emotion} → adjusting tone and voice params",
            "session_id": session_id,
        })

    # ── Step 3: Session-aware tool executor ───────────────────
    async def _tool_executor_with_session(tool_name: str, args: dict) -> str:
        if tool_name in ("get_next_stop", "identify_shipment"):
            if not args.get("driver_id"):
                args["driver_id"] = driver_id

        if not args.get("shipment_id"):
            active = session.get("active_shipments", [])
            if active:
                args["shipment_id"] = active[0]["id"]

        result = await execute_tool(tool_name, args)

        # Broadcast tool call to dashboard
        await broadcast({
            "type":      "tool_call",
            "tool_name": tool_name,
            "result":    result,
            "session_id": session_id,
        })

        return result

    # ── Step 4: Groq LLM ──────────────────────────────────────
    session_fresh = get_session(session_id)

    try:
        response_text, updated_history = await respond(
            transcript        = transcript,
            emotion_directive = emotion_directive,
            driver_name       = driver_name,
            driver_id         = driver_id,
            detected_language = language,
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

    # send to widget itself as well
    try:
        await ws.send_text(json.dumps({
            "type": "response",
            "text": response_text,
        }))
    except Exception:
        pass

    # ── Step 5: TTS → stream audio back ───────────────────────
    try:
        audio_bytes = await synthesize(
            text      = response_text,
            stability = tts_params["stability"],
            speed     = tts_params["speed"],
        )
        await ws.send_bytes(audio_bytes)

    except Exception as e:
        print(f"[TTS ERROR] {e}")

        try:
            from services.deepgram_tts import synthesize_fallback
            audio_bytes = await synthesize_fallback(response_text)
            await ws.send_bytes(audio_bytes)
            print("[TTS] Fell back to DeepGram Aura successfully")

        except Exception as e2:
            print(f"[TTS FALLBACK ERROR] {e2}")
            await ws.send_text(json.dumps({
                "type": "tts_fallback",
                "text": response_text,
            }))

    # Tell the widget this turn is done — back to listening
    try:
        await ws.send_text(json.dumps({"type": "done"}))
    except Exception:
        pass