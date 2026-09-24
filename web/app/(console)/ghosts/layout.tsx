import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ghost Lab",
  description:
    "Feature intents attach to the architecture and score whether the next change can still land. The heuristic table stays. An agent run writes only in a sandbox.",
  alternates: { canonical: "/ghosts" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
