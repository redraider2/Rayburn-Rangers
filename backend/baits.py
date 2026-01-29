# backend/baits.py
from __future__ import annotations

from typing import Dict, List, Tuple
import re

# 1) Taxonomy: slug -> canonical + category
BAIT_TAXONOMY: Dict[str, Dict[str, str]] = {
    "crankbait": {"canonical": "Crankbait", "category": "hard_baits"},
    "lipless_crankbait": {"canonical": "Lipless Crankbait", "category": "hard_baits"},
    "jerkbait": {"canonical": "Jerkbait", "category": "hard_baits"},
    "spinnerbait": {"canonical": "Spinnerbait", "category": "wire_baits"},
    "chatterbait": {"canonical": "Chatterbait (Bladed Jig)", "category": "wire_baits"},
    "jig": {"canonical": "Jig", "category": "jigs"},
    "frog": {"canonical": "Frog", "category": "topwater"},
    "topwater": {"canonical": "Topwater", "category": "topwater"},
    "soft_plastic": {"canonical": "Soft Plastic", "category": "soft_plastics"},
    "texas_rig": {"canonical": "Texas Rig", "category": "rigs"},
    "carolina_rig": {"canonical": "Carolina Rig", "category": "rigs"},
    "drop_shot": {"canonical": "Drop Shot", "category": "rigs"},
    "ned_rig": {"canonical": "Ned Rig", "category": "rigs"},
    "swimbait": {"canonical": "Swimbait", "category": "soft_plastics"},
}

# 2) Aliases: slug -> phrases to match in transcript text
BAIT_ALIASES: Dict[str, List[str]] = {
    "crankbait": ["crankbait", "squarebill", "deep diver", "shallow crank", "medium diver"],
    "lipless_crankbait": ["lipless", "rattle trap", "rat-l-trap", "trap", "rattletrap"],
    "jerkbait": ["jerkbait", "pointer", "vision 110"],
    "spinnerbait": ["spinnerbait"],
    "chatterbait": ["chatterbait", "bladed jig"],
    "jig": ["jig", "football jig", "flipping jig", "swim jig"],
    "frog": ["frog", "topwater frog"],
    "topwater": ["topwater", "walking bait", "spook", "popper", "buzzbait", "plopper", "whopper plopper"],
    "soft_plastic": ["senko", "stick bait", "worm", "trick worm", "creature bait", "brush hog", "craw", "crawfish"],
    "texas_rig": ["texas rig", "t-rig", "texas-rig"],
    "carolina_rig": ["carolina rig", "c-rig", "carolina-rig"],
    "drop_shot": ["drop shot", "dropshot"],
    "ned_rig": ["ned rig", "ned"],
    "swimbait": ["swimbait", "paddle tail", "paddletail", "keitech"],
}

def normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def iter_alias_pairs() -> List[Tuple[str, str]]:
    """
    Returns list of (slug, alias_normalized) for matching.
    """
    pairs: List[Tuple[str, str]] = []
    for slug, aliases in BAIT_ALIASES.items():
        for a in aliases:
            pairs.append((slug, normalize_text(a)))
    return pairs
