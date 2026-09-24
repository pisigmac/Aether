import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site";

const routes = ["", "/radar", "/butterfly", "/ghosts", "/cost", "/ingest"];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date("2026-09-23");
  return routes.map((path) => ({
    url: `${siteUrl}${path || "/"}`,
    lastModified,
    changeFrequency: path === "" ? "weekly" : "monthly",
    priority: path === "" ? 1 : 0.7,
  }));
}
