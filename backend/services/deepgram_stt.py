import httpx
from config import settings

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


async def transcribe(audio_buffer: bytes) -> dict:
    """
    Sends raw audio bytes to DeepGram Nova 3.
    Returns transcript, language, confidence.
    """
    params = {
        "model":           "nova-3",
        "smart_format":    "true",
        "language":        "en",
        "punctuate":       "true",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
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
        language    = channel.get("detected_language", "en")
        transcript  = alternative.get("transcript", "")
        confidence  = alternative.get("confidence", 0.0)
    except (KeyError, IndexError):
        return {"transcript": "", "language": "en", "confidence": 0.0}

    return {
        "transcript": transcript,
        "language":   language,
        "confidence": confidence,
    }