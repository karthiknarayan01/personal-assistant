"""Deterministic red-flag keyword check, as a safety net alongside — never
a replacement for — the agent's own judgment. Instructions require using
both: this tool won't catch every phrasing of an emergency, and the
agent must still reason about severity/context itself.
"""

_RED_FLAGS = [
    "chest pain", "chest pressure", "chest tightness",
    "can't breathe", "cannot breathe", "difficulty breathing",
    "shortness of breath", "gasping for air",
    "severe bleeding", "uncontrolled bleeding", "won't stop bleeding",
    "coughing blood", "vomiting blood", "blood in stool",
    "sudden numbness", "sudden weakness", "slurred speech",
    "face drooping", "one side of my body", "can't move my",
    "suicidal", "want to die", "kill myself", "self-harm", "hurt myself",
    "unconscious", "unresponsive", "passed out", "fainted",
    "seizure", "convulsion", "convulsing",
    "anaphylaxis", "throat swelling", "swollen tongue", "can't swallow",
    "severe allergic reaction",
    "poisoning", "overdose", "swallowed poison", "ingested chemical",
    "severe burn", "third-degree burn",
    "broken bone", "bone sticking out", "visible deformity",
    "fever in newborn", "baby under 3 months", "infant fever",
    "worst headache of my life", "sudden severe headache",
    "severe abdominal pain", "heavy pregnancy bleeding",
]


def check_emergency_symptoms(description: str) -> dict:
    """Checks a symptom description against a list of medical red-flag phrases.

    Call this for every user query before recommending anything. A
    "false" result does NOT mean it's safe to proceed with home remedies
    — still use your own judgment about severity, duration, and context.
    A "true" result means stop and advise immediate medical attention;
    do not offer home remedies for that concern.

    Args:
        description: The user's description of their symptoms/situation,
            in their own words.

    Returns:
        dict: {"status": "success", "is_possible_emergency": bool,
        "matched_terms": [...]}.
    """
    text = description.lower()
    matched = [term for term in _RED_FLAGS if term in text]
    return {
        "status": "success",
        "is_possible_emergency": len(matched) > 0,
        "matched_terms": matched,
    }
