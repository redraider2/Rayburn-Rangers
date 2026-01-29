# backend/scripts/transcribe_extract.py
import sys
from pathlib import Path

# Add backend root to Python path so imports work when running as a script
ROOT_DIR = Path(__file__).resolve().parents[1]  # .../backend
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Dict, List, Tuple, Optional

from baits import BAIT_DICTIONARY
from db import connect, insert_bait_hits


@dataclass
class BaitHit:
    bait: str
    keyword: str
    confidence: int
    excerpt: str


def ensure_wav_16k_mono(input_path: Path, wav_out: Path) -> None:
    """
    Convert any media file (mp4/mp3/m4a/wav...) to 16kHz mono wav for stable Whisper input.
    Requires ffmpeg installed system-wide.
    """
    wav_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(wav_out),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def make_excerpt(text: str, idx: int, window: int = 60) -> str:
    start = max(0, idx - window)
    end = min(len(text), idx + window)
    return text[start:end].strip()


def extract_baits(full_text: str, bait_dict: Dict[str, List[str]]) -> List[BaitHit]:
    """
    Simple, explainable extractor:
    - searches for dictionary keywords
    - creates short evidence excerpts
    - sets confidence based on keyword specificity + repetition (basic scoring)
    """
    text = normalize_text(full_text)
    hits: List[BaitHit] = []
    seen: set[Tuple[str, str]] = set()

    # Count occurrences of each keyword
    keyword_counts: Dict[str, int] = {}
    for bait, keywords in bait_dict.items():
        # allow dict to contain non-list values safely (ignore those)
        if not isinstance(keywords, list):
            continue
        for kw in keywords:
            kw_n = normalize_text(kw)
            if not kw_n:
                continue
            keyword_counts[kw_n] = text.count(kw_n)

    for bait, keywords in bait_dict.items():
        if not isinstance(keywords, list):
            continue
        for kw in keywords:
            kw_n = normalize_text(kw)
            if not kw_n:
                continue

            pos = text.find(kw_n)
            if pos == -1:
                continue

            key = (bait, kw_n)
            if key in seen:
                continue
            seen.add(key)

            # Confidence scoring (MVP)
            count = keyword_counts.get(kw_n, 1)
            base = 65
            if len(kw_n) >= 10:
                base += 10  # more specific phrase
            if count >= 2:
                base += 10
            if count >= 4:
                base += 5
            conf = min(95, base)

            excerpt = make_excerpt(text, pos)
            hits.append(BaitHit(bait=bait, keyword=kw, confidence=conf, excerpt=excerpt))

    hits.sort(key=lambda h: (-h.confidence, h.bait))
    return hits


def read_text_file(p: Path) -> str:
    if not p.exists():
        raise SystemExit(f"Transcript file not found: {p}")
    return p.read_text(encoding="utf-8", errors="ignore")


def main():
    parser = argparse.ArgumentParser(description="Transcript bait extraction (text) + optional DB insert")
    parser.add_argument(
        "--text",
        help="Path to a transcript .txt file (recommended for YouTube transcripts).",
        default=None,
    )
    parser.add_argument(
        "--video-id",
        default=None,
        help="video_id to associate bait hits with. If omitted, uses transcript filename stem.",
    )
    parser.add_argument(
        "--outdir",
        default="data/out",
        help="Output directory for JSON results",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip writing bait hits to SQLite (JSON output still written).",
    )

    # Optional legacy path: accept a positional media input (we won't whisper in this version)
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="(Optional) Path to audio/video file. Not used for YouTube transcript mode.",
    )

    args = parser.parse_args()

    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    # Decide transcript source
    transcript_text = ""
    source_label = ""

    if args.text:
        text_path = Path(args.text).expanduser().resolve()
        transcript_text = read_text_file(text_path)
        source_label = f"text:{text_path.name}"
        base_name = text_path.stem
    else:
        raise SystemExit("Missing --text. For YouTube transcripts, run with: --text data/inbox/youtube_transcript.txt")

    # Extract
    print(f"1) Loading transcript ({source_label})...")
    print("\n--- TRANSCRIPT PREVIEW (first 500 chars) ---")
    preview = (transcript_text or "")[:500]
    print(preview if preview else "[empty transcript]")
    print("--- END PREVIEW ---\n")

    print("2) Extracting baits from transcript text...")
    hits = extract_baits(transcript_text, BAIT_DICTIONARY)

    video_id = args.video_id or base_name
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = outdir / f"{base_name}_{stamp}.json"

    # Optional: persist bait hits into SQLite
    inserted = 0
    if not args.no_db:
        db_hits = [
            {
                "bait_name": h.bait,       # canonical bucket (e.g., "crankbait")
                "bait_text": h.keyword,    # matched phrase
                "snippet": h.excerpt,      # evidence excerpt
                "confidence": h.confidence,
            }
            for h in hits
        ]

        if db_hits:
            try:
                with connect() as conn:
                    inserted = insert_bait_hits(conn, video_id, db_hits)
                    conn.commit()
                print(f"✅ Inserted {inserted} bait hits into DB for video_id={video_id}")
            except Exception as e:
                print(f"⚠️ DB insert failed (continuing, JSON still written): {e}")
        else:
            print("ℹ️ No bait hits found; nothing inserted into DB.")

    payload = {
        "source": source_label,
        "video_id": video_id,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "bait_hits": [
            {
                "bait": h.bait,
                "keyword": h.keyword,
                "confidence": h.confidence,
                "excerpt": h.excerpt,
            }
            for h in hits
        ],
        "counts": {
            "bait_hits": len(hits),
            "inserted_to_db": inserted,
        },
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"✅ Done. Wrote: {json_path}")
    print(f"Found {len(hits)} bait hits.")
    if hits[:10]:
        print("Top hits:")
        for h in hits[:10]:
            print(f" - {h.bait} ({h.keyword}) conf={h.confidence}")


if __name__ == "__main__":
    main()
