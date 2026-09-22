"use client";

import type { TimelineFrame } from "@/lib/types";

export function TimeScrubber({
  frames,
  index,
  onChange,
}: {
  frames: TimelineFrame[];
  index: number;
  onChange: (index: number) => void;
}) {
  return (
    <div className="card p-4">
      <div className="mb-3 flex items-center justify-between text-sm text-mist">
        <span>now → +24 months</span>
        <span className="font-mono text-sky-200">{frames[index]?.label ?? "now"}</span>
      </div>
      <input
        type="range"
        min={0}
        max={Math.max(frames.length - 1, 0)}
        value={index}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-sky-400"
      />
      <div className="mt-2 flex justify-between font-mono text-xs text-mist/70">
        {frames.map((frame, i) => (
          <button
            key={frame.t_index}
            type="button"
            onClick={() => onChange(i)}
            className={i === index ? "text-sky-200" : "hover:text-white"}
          >
            {frame.label}
          </button>
        ))}
      </div>
    </div>
  );
}
