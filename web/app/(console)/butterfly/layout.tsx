import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Butterfly",
  description:
    "Watch a schema change or pull request travel across contracts at now, +3, +8, and +24 months. The path is schema, SQL, module, HTTP, then frontend.",
  alternates: { canonical: "/butterfly" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
