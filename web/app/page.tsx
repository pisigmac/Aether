import type { Metadata } from "next";
import Link from "next/link";
import { InstallBox } from "@/components/InstallBox";
import { AetherLogo, HomeLink } from "@/components/Logo";
import { siteDescription, siteName, siteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: {
    absolute: "Aether — software weather for the architecture agents are about to change",
  },
  description: siteDescription,
  alternates: { canonical: "/" },
  openGraph: {
    title: "Aether — forecast the storm in the architecture",
    description: siteDescription,
    url: siteUrl,
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Aether — forecast the storm in the architecture",
    description: siteDescription,
  },
};

const bands = [
  { name: "Calm", range: "P < 0.6", note: "Stable. Features can land without raising structural risk." },
  { name: "Watch", range: "0.6–1.2", note: "Debt is forming. Eight months out it becomes a bottleneck." },
  { name: "High pressure", range: "P ≥ 1.2", note: "A core module will fail the next feature cycle." },
  { name: "Storm", range: "Collision", note: "Two change vectors share a contract. Cut that path." },
];

const instruments = [
  {
    kicker: "01 · Radar",
    title: "A weather map, not a hairball.",
    body: "Cells are sized by mass and colored by pressure. Scrub from now to +24 months and see which modules heat up as the team keeps its current velocity.",
    href: "/radar",
    label: "Open Radar",
  },
  {
    kicker: "02 · Butterfly",
    title: "Watch one change cross the graph.",
    body: "Treat a schema edit or a pull request as a perturbation. Impact travels schema → SQL → module → HTTP → frontend, at now, +3, +8, and +24 months.",
    href: "/butterfly",
    label: "Open Butterfly",
  },
  {
    kicker: "03 · Ghost Lab",
    title: "Ask if the next feature can still land.",
    body: "Pagination, auth, webhooks, a split module. Intents attach to the IR and score extensibility. An agent run writes a stub in a sandbox. The heuristic table stays.",
    href: "/ghosts",
    label: "Open Ghost Lab",
  },
  {
    kicker: "04 · Cost Horizon",
    title: "Price the two-year cost of keeping it.",
    body: "Unbounded lists, chatty calls, missing indexes, god modules, schema leaks. The horizon is tied to the decision in front of you, not a generic cloud bill.",
    href: "/cost",
    label: "Open Cost Horizon",
  },
];

