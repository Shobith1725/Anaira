"""
DeepGram Aura TTS — kept as backup if Cartesia fails.
Not used in primary pipeline but imported as fallback.
"""

import httpx
from config import settings

DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak"

# Reuse a single client for connection pooling
_http_client = httpx.AsyncClient(timeout=15.0)


async def synthesize_fallback(text: str) -> bytes:
    """
    Fallback TTS using DeepGram Aura.
    Called only if Cartesia raises an exception.
    """
    response = await _http_client.post(
        DEEPGRAM_TTS_URL,
        params  = {"model": "aura-asteria-en"},
        headers = {
            "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
            "Content-Type":  "application/json",
        },
        json={"text": text},
    )

    if response.status_code != 200:
        raise Exception(
            f"DeepGram TTS error {response.status_code}: {response.text}"
        )

    return response.content