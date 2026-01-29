# backend/app.py
import os
import json
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from youtube_client import youtube_search
from cache import read_cache, write_cache

from db import (
    init_db,
    connect,
    now_iso,
    upsert_video,
    insert_bait_hits,
    get_baits_for_video,
    bait_summary,
)

load_dotenv()

app = FastAPI(title="Rayburn Ranger API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/")
def root():
    return {
        "ok": True,
        "docs": "/docs",
        "endpoints": [
            "/intel/videos",
            "/api/ramps",
            "/api/videos/{video_id}/baits",
            "/api/baits/summary",
            "/api/baits/ingest",
        ],
    }


# -------------------------
# 1) YouTube intel (existing)
# -------------------------
@app.get("/intel/videos")
async def intel_videos(
    q: str = Query(default="Sam Rayburn fishing"),
    max_results: int = Query(default=12, ge=1, le=50),
    ttl_seconds: int = Query(default=6 * 60 * 60),
):
    cache_key = f"yt::{q}::{max_results}"
    cached = read_cache(cache_key, ttl_seconds)
    if cached is not None:
        return {"source": "cache", "items": cached}

    raw = await youtube_search(q, max_results)
    items = []

    for it in raw.get("items", []):
        vid = it.get("id", {}).get("videoId")
        sn = it.get("snippet", {})
        if not vid:
            continue
        items.append(
            {
                "videoId": vid,
                "title": sn.get("title"),
                "channel": sn.get("channelTitle"),
                "published": sn.get("publishedAt"),
                "url": f"https://www.youtube.com/watch?v={vid}",
                "thumbnail": sn.get("thumbnails", {}).get("medium", {}).get("url"),
            }
        )

    write_cache(cache_key, items)
    return {"source": "api", "items": items}


# -------------------------
# 2) Ramps from ArcGIS -> GeoJSON
# -------------------------
def _arcgis_geojson_query_url(layer_url: str) -> str:
    # IMPORTANT: you need the /0 at the end of your FeatureServer URL
    # Example:
    # https://services3.arcgis.com/.../arcgis/rest/services/Rayburn_Access_Points/FeatureServer/0
    params = {
        "where": "1=1",
        "outFields": "*",
        "outSR": "4326",
        "f": "geojson",
    }
    return f"{layer_url}/query"


@app.get("/api/ramps")
async def api_ramps():
    layer_url = os.getenv("RAYBURN_ACCESS_POINTS_LAYER_URL", "").strip()
    if not layer_url:
        raise HTTPException(
            status_code=500,
            detail="Missing RAYBURN_ACCESS_POINTS_LAYER_URL in backend environment",
        )

    # If user accidentally put FeatureServer without /0, warn early:
    if layer_url.endswith("/FeatureServer") or layer_url.endswith("/FeatureServer/"):
        raise HTTPException(
            status_code=500,
            detail="RAYBURN_ACCESS_POINTS_LAYER_URL must end with /0 (layer 0), not the service root.",
        )

    url = _arcgis_geojson_query_url(layer_url)

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params={"where": "1=1", "outFields": "*", "outSR": "4326", "f": "geojson"})
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"ArcGIS query failed: HTTP {r.status_code}")

        return r.json()


# -------------------------
# 3) Bait storage endpoints
# -------------------------

@app.get("/api/videos/{video_id}/baits")
def api_get_baits_for_video(video_id: str):
    with connect() as conn:
        return {"video_id": video_id, "items": get_baits_for_video(conn, video_id)}


@app.get("/api/baits/summary")
def api_bait_summary(limit: int = 25):
    with connect() as conn:
        return {"items": bait_summary(conn, limit=limit)}


@app.post("/api/baits/ingest")
def api_baits_ingest(payload: Dict[str, Any] = Body(...)):
    """
    This is the "bridge" from Whisper output into SQLite.

    Expected payload shape (example):
    {
      "video": {
        "video_id": "zeMZzfGjyy0",
        "title": "...",
        "channel": "...",
        "published": "...",
        "url": "https://www.youtube.com/watch?v=...",
        "thumbnail": "...",
        "source": "whisper"
      },
      "hits": [
        {
          "bait_name": "Texas rig",
          "bait_text": "texas rig",
          "snippet": "…I was throwing a texas rig near the timber…",
          "t_start": 123.4,
          "t_end": 126.1,
          "confidence": 80,
          "category": "rig"
        }
      ]
    }
    """
    video = payload.get("video") or {}
    hits = payload.get("hits") or []

    video_id = (video.get("video_id") or video.get("videoId") or "").strip()
    if not video_id:
        raise HTTPException(status_code=400, detail="payload.video.video_id is required")

    # Normalize video fields
    vrow = {
        "video_id": video_id,
        "title": video.get("title"),
        "channel": video.get("channel") or video.get("channelTitle"),
        "published": video.get("published") or video.get("publishedAt"),
        "url": video.get("url"),
        "thumbnail": video.get("thumbnail"),
        "source": video.get("source") or "ingest",
        "created_at": now_iso(),
    }

    with connect() as conn:
        upsert_video(conn, vrow)

        if not isinstance(hits, list):
            raise HTTPException(status_code=400, detail="payload.hits must be a list")

        n = insert_bait_hits(conn, video_id, hits)
        conn.commit()

    return {"ok": True, "video_id": video_id, "inserted": n}
