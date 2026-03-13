import httpx
from config import settings

CARTESIA_URL    = "https://api.cartesia.ai/tts/bytes"
CARTESIA_VOICE  = "a0e99841-438c-4a64-b679-ae501e7d6091"  # Sonic default voice


async def synthesize(text:      str,
                     stability: float = 0.72,
                     speed:     float = 1.0) -> bytes:
    """
    Converts text to MP3 audio bytes using Cartesia Sonic.
    stability and speed come from EmpathyOS.
    Returns raw MP3 bytes to stream back to browser.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            CARTESIA_URL,
            headers={
                "X-API-Key":         settings.CARTESIA_API_KEY,
                "Cartesia-Version":  "2024-06-10",
                "Content-Type":      "application/json",
            },
            json={
                "transcript":    text,
                "model_id":      "sonic-english",
                "voice": {
                    "mode": "id",
                    "id":   CARTESIA_VOICE,
                },
                "output_format": {
                    "container":   "mp3",
                    "encoding":    "mp3",
                    "sample_rate": 44100,
                },
                "speed":     speed,
                "stability": stability,
            },
        )

    if response.status_code != 200:
        raise Exception(
            f"Cartesia error {response.status_code}: {response.text}"
        )

    return response.content