"""
DeepGram Aura TTS — kept as backup if Cartesia fails.
Not used in primary pipeline but imported as fallback.
"""

import httpx
from config import settings

DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak"


async def synthesize_fallback(text: str) -> bytes:
    """
    Fallback TTS using DeepGram Aura.
    Called only if Cartesia raises an exception.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
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