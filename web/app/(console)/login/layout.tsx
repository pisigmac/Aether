import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in through OpenDesk. Aether does not store passwords.",
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return children;
}
