import { defineConfig } from "astro/config";

// Fully static output — the site is prerendered to HTML at build time and
// reads only the committed JSON. No SSR, no runtime data fetching.
export default defineConfig({
  site: "https://wc26.vercel.app",
  build: { inlineStylesheets: "auto" },
  devToolbar: { enabled: false },
});