const marks = {
  pandas: {
    fill: "#c4b5fd",
    d: "M16.922 0h2.623v18.104h-2.623zm-4.126 12.94h2.623v2.57h-2.623zm0-7.037h2.623v5.446h-2.623zm0 11.197h2.623v5.446h-2.623zM4.456 5.896h2.622V24H4.455zm4.213 2.559h2.623v2.57H8.67zm0 4.151h2.623v5.447H8.67zm0-11.187h2.623v5.446H8.67Z",
  },
  flask: {
    fill: "#3BABC3",
    d: "M10.773 2.878c-.013 1.434.322 4.624.445 5.734l-8.558 3.83c-.56-.959-.98-2.304-1.237-3.38l-.06.027c-.205.09-.406.053-.494-.088l-.011-.018-.82-1.506c-.058-.105-.05-.252.024-.392a.78.78 0 0 1 .358-.331l9.824-4.207c.146-.064.299-.063.4.004.106.062.127.128.13.327Zm.68 7c.523 1.97.675 2.412.832 2.818l-7.263 3.7a19.35 19.35 0 0 1-1.81-2.83l8.24-3.689Zm12.432 8.786h.003c.283.402-.047.657-.153.698l-.947.37c.037.125.035.319-.217.414l-.736.287c-.229.09-.398-.059-.42-.2l-.025-.125c-4.427 1.784-7.94 1.685-10.696.647-1.981-.745-3.576-1.983-4.846-3.379l6.948-3.54c.721 1.431 1.586 2.454 2.509 3.178 2.086 1.638 4.415 1.712 5.793 1.563l-.047-.233c-.015-.077.007-.135.086-.165l.734-.288a.302.302 0 0 1 .342.086l.748-.288a.306.306 0 0 1 .341.086l.583.89Z",
  },
  express: {
    fill: "#f3ecdf",
    d: "M12.262 16.666h1.146l6.975-9.325H19.22zm9.778 1.441v.004l-4.334-5.706-.557.74 4.873 6.682H.945V4.173h9.505l5.026 6.7.574-.772-4.374-5.928h.003l-.719-.945H0v17.544h24zM10.917 8.705a3.8 3.8 0 0 0-1.292-1.183q-.796-.45-1.916-.45c-.746 0-1.37.14-1.906.424a3.76 3.76 0 0 0-1.31 1.12 4.9 4.9 0 0 0-.75 1.581 7.17 7.17 0 0 0 0 3.696c.148.567.402 1.101.75 1.573a3.5 3.5 0 0 0 1.31 1.066q.803.39 1.906.389 1.77 0 2.739-.868.966-.867 1.328-2.457h-1.139q-.271 1.084-.977 1.734-.704.651-1.952.65-.812 0-1.392-.342a3.1 3.1 0 0 1-.957-.869 3.5 3.5 0 0 1-.551-1.182 5 5 0 0 1-.17-1.133 9 9 0 0 0-.015-.286 4.5 4.5 0 0 1 .015-.829c.047-.418.147-.83.296-1.223A3.7 3.7 0 0 1 5.54 9.05a2.9 2.9 0 0 1 .922-.742q.541-.28 1.246-.28c.47 0 .869.093 1.23.28q.541.281.922.742.379.461.587 1.057t.225 1.246H5.625l.004.957h6.182a7.3 7.3 0 0 0-.18-1.924 4.9 4.9 0 0 0-.715-1.68z",
  },
  python: {
    fill: "#4B8BBE",
    d: "M14.25.18l.9.2.73.26.59.3.45.32.34.34.25.34.16.33.1.3.04.26.02.2-.01.13V8.5l-.05.63-.13.55-.21.46-.26.38-.3.31-.33.25-.35.19-.35.14-.33.1-.3.07-.26.04-.21.02H8.77l-.69.05-.59.14-.5.22-.41.27-.33.32-.27.35-.2.36-.15.37-.1.35-.07.32-.04.27-.02.21v3.06H3.17l-.21-.03-.28-.07-.32-.12-.35-.18-.36-.26-.36-.36-.35-.46-.32-.59-.28-.73-.21-.88-.14-1.05-.05-1.23.06-1.22.16-1.04.24-.87.32-.71.36-.57.4-.44.42-.33.42-.24.4-.16.36-.1.32-.05.24-.01h.16l.06.01h8.16v-.83H6.18l-.01-2.75-.02-.37.05-.34.11-.31.17-.28.25-.26.31-.23.38-.2.44-.18.51-.15.58-.12.64-.1.71-.06.77-.04.84-.02 1.27.05zm-6.3 1.98l-.23.33-.08.41.08.41.23.34.33.22.41.09.41-.09.33-.22.23-.34.08-.41-.08-.41-.23-.33-.33-.22-.41-.09-.41.09zm13.09 3.95l.28.06.32.12.35.18.36.27.36.35.35.47.32.59.28.73.21.88.14 1.04.05 1.23-.06 1.23-.16 1.04-.24.86-.32.71-.36.57-.4.45-.42.33-.42.24-.4.16-.36.09-.32.05-.24.02-.16-.01h-8.22v.82h5.84l.01 2.76.02.36-.05.34-.11.31-.17.29-.25.25-.31.24-.38.2-.44.17-.51.15-.58.13-.64.09-.71.07-.77.04-.84.01-1.27-.04-1.07-.14-.9-.2-.73-.25-.59-.3-.45-.33-.34-.34-.25-.34-.16-.33-.1-.3-.04-.25-.02-.2.01-.13v-5.34l.05-.64.13-.54.21-.46.26-.38.3-.32.33-.24.35-.2.35-.14.33-.1.3-.06.26-.04.21-.02.13-.01h5.84l.69-.05.59-.14.5-.21.41-.28.33-.32.27-.35.2-.36.15-.36.1-.35.07-.32.04-.28.02-.21V6.07h2.09l.14.01zm-6.47 14.25l-.23.33-.08.41.08.41.23.33.33.23.41.08.41-.08.33-.23.23-.33.08-.41-.08-.41-.23-.33-.33-.23-.41-.08-.41.08z",
  },
  fastapi: {
    fill: "#009688",
    d: "M12 .0387C5.3729.0384.0003 5.3931 0 11.9988c-.001 6.6066 5.372 11.9628 12 11.9625 6.628.0003 12.001-5.3559 12-11.9625-.0003-6.6057-5.3729-11.9604-12-11.96m-.829 5.4153h7.55l-7.5805 5.3284h5.1828L5.279 18.5436q2.9466-6.5444 5.892-13.0896",
  },
  huggingface: {
    fill: "#FFD21E",
    d: "M12.025 1.13c-5.77 0-10.449 4.647-10.449 10.378 0 1.112.178 2.181.503 3.185.064-.222.203-.444.416-.577a.96.96 0 0 1 .524-.15c.293 0 .584.124.84.284.278.173.48.408.71.694.226.282.458.611.684.951v-.014c.017-.324.106-.622.264-.874s.403-.487.762-.543c.3-.047.596.06.787.203s.31.313.4.467c.15.257.212.468.233.542.01.026.653 1.552 1.657 2.54.616.605 1.01 1.223 1.082 1.912.055.537-.096 1.059-.38 1.572.637.121 1.294.187 1.967.187.657 0 1.298-.063 1.921-.178-.287-.517-.44-1.041-.384-1.581.07-.69.465-1.307 1.081-1.913 1.004-.987 1.647-2.513 1.657-2.539.021-.074.083-.285.233-.542.09-.154.208-.323.4-.467a1.08 1.08 0 0 1 .787-.203c.359.056.604.29.762.543s.247.55.265.874v.015c.225-.34.457-.67.683-.952.23-.286.432-.52.71-.694.257-.16.547-.284.84-.285a.97.97 0 0 1 .524.151c.228.143.373.388.43.625l.006.04a10.3 10.3 0 0 0 .534-3.273c0-5.731-4.678-10.378-10.449-10.378M8.327 6.583a1.5 1.5 0 0 1 .713.174 1.487 1.487 0 0 1 .617 2.013c-.183.343-.762-.214-1.102-.094-.38.134-.532.914-.917.71a1.487 1.487 0 0 1 .69-2.803m7.486 0a1.487 1.487 0 0 1 .689 2.803c-.385.204-.536-.576-.916-.71-.34-.12-.92.437-1.103.094a1.487 1.487 0 0 1 .617-2.013 1.5 1.5 0 0 1 .713-.174m-10.68 1.55a.96.96 0 1 1 0 1.921.96.96 0 0 1 0-1.92m13.838 0a.96.96 0 1 1 0 1.92.96.96 0 0 1 0-1.92M8.489 11.458c.588.01 1.965 1.157 3.572 1.164 1.607-.007 2.984-1.155 3.572-1.164.196-.003.305.12.305.454 0 .886-.424 2.328-1.563 3.202-.22-.756-1.396-1.366-1.63-1.32q-.011.001-.02.006l-.044.026-.01.008-.03.024q-.018.017-.035.036l-.032.04a1 1 0 0 0-.058.09l-.014.025q-.049.088-.11.19a1 1 0 0 1-.083.116 1.2 1.2 0 0 1-.173.18q-.035.029-.075.058a1.3 1.3 0 0 1-.251-.243 1 1 0 0 1-.076-.107c-.124-.193-.177-.363-.337-.444-.034-.016-.104-.008-.2.022q-.094.03-.216.087-.06.028-.125.063l-.13.074q-.067.04-.136.086a3 3 0 0 0-.135.096 3 3 0 0 0-.26.219 2 2 0 0 0-.12.121 2 2 0 0 0-.106.128l-.002.002a2 2 0 0 0-.09.132l-.001.001a1.2 1.2 0 0 0-.105.212q-.013.036-.024.073c-1.139-.875-1.563-2.317-1.563-3.203 0-.334.109-.457.305-.454m.836 10.354c.824-1.19.766-2.082-.365-3.194-1.13-1.112-1.789-2.738-1.789-2.738s-.246-.945-.806-.858-.97 1.499.202 2.362c1.173.864-.233 1.45-.685.64-.45-.812-1.683-2.896-2.322-3.295s-1.089-.175-.938.647 2.822 2.813 2.562 3.244-1.176-.506-1.176-.506-2.866-2.567-3.49-1.898.473 1.23 2.037 2.16c1.564.932 1.686 1.178 1.464 1.53s-3.675-2.511-4-1.297c-.323 1.214 3.524 1.567 3.287 2.405-.238.839-2.71-1.587-3.216-.642-.506.946 3.49 2.056 3.522 2.064 1.29.33 4.568 1.028 5.713-.624m5.349 0c-.824-1.19-.766-2.082.365-3.194 1.13-1.112 1.789-2.738 1.789-2.738s.246-.945.806-.858.97 1.499-.202 2.362c-1.173.864.233 1.45.685.64.451-.812 1.683-2.896 2.322-3.295s1.089-.175.938.647-2.822 2.813-2.562 3.244 1.176-.506 1.176-.506 2.866-2.567 3.49-1.898-.473 1.23-2.037 2.16c-1.564.932-1.686 1.178-1.464 1.53s3.675-2.511 4-1.297c.323 1.214-3.524 1.567-3.287 2.405.238.839 2.71-1.587 3.216-.642.506.946-3.49 2.056-3.522 2.064-1.29.33-4.568 1.028-5.713-.624",
  },
} as const;

