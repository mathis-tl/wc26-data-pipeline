// Site-wide constants. Kept out of components so links live in one place.

export const SITE = {
  title: "Coupe du Monde 2026 · rapport du tournoi",
  description:
    "Un rapport visuel de la Coupe du Monde 2026, généré chaque jour par un " +
    "pipeline de données automatisé. Classements recalculés depuis les " +
    "résultats bruts et réconciliés avec l'officiel.",
  repo: "https://github.com/mathis-tl/wc26-data-pipeline",
  author: "Mathis Telle",
  dataSources: [
    { name: "football-data.org", role: "résultats & classements", url: "https://www.football-data.org" },
  ],
  stack: ["Python", "httpx", "DuckDB", "dbt", "Astro", "GitHub Actions", "Vercel"],
};
