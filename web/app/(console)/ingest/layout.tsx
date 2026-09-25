import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ingest",
  description:
    "Feed Aether a local path or a public Git URL. Licenses must be MIT, Apache-2.0, or BSD. Python, TypeScript, Go, and Java are parsed. No scrape.",
  alternates: { canonical: "/ingest" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
