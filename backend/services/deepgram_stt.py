import httpx
from config import settings

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

# Reuse a single client for connection pooling (saves ~100-200ms per call)
_http_client = httpx.AsyncClient(timeout=10.0)


async def transcribe(audio_buffer: bytes) -> dict:
    """
    Sends raw audio bytes to DeepGram Nova 3.
    Returns transcript and confidence. Language is always 'en'.

    ✅ FIXED: removed detect_language param entirely.
    Previously DeepGram returned detected_language='es' even when
    language='en' was set, which leaked into the Groq system prompt
    and caused Spanish responses.
    """
    params = {
        "model":        "nova-3",
        "smart_format": "true",
        "language":     "en",      # force English — no auto-detection
        "punctuate":    "true",
        # ✅ detect_language intentionally NOT set — it overrides language=en
    }

    response = await _http_client.post(
        DEEPGRAM_URL,
        params  = params,
        headers = {
            "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
            "Content-Type":  "audio/webm",
        },
        content = audio_buffer,
    )

    if response.status_code != 200:
        print(f"[DEEPGRAM ERROR] {response.status_code}: {response.text}")
        return {"transcript": "", "language": "en", "confidence": 0.0}

    data = response.json()

    try:
        channel     = data["results"]["channels"][0]
        alternative = channel["alternatives"][0]
        transcript  = alternative.get("transcript", "")
        confidence  = alternative.get("confidence", 0.0)
    except (KeyError, IndexError):
        return {"transcript": "", "language": "en", "confidence": 0.0}

    return {
        "transcript": transcript,
        "language":   "en",        # always en — never trust detected_language
        "confidence": confidence,
    }