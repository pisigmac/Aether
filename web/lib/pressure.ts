export function pressureColor(pressure: number) {
  if (pressure < 0.6) return "#7dbea8";
  if (pressure < 1.2) return "#e7a15a";
  return "#e36b5a";
}

export function pressureLabel(pressure: number) {
  if (pressure < 0.6) return "calm";
  if (pressure < 1.2) return "watch";
  return "high-pressure";
}
