import type { GhostResult } from "@/lib/types";

const TONE = {
  pass: "text-emerald-300",
  warn: "text-amber-300",
  fail: "text-rose-300",
};

export function GhostTable({ ghosts }: { ghosts: GhostResult[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-white/10 px-5 py-4">
        <p className="font-mono text-xs uppercase tracking-widest text-sky-300/80">Extensibility probes</p>
        <h2 className="text-xl">Ghost Lab</h2>
        <p className="mt-1 text-sm text-mist">
          Feature intents attach to the IR and score whether the next change can still land.
        </p>
      </div>
      <table className="w-full text-left text-sm">
        <thead className="text-mist">
          <tr className="border-b border-white/10">
            <th className="px-5 py-3 font-normal">Intent</th>
            <th className="px-5 py-3 font-normal">Verdict</th>
            <th className="px-5 py-3 font-normal">Score</th>
            <th className="px-5 py-3 font-normal">Touches</th>
            <th className="px-5 py-3 font-normal">Trace</th>
          </tr>
        </thead>
        <tbody>
          {ghosts.map((g) => (
            <tr key={g.intent} className="border-b border-white/5 align-top">
              <td className="px-5 py-3">
                <p className="text-white">{g.title}</p>
                <p className="text-xs text-mist">{g.note}</p>
                {g.fail_reason && <p className="text-xs text-rose-200">fail: {g.fail_reason}</p>}
                {g.artifact_path && <p className="text-xs text-mist">artifact: {g.artifact_path}</p>}
              </td>
              <td className={`px-5 py-3 font-mono uppercase ${TONE[g.verdict]}`}>{g.verdict}</td>
              <td className="px-5 py-3 font-mono">{g.extensibility.toFixed(2)}</td>
              <td className="px-5 py-3 text-mist">
                {g.files_touched.slice(0, 3).join(", ") || "—"}
                {g.core_mass_hits.length > 0 && (
                  <p className="text-xs text-amber-200">core: {g.core_mass_hits.join(", ")}</p>
                )}
              </td>
              <td className="px-5 py-3 text-xs">
                {g.trace_url ? (
                  <a className="text-sky-300 underline" href={g.trace_url} target="_blank" rel="noreferrer">
                    {g.trace_id?.slice(0, 8) || "trace"}
                  </a>
                ) : (
                  <span className="text-mist">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
