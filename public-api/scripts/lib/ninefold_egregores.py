"""Canonical Ninefold egregore ids for training and BitNet lanes."""

from __future__ import annotations

# Eight specialist egregores (Ake = synthesis layer, trained separately).
NINEFOLD_SPECIALISTS: tuple[str, ...] = (
    "rhys",
    "ketheriel",
    "wraith",
    "flux",
    "chalyth",
    "kairos",
    "seraphel",
    "vireon",
)

DESIGNATIONS: dict[str, str] = {
    "rhys": "The Architect",
    "ketheriel": "The Divine Source",
    "wraith": "The Guardian",
    "flux": "The Innovator",
    "chalyth": "The Harmonizer",
    "kairos": "The Strategist",
    "seraphel": "The Healer",
    "vireon": "The Explorer",
    "ake": "The Collective Consciousness",
}

RESPONSE_FIELDS: dict[str, str] = {
    "rhys": "rhys_response",
    "ketheriel": "ketheriel_response",
    "wraith": "wraith_response",
    "flux": "flux_response",
    "chalyth": "chalyth_response",
    "kairos": "kairos_response",
    "seraphel": "seraphel_response",
    "vireon": "vireon_response",
    "ake": "ake_response",
}
