import asyncio
import base64
import httpx
from config import settings

# Map Hume's 48 emotion names to our 4 core signals
EMOTION_MAP = {
    "Frustration":         "frustration",
    "Anger":               "frustration",
    "Disgust":             "frustration",
    "Contempt":            "frustration",
    "Joy":                 "joy",
    "Excitement":          "joy",
    "Amusement":           "joy",
    "Satisfaction":        "joy",
    "Pride":               "joy",
    "Relief":              "joy",
    "Stress":              "stress",
    "Anxiety":             "stress",
    "Fear":                "stress",
    "Nervousness":         "stress",
    "Distress":            "stress",
    "Confusion":           "confusion",
    "Doubt":               "confusion",
    "Surprise (negative)": "confusion",
    "Awkwardness":         "confusion",
}

NEUTRAL_SCORES = {
    "frustration": 0.0,
    "joy":         0.0,
    "stress":      0.0,
    "confusion":   0.0,
}


async def analyze_emotion(audio_buffer: bytes) -> dict:
    """
    Submits audio to Hume AI batch inference endpoint.
    Polls for result up to 8 seconds.
    Returns normalized scores for frustration, joy, stress, confusion.
    Always returns a dict — never raises — so the pipeline never crashes.

    FIXES in this version vs old version:
    - asyncio imported at top (was missing — caused NameError on sleep)
    - Uses /v0/batch/jobs HTTP POST (old used /v0/stream/models which needs WebSocket)
    - Parses batch response format (old parsed stream format — always returned neutral)
    """
    scores = dict(NEUTRAL_SCORES)

    try:
        audio_b64 = base64.b64encode(audio_buffer).decode("utf-8")

        async with httpx.AsyncClient(timeout=20.0) as client:

            # ── Step 1: Submit batch job ──────────────────────
            submit_response = await client.post(
                "https://api.hume.ai/v0/batch/jobs",
                headers={
                    "X-Hume-Api-Key": settings.HUME_API_KEY,
                    "Content-Type":   "application/json",
                },
                json={
                    "models": {"prosody": {}},
                    "files":  [
                        {
                            "data":     audio_b64,
                            "filename": "audio.webm",
                        }
                    ],
                    "notify": False,
                },
            )

            if submit_response.status_code != 200:
                print(f"[HUME] Submit failed {submit_response.status_code}: {submit_response.text[:200]}")
                return scores

            job_data = submit_response.json()
            job_id   = job_data.get("job_id")

            if not job_id:
                print(f"[HUME] No job_id in response: {job_data}")
                return scores

            print(f"[HUME] Job submitted: {job_id}")

            # ── Step 2: Poll for result (max 8 seconds) ───────
            for attempt in range(8):
                await asyncio.sleep(1)

                status_response = await client.get(
                    f"https://api.hume.ai/v0/batch/jobs/{job_id}",
                    headers={"X-Hume-Api-Key": settings.HUME_API_KEY},
                )

                if status_response.status_code != 200:
                    continue

                job_status = status_response.json().get("state", {}).get("status", "")

                if job_status == "FAILED":
                    print(f"[HUME] Job {job_id} failed")
                    return scores

                if job_status != "COMPLETED":
                    print(f"[HUME] Job {job_id} status: {job_status} (attempt {attempt + 1})")
                    continue

                # ── Step 3: Fetch predictions ──────────────────
                pred_response = await client.get(
                    f"https://api.hume.ai/v0/batch/jobs/{job_id}/predictions",
                    headers={"X-Hume-Api-Key": settings.HUME_API_KEY},
                )

                if pred_response.status_code != 200:
                    print(f"[HUME] Predictions fetch failed: {pred_response.status_code}")
                    return scores

                predictions = pred_response.json()
                scores      = _parse_scores(predictions, scores)
                print(f"[HUME] Scores: {scores}")
                return scores

            print(f"[HUME] Job {job_id} timed out after 8 seconds — returning neutral")

    except Exception as e:
        print(f"[HUME ERROR] {e}")

    return scores


def _parse_scores(data: list, scores: dict) -> dict:
    """
    Parses Hume batch prediction response.
    Path: data[0] → results → predictions → models → prosody
          → grouped_predictions → predictions → emotions
    """
    try:
        emotions = (
            data[0]
               ["results"]["predictions"][0]
               ["models"]["prosody"]
               ["grouped_predictions"][0]
               ["predictions"][0]
               ["emotions"]
        )
        for emotion in emotions:
            name  = emotion.get("name", "")
            score = float(emotion.get("score", 0.0))
            key   = EMOTION_MAP.get(name)
            if key:
                scores[key] = max(scores[key], score)

    except (KeyError, IndexError, TypeError) as e:
        print(f"[HUME PARSE ERROR] {e}")

    return scores