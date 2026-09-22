export function pressureColor(pressure: number) {
  if (pressure < 0.6) return "#3d9ee0";
  if (pressure < 1.2) return "#d4a017";
  return "#e05a4f";
}

export function pressureLabel(pressure: number) {
  if (pressure < 0.6) return "calm";
  if (pressure < 1.2) return "watch";
  return "high-pressure";
}
