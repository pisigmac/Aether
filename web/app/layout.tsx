import type { Metadata } from "next";
import { ForecastProvider } from "@/components/ForecastProvider";
import { Shell } from "@/components/Shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aether — software weather",
  description: "Forecast of architectural pressure, blast radius, and cost.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ForecastProvider>
          <Shell>{children}</Shell>
        </ForecastProvider>
      </body>
    </html>
  );
}