type MarkName = keyof typeof marks;

type Run = { name: string; stack: string; pressure: string; where: string; detail: string; mark: MarkName };

const libraryRuns: Run[] = [
  { name: "pandas", stack: "Python", pressure: "2.21", where: "config.py", detail: "195 of 282 high", mark: "pandas" },
  { name: "Flask", stack: "Python", pressure: "2.22", where: "wrappers.py", detail: "17 of 27 high", mark: "flask" },
  { name: "requests", stack: "Python", pressure: "2.23", where: "adapters.py", detail: "8 of 22 high", mark: "python" },
  { name: "httpcore", stack: "Python", pressure: "2.27", where: "connection_pool.py", detail: "16 of 33 high", mark: "python" },
  { name: "Starlette", stack: "Python", pressure: "2.22", where: "websockets.py", detail: "16 of 51 high", mark: "python" },
  { name: "Express", stack: "Express", pressure: "1.80", where: "application.js", detail: "4 of 9 high", mark: "express" },
  { name: "body-parser", stack: "Express", pressure: "1.61", where: "read.js", detail: "1 of 9 high", mark: "express" },
  { name: "morgan", stack: "Express", pressure: "1.54", where: "index.js", detail: "1 of 3 high", mark: "express" },
  { name: "cors", stack: "Express", pressure: "1.80", where: "lib/index.js", detail: "1 of 3 high", mark: "express" },
  { name: "FastAPI", stack: "Python", pressure: "2.30", where: "fastapi/_compat/shared.py", detail: "19 of 411 high", mark: "fastapi" },
];

