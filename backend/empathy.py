"""
EmpathyOS — maps Hume AI emotion scores
to Groq tone directive + Cartesia TTS parameters.
"""


EMOTION_PROFILES = {
    "frustration": {
        "threshold": 0.65,
        "directive": (
            "The driver sounds frustrated. Use a calm, slow, empathetic tone. "
            "Start by acknowledging their situation before giving information. "
            "Never sound dismissive."
        ),
        "stability": 0.95,
        "speed":     0.82,
    },
    "stress": {
        "threshold": 0.60,
        "directive": (
            "The driver sounds stressed. Be reassuring and solution-first. "
            "Lead immediately with what you are doing to help. Keep it short."
        ),
        "stability": 0.90,
        "speed":     0.86,
    },
    "confusion": {
        "threshold": 0.50,
        "directive": (
            "The driver sounds confused. Use very simple, short sentences. "
            "Give one piece of information at a time. "
            "Confirm they understood before moving on."
        ),
        "stability": 0.85,
        "speed":     0.88,
    },
    "joy": {
        "threshold": 0.65,
        "directive": (
            "The driver sounds positive and upbeat. Match their energy. "
            "Be warm and efficient."
        ),
        "stability": 0.55,
        "speed":     1.08,
    },
}

NEUTRAL_PROFILE = {
    "directive": (
        "The driver sounds calm and neutral. "
        "Be professional, warm, and efficient. Keep responses brief."
    ),
    "stability": 0.72,
    "speed":     1.00,
}


def get_neutral_directive() -> tuple[str, dict]:
    """Returns neutral directive and TTS params (no Hume analysis)."""
    return (
        NEUTRAL_PROFILE["directive"],
        {"stability": NEUTRAL_PROFILE["stability"], "speed": NEUTRAL_PROFILE["speed"]}
    )


def get_emotion_directive(scores: dict) -> tuple[str, dict]:
    """
    Takes Hume emotion scores dict.
    Returns (directive_string_for_LLM, tts_params_for_Cartesia).

    tts_params = {"stability": float, "speed": float}
    """
    # Find dominant emotion that exceeds its threshold
    dominant = None
    dominant_score = 0.0

    for emotion, profile in EMOTION_PROFILES.items():
        score = scores.get(emotion, 0.0)
        if score >= profile["threshold"] and score > dominant_score:
            dominant = emotion
            dominant_score = score

    if dominant:
        profile = EMOTION_PROFILES[dominant]
        return (
            profile["directive"],
            {"stability": profile["stability"], "speed": profile["speed"]}
        )

    return (
        NEUTRAL_PROFILE["directive"],
        {"stability": NEUTRAL_PROFILE["stability"], "speed": NEUTRAL_PROFILE["speed"]}
    )