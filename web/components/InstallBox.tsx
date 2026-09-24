"use client";

import { useState } from "react";

export function InstallBox({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
    } catch {
      const area = document.createElement("textarea");
      area.value = command;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.left = "-9999px";
      document.body.appendChild(area);
      area.select();
      const ok = document.execCommand("copy");
      area.remove();
      if (!ok) return;
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <div id="install" className="mt-8 max-w-xl scroll-mt-24">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#e7a15a]">Install</p>
      <div className="mt-2 flex items-center gap-3 rounded-2xl border border-[#e7a15a]/55 bg-[#10160f] px-4 py-3">
        <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap font-mono text-xs text-[#f3ecdf]">{command}</code>
        <button
          type="button"
          onClick={() => void copy()}
          className="shrink-0 rounded-full border border-[#e7a15a]/70 px-3 py-1 font-mono text-[11px] uppercase tracking-widest text-[#f3ecdf] hover:bg-[#e7a15a] hover:text-[#141910]"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <p className="mt-2 font-mono text-[11px] leading-relaxed text-[#b7aa93]">
        One shot.{" "}
        <a href="/install.sh" className="text-[#e7dcc8] underline decoration-[#e7a15a]/70 underline-offset-2">
          install.sh
        </a>{" "}
        clones the repo, installs the engine and dashboard, and starts them.
      </p>
    </div>
  );
}
