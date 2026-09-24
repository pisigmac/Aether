import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Aether — forecast the storm in the architecture";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#141910",
          color: "#f4efe4",
          padding: "64px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 22, letterSpacing: 4 }}>
          <span>AETHER WEATHER SERVICE</span>
          <span>24-MONTH BULLETIN</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ fontSize: 68, lineHeight: 1.02, maxWidth: 900 }}>
            Forecast the storm in the architecture.
          </div>
          <div style={{ fontSize: 28, color: "#d7c7a4" }}>
            Pressure, blast radius, and the cost of keeping the next feature.
          </div>
        </div>
        <div style={{ display: "flex", gap: 28, fontSize: 22 }}>
          <span>CALM</span>
          <span>WATCH</span>
          <span style={{ color: "#e7a15a" }}>HIGH PRESSURE</span>
          <span style={{ color: "#e36b5a" }}>STORM</span>
        </div>
      </div>
    ),
    { ...size },
  );
}