const aiRuns: Run[] = [
  { name: "Whisper", stack: "AI", pressure: "2.20", where: "whisper/decoding.py", detail: "7 of 14 high", mark: "python" },
  { name: "Hugging Face Hub", stack: "AI", pressure: "2.27", where: "cli/_cli_utils.py", detail: "112 of 203 high", mark: "huggingface" },
  { name: "sentence-transformers", stack: "AI", pressure: "2.27", where: "util/decorators.py", detail: "97 of 211 high", mark: "huggingface" },
];

function ProjectMark({ name, className = "h-5 w-5 shrink-0" }: { name: MarkName; className?: string }) {
  const mark = marks[name];
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path fill={mark.fill} d={mark.d} />
    </svg>
  );
}

function RunChip({ run, rule = "border-[#e7a15a]/45" }: { run: Run; rule?: string }) {
  return (
    <span className={`inline-flex items-center gap-3 border-r px-6 py-3 font-mono text-xs uppercase tracking-wider ${rule}`}>
      <ProjectMark name={run.mark} />
      <span className="text-[#f3ecdf]">{run.name}</span>
      <span className="text-[#7dbea8]">{run.stack}</span>
      <span className="text-[#e7a15a]">High pressure</span>
      <span className="text-[#e7dcc8]">P {run.pressure}</span>
      <span className="normal-case tracking-normal text-[#b7aa93]">{run.where}</span>
    </span>
  );
}

