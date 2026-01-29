// frontend/src/api/rayburnApi.js

// Line 1
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

// Line 3
export async function fetchIntelVideos(q = "Sam Rayburn fishing", maxResults = 12) {
  // Line 4
  const url =
    `${API_BASE}/intel/videos` +
    `?q=${encodeURIComponent(q)}` +
    `&max_results=${encodeURIComponent(maxResults)}`;

  // Line 10
  const res = await fetch(url);

  // Line 12
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} - ${text}`);
  }

  // Line 17
  return res.json();
}

// Line 20
export async function fetchRamps() {
  // Line 21
  const url = `${API_BASE}/api/ramps`;

  // Line 23
  const res = await fetch(url);

  // Line 25
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} - ${text}`);
  }

  // Line 30
  return res.json(); // GeoJSON (FeatureCollection)
}
