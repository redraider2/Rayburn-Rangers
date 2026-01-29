// frontend/src/components/RayburnMap.jsx

// Line 1
import { useEffect, useMemo, useState } from "react";
// Line 2
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
// Line 3
import L from "leaflet";
// Line 4


// Line 6
// Fix default marker icons (Leaflet + Vite/React need this)
import marker2x from "leaflet/dist/images/marker-icon-2x.png";
import marker1x from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

// Line 12
delete L.Icon.Default.prototype._getIconUrl;
// Line 13
L.Icon.Default.mergeOptions({
  iconRetinaUrl: marker2x,
  iconUrl: marker1x,
  shadowUrl: markerShadow,
});

// ✅ ArcGIS Feature Layer URL (must end with /0)
const FEATURE_LAYER_URL =
  import.meta.env.VITE_RAYBURN_ACCESS_POINTS_LAYER_URL || "";

function buildGeoJsonQueryUrl(layerUrl) {
  const params = new URLSearchParams({
    where: "1=1",
    outFields: "*",
    outSR: "4326",
    f: "geojson",
  });
  return `${layerUrl}/query?${params.toString()}`;
}


// Line 20
export default function RayburnMap({ selectedVideo, onLink }) {
  // Line 21
  const [points, setPoints] = useState([]);
  // Line 22
  const [loading, setLoading] = useState(false);
  // Line 23
  const [err, setErr] = useState("");

  // Line 26
  // Rough center for Sam Rayburn area (you can tweak)
  const center = useMemo(() => [31.28, -94.20], []);

  // Line 30
  useEffect(() => {
    // Line 31
    async function loadPoints() {
      // Line 32
      setLoading(true);
      // Line 33
      setErr("");

      try {
        // Line 36
        // ✅ Pull GeoJSON from your backend: http://127.0.0.1:8000/api/ramps
        if (!FEATURE_LAYER_URL) {
          setErr("Missing VITE_RAYBURN_ACCESS_POINTS_LAYER_URL in frontend/.env.local");
return;
}

const url = buildGeoJsonQueryUrl(FEATURE_LAYER_URL);
const res = await fetch(url);
if (!res.ok) throw new Error(`ArcGIS query failed: ${res.status}`);
const geo = await res.json();


        // Line 40
        const features = (geo.features || []).map((f) => {
          const [lng, lat] = f.geometry.coordinates;
          return {
            id: f.properties?.OBJECTID ?? crypto.randomUUID(),
            name:
              f.properties?.Name ||
              f.properties?.NAME ||
              f.properties?.Title ||
              "Access Point",
            type: f.properties?.Type || f.properties?.TYPE || "",
            lat,
            lng,
            raw: f.properties,
          };
        });

        // Line 57
        setPoints(features);
      } catch (e) {
        // Line 59
        setErr(e?.message || "Failed to load access points.");
      } finally {
        // Line 62
        setLoading(false);
      }
    }

    // Line 66
    loadPoints();
  }, []);

  // Line 70
  return (
    <section style={{ width: "100%", maxWidth: 900, margin: "40px auto" }}>
      <h2 style={{ textAlign: "center", marginBottom: 12 }}>Sam Rayburn Map</h2>

      {loading && <p style={{ textAlign: "center" }}>Loading access points…</p>}

      {err && (
        <p style={{ textAlign: "center", color: "crimson" }}>
          {err}
        </p>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 16 }}>
        <div
          style={{
            height: 520,
            borderRadius: 14,
            overflow: "hidden",
            border: "1px solid #e5e7eb",
          }}
        >
          <MapContainer center={center} zoom={10} style={{ height: "100%" }}>
            <TileLayer
              // OSM basemap (free)
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="&copy; OpenStreetMap contributors"
            />

            {points.map((p) => (
              <Marker key={p.id} position={[p.lat, p.lng]}>
                <Popup>
                  <div style={{ minWidth: 220 }}>
                    <strong>{p.name}</strong>
                    {p.type ? <div>Type: {p.type}</div> : null}

                    <div style={{ marginTop: 10 }}>
                      {selectedVideo ? (
                        <>
                          <div style={{ fontSize: 12, opacity: 0.8 }}>
                            Link to selected video:
                          </div>
                          <button
                            onClick={() => onLink(p)}
                            style={{
                              marginTop: 8,
                              padding: "8px 10px",
                              borderRadius: 8,
                              border: "1px solid #111827",
                              cursor: "pointer",
                            }}
                          >
                            Link this ramp
                          </button>
                        </>
                      ) : (
                        <div style={{ fontSize: 12, opacity: 0.8 }}>
                          Select a video above, then link it to a ramp.
                        </div>
                      )}
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>

        <div
          style={{
            border: "1px solid #e5e7eb",
            borderRadius: 14,
            padding: 14,
          }}
        >
          <strong>Selected Video</strong>
          {selectedVideo ? (
            <div style={{ marginTop: 10 }}>
              <div>{selectedVideo.title}</div>
              <div style={{ fontSize: 12, opacity: 0.8 }}>
                {selectedVideo.channel || selectedVideo.channelTitle || ""}
              </div>
            </div>
          ) : (
            <div style={{ marginTop: 10, fontSize: 12, opacity: 0.8 }}>
              Click a video to select it.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
