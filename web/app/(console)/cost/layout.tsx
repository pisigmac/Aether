import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cost Horizon",
  description:
    "A 24-month cost horizon tied to architectural patterns: unbounded lists, chatty calls, missing indexes, god modules, and schema leaks.",
  alternates: { canonical: "/cost" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
