import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Radar",
  description:
    "A weather map of one repository. Cells are sized by mass and colored by architectural pressure. Scrub from now to +24 months.",
  alternates: { canonical: "/radar" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
