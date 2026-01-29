// frontend/src/App.jsx

import { useMemo, useState } from "react";
import VideoIntel from "./components/VideoIntel";
import RayburnMap from "./components/RayburnMap";
import "./App.css";

function makeId() {
  // fallback for older browsers
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function App() {
  // Selected video from VideoIntel
  const [selectedVideo, setSelectedVideo] = useState(null);

  // Local MVP links (we’ll persist to backend next)
  const [links, setLinks] = useState([]);

  function handleSelectVideo(video) {
    setSelectedVideo(video);
  }

  function handleLinkAccessPoint(accessPoint) {
    if (!selectedVideo) return;

    const newLink = {
      id: makeId(),

      // video fields
      videoId: selectedVideo.videoId || selectedVideo.id || selectedVideo.url,
      videoTitle: selectedVideo.title || "(untitled)",
      videoUrl: selectedVideo.url || "",

      // access point fields
      accessPointId: accessPoint.id,
      accessPointName: accessPoint.name || "Access Point",

      // MVP default confidence
      confidence: 75,
      createdAt: new Date().toISOString(),
    };

    setLinks((prev) => [newLink, ...prev]);
  }

  const selectedVideoLabel = useMemo(() => {
    if (!selectedVideo) return "None";
    return selectedVideo.title || "(untitled)";
  }, [selectedVideo]);

  return (
    <div className="app">
      <h1>Rayburn Ranger</h1>
      <p className="subtitle">Video intel pulled from your FastAPI backend.</p>

      <VideoIntel onSelectVideo={handleSelectVideo} selectedVideo={selectedVideo} />

      <RayburnMap selectedVideo={selectedVideo} onLink={handleLinkAccessPoint} />

      <section style={{ width: "100%", maxWidth: 900, margin: "20px auto" }}>
        <h3>Linked Intel</h3>

        <div style={{ fontSize: 13, opacity: 0.75, marginBottom: 8 }}>
          Selected video: <b>{selectedVideoLabel}</b>
        </div>

        {links.length === 0 ? (
          <p style={{ opacity: 0.8 }}>
            No links yet. Select a video, then click a ramp marker.
          </p>
        ) : (
          <ul style={{ paddingLeft: 18 }}>
            {links.map((l) => (
              <li key={l.id} style={{ marginBottom: 10 }}>
                <strong>{l.accessPointName}</strong> ←{" "}
                {l.videoUrl ? (
                  <a href={l.videoUrl} target="_blank" rel="noreferrer">
                    {l.videoTitle}
                  </a>
                ) : (
                  l.videoTitle
                )}{" "}
                <span style={{ opacity: 0.7 }}>(confidence {l.confidence})</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