function StatusStrip({
  runs,
  label,
  className = "",
  rule,
  repeat = 1,
}: {
  runs: Run[];
  label: string;
  className?: string;
  rule?: string;
  repeat?: number;
}) {
  const loop = Array.from({ length: repeat }, () => runs).flat();
  return (
    <div className={`strip ${className}`} aria-label={label}>
      <div className="strip-track">
        {[0, 1].map((copy) => (
          <div key={copy} className="flex" aria-hidden={copy === 1}>
            {loop.map((run, index) => (
              <RunChip key={`${copy}-${run.name}-${index}`} run={run} rule={rule} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: siteName,
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Web",
  description: siteDescription,
  url: siteUrl,
  softwareHelp: `${siteUrl}/ingest`,
  featureList: [
    "Architectural pressure radar",
    "Blast-radius butterfly graph",
    "Ghost Lab extensibility probes",
    "24-month cost horizon",
  ],
};

export default function LandingPage() {
  return (
    <div className="bulletin min-h-screen">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <a href="#bulletin" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-white focus:px-3 focus:py-2 focus:text-black">
        Skip to the bulletin
      </a>
      <header className="sticky top-0 z-30 border-b border-white/10 bg-[#141910]/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
        <AetherLogo />
        <nav className="flex items-center gap-5 font-mono text-xs uppercase tracking-widest">
          <HomeLink className="text-[#f3ecdf]">Home</HomeLink>
          <a href="#install" className="text-[#d7c7a4] hover:text-white">
            Install
          </a>
          <a href="#instruments" className="text-[#d7c7a4] hover:text-white">
            Instruments
          </a>
          <a href="#field" className="text-[#d7c7a4] hover:text-white">
            Field notes
          </a>
          <Link href="/ingest" className="rounded-full border border-[#e7a15a]/70 px-3 py-1.5 text-[#f3ecdf] hover:bg-[#e7a15a] hover:text-[#141910]">
            Ingest a repo
          </Link>
        </nav>
        </div>
      </header>

      <main id="bulletin">
        <section className="mx-auto grid max-w-6xl items-center gap-10 px-6 pb-16 pt-6 md:grid-cols-[1.15fr_0.85fr]">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-[#7dbea8]">Issued for the next 24 months</p>
            <h1 className="mt-4 font-display text-5xl font-medium leading-[1.02] tracking-tight sm:text-6xl">
              Forecast the storm in the architecture.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-[#e7dcc8]">
              Agents write the feature today. Aether reads the repository, fast-forwards the graph at your team’s velocity, and tells you where pressure, blast radius, and cost will be when that feature has to live.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/radar" className="rounded-full bg-[#f3ecdf] px-5 py-3 text-sm font-medium text-[#141910] hover:bg-white">
                Read the forecast
              </Link>
              <Link href="/ingest" className="rounded-full border border-white/20 px-5 py-3 text-sm text-[#f3ecdf] hover:border-white/50">
                Feed it a repository
              </Link>
            </div>
            <InstallBox command={`curl -fsSL ${siteUrl}/install.sh | bash`} />
            <p className="mt-6 max-w-xl font-mono text-xs leading-relaxed text-[#b7aa93]">
              Python and TypeScript. MIT, Apache-2.0, and BSD. Public git history only. Unresolved edges stay fog — Aether does not invent certainty.
            </p>
          </div>
          <Barometer />
        </section>

        <StatusStrip runs={libraryRuns} label="Library forecast status at eight months" />
        <StatusStrip
          runs={aiRuns}
          label="AI forecast status at eight months"
          className="strip-ai"
          rule="border-[#7dbea8]/45"
          repeat={4}
        />

        <section aria-labelledby="scale-heading" className="border-y border-white/10">
          <div className="mx-auto grid max-w-6xl gap-px bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
            <h2 id="scale-heading" className="sr-only">
              How to read the weather
            </h2>
            {bands.map((band) => (
              <article key={band.name} className="bg-[#141910] px-6 py-6">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#e7a15a]">{band.range}</p>
                <h3 className="mt-2 font-display text-2xl">{band.name}</h3>
                <p className="mt-2 text-sm leading-relaxed text-[#d7c7a4]">{band.note}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="instruments" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-20">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-[#7dbea8]">Four instruments</p>
          <h2 className="mt-3 max-w-2xl font-display text-4xl leading-tight">
            The same forecast, read four ways.
          </h2>
          <div className="mt-12 divide-y divide-white/10 border-y border-white/10">
            {instruments.map((item) => (
              <article key={item.kicker} className="grid gap-4 py-8 md:grid-cols-[180px_1fr_auto] md:items-end">
                <p className="font-mono text-xs uppercase tracking-[0.16em] text-[#e7a15a]">{item.kicker}</p>
                <div>
                  <h3 className="font-display text-3xl">{item.title}</h3>
                  <p className="mt-2 max-w-2xl text-[#e7dcc8]">{item.body}</p>
                </div>
                <Link href={item.href} className="font-mono text-xs uppercase tracking-widest text-[#f3ecdf] underline decoration-[#e7a15a]/70 underline-offset-4 hover:text-[#e7a15a]">
                  {item.label}
                </Link>
              </article>
            ))}
          </div>
        </section>

        <section id="field" className="mx-auto grid max-w-6xl scroll-mt-24 gap-6 px-6 pb-20 lg:grid-cols-2">
          <div className="lg:col-span-2">
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-[#7dbea8]">Field notes</p>
            <h2 className="mt-3 font-display text-4xl">Filed at +8 months.</h2>
            <p className="mt-3 max-w-2xl text-[#d7c7a4]">
              Heuristic forecasts from the repos Aether has already ingested. The brass strip is the libraries. The green strip under it is the AI repos.
            </p>
          </div>
          {[...libraryRuns, ...aiRuns].map((run) => (
            <article key={run.name} className="rounded-3xl border border-white/10 bg-[#10160f] p-6">
              <div className="flex items-center gap-3">
                <ProjectMark name={run.mark} className="h-8 w-8 shrink-0" />
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-[#7dbea8]">{run.stack}</p>
                  <h3 className="font-display text-3xl">{run.name}</h3>
                </div>
              </div>
              <p className="mt-3 font-mono text-sm text-[#e7a15a]">High pressure · P {run.pressure}</p>
              <p className="mt-2 text-[#e7dcc8]">
                Hottest file <span className="font-mono text-sm">{run.where}</span>. {run.detail} at this horizon.
              </p>
            </article>
          ))}
        </section>

        <section className="border-t border-white/10">
          <div className="mx-auto grid max-w-6xl gap-10 px-6 py-16 md:grid-cols-[0.8fr_1.2fr]">
            <h2 className="font-display text-4xl leading-tight">How a bulletin is made.</h2>
            <ol className="space-y-5 text-[#e7dcc8]">
              <li><span className="font-mono text-xs text-[#e7a15a]">01 </span>Point Aether at a local checkout or a public Git URL on GitHub, GitLab, Bitbucket, or Codeberg.</li>
              <li><span className="font-mono text-xs text-[#e7a15a]">02 </span>Parsers emit a language-agnostic IR. Physics never sees the source language.</li>
              <li><span className="font-mono text-xs text-[#e7a15a]">03 </span>The graph is fast-forwarded from this repo’s commit velocity. The checkout is not rewritten.</li>
              <li><span className="font-mono text-xs text-[#e7a15a]">04 </span>You read Radar, Butterfly, Ghost Lab, and Cost Horizon from one forecast.</li>
            </ol>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/10">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-8 font-mono text-xs uppercase tracking-widest text-[#b7aa93]">
          <p>Aether · software weather</p>
          <div className="flex gap-5">
            <a href="/install.sh" className="hover:text-white">Install</a>
            <Link href="/radar" className="hover:text-white">Forecast</Link>
            <Link href="/ingest" className="hover:text-white">Ingest</Link>
            <a href="https://pypi.org/project/kaether/" className="hover:text-white">Python SDK</a>
            <a href="https://github.com/pisigmac/Aether" className="hover:text-white">Source</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Barometer() {
  return (
    <figure className="relative mx-auto aspect-square w-full max-w-md" aria-label="Barometer marked calm, watch, high pressure, and storm">
      <svg viewBox="0 0 400 400" className="h-full w-full" role="img">
        <title>Software weather barometer</title>
        <circle cx="200" cy="200" r="168" fill="none" stroke="rgba(243,236,223,0.18)" strokeWidth="1" />
        <g className="isobar" fill="none" stroke="rgba(231,161,90,0.45)" strokeWidth="1">
          <ellipse cx="200" cy="200" rx="150" ry="92" />
          <ellipse cx="200" cy="200" rx="120" ry="150" transform="rotate(28 200 200)" />
          <ellipse cx="200" cy="200" rx="78" ry="140" transform="rotate(64 200 200)" />
        </g>
        <circle cx="200" cy="200" r="108" fill="#10160f" stroke="rgba(243,236,223,0.25)" />
        <path d="M200 200 L200 118" stroke="#e7a15a" strokeWidth="3" strokeLinecap="round" />
        <circle cx="200" cy="200" r="6" fill="#f3ecdf" />
        <text x="248" y="156" textAnchor="middle" fill="#f3ecdf" fontSize="12" fontFamily="ui-monospace, monospace">
          +8 MO
        </text>
        <text x="200" y="248" textAnchor="middle" fill="#d7c7a4" fontSize="11" fontFamily="ui-monospace, monospace">
          HIGH PRESSURE
        </text>
      </svg>
      <figcaption className="sr-only">
        The needle sits in high pressure at month eight, the horizon where a core module becomes the bottleneck.
      </figcaption>
    </figure>
  );
}
