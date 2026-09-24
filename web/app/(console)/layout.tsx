import { ForecastProvider } from "@/components/ForecastProvider";
import { Shell } from "@/components/Shell";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <ForecastProvider>
      <Shell>{children}</Shell>
    </ForecastProvider>
  );
}
