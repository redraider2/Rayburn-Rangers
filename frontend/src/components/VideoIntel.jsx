// frontend/src/components/VideoIntel.jsx

import { useState } from "react";
import { fetchIntelVideos } from "../api/rayburnApi";

export default function VideoIntel({ onSelectVideo, selectedVideo }) {
  const [q, setQ] = useState("Sam Rayburn fishing");
  const [maxResults, setMaxResults] = useState(12);
  const [source, setSource] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadVideos() {
    setLoading(true);
    setError("");

    try {
      const data = await fetchIntelVideos(q, maxResults);
      setSource(data.source || "");
      setItems(Array.isArray(data.items) ? data.items : []);
    } catch (e) {
      setItems([]);
      setSource("");
      setError(e?.message || "Failed to load videos");
    } finally {
      setLoading(false);
    }
  }

  function isSelected(v) {
    const selId = selectedVideo?.videoId || selectedVideo?.id || selectedVideo?.url;
    const vidId = v?.videoId || v?.id || v?.url;
    return selId && vidId && selId === vidId;
  }

  return (
    <div style={{ padding: 16, fontFamily: "system-ui, -apple-system, Segoe UI, Roboto" }}>
      <h2 style={{ marginTop: 0 }}>Rayburn Ranger — Intel Videos</h2>

      <div style={{ display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap" }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Search</span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{ padding: 8, width: 280 }}
            placeholder="Sam Rayburn fishing"
          />
        </label>

        <label style={{ display: "grid", gap: 6 }}>
          <span>Max results</span>
          <input
            type="number"
            min="1"
            max="50"
            value={maxResults}
            onChange={(e) => setMaxResults(Number(e.target.value))}
            style={{ padding: 8, width: 120 }}
          />
        </label>

        <button
          onClick={loadVideos}
          disabled={loading}
          style={{ padding: "10px 14px", cursor: loading ? "not-allowed" : "pointer" }}
        >
          {loading ? "Loading..." : "Load videos"}
        </button>

        {source && (
          <div style={{ opacity: 0.7 }}>
            source: <b>{source}</b>
          </div>
        )}

        {selectedVideo && (
          <div style={{ opacity: 0.85 }}>
            selected: <b>{selectedVideo.title}</b>
          </div>
        )}
      </div>

      {error && (
        <div style={{ marginTop: 12, color: "crimson" }}>
          <b>Error:</b> {error}
        </div>
      )}

      <div
        style={{
          marginTop: 16,
          display: "grid",
          gap: 12,
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
        }}
      >
        {items.map((v) => {
          const selected = isSelected(v);

          return (
            <div
              key={v.videoId || v.url}
              onClick={() => onSelectVideo?.(v)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onSelectVideo?.(v);
              }}
              style={{
                textDecoration: "none",
                color: "inherit",
                border: selected ? "2px solid #111827" : "1px solid rgba(0,0,0,0.15)",
                borderRadius: 12,
                overflow: "hidden",
                cursor: "pointer",
                boxShadow: selected ? "0 0 0 3px rgba(17,24,39,0.15)" : "none",
              }}
              title="Click to select this video (then link to a ramp on the map)"
            >
              {v.thumbnail ? (
                <img
                  src={v.thumbnail}
                  alt={v.title || "Video thumbnail"}
                  style={{ width: "100%", height: 160, objectFit: "cover" }}
                />
              ) : (
                <div style={{ height: 160, background: "#f5f5f5" }} />
              )}

              <div style={{ padding: 12 }}>
                <div style={{ fontWeight: 700, lineHeight: 1.25 }}>
                  {v.title || "(untitled)"}
                </div>

                <div style={{ fontSize: 14, opacity: 0.8, marginTop: 6 }}>
                  {v.channel || v.channelTitle || ""}
                </div>

                <div style={{ fontSize: 12, opacity: 0.7, marginTop: 6 }}>
                  {v.published || v.publishedAt
                    ? new Date(v.published || v.publishedAt).toLocaleString()
                    : ""}
                </div>

                <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectVideo?.(v);
                    }}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 10,
                      border: selected ? "1px solid #111827" : "1px solid rgba(0,0,0,0.25)",
                      cursor: "pointer",
                      background: selected ? "#111827" : "white",
                      color: selected ? "white" : "inherit",
                    }}
                  >
                    {selected ? "Selected" : "Select"}
                  </button>

                  <a
                    href={v.url}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 10,
                      border: "1px solid rgba(0,0,0,0.25)",
                      textDecoration: "none",
                      color: "inherit",
                      display: "inline-flex",
                      alignItems: "center",
                    }}
                  >
                    Open ↗
                  </a>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
