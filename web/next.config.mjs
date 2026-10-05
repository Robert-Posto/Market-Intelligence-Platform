/*
 * Next.js e doar interfața. Datele vin din API-ul Python (app/server.py), care
 * rămâne singurul loc care citește baza: read-only, cu interogări parametrizate,
 * iar /pdf servește doar URL-uri înregistrate în `surse`. Rescrierile de mai jos
 * trimit cererile mai departe pe server, deci browserul vede o singură origine
 * și nu e nevoie de CORS.
 */
import { fileURLToPath } from "node:url";

const API = process.env.MIP_API || "http://localhost:8765";
// web/ e un proiect separat: fără asta Next.js alegea drept rădăcină proiect-it/
// (are și el un package-lock.json), iar compilarea urmărea fișiere din afara web/
const RADACINA = fileURLToPath(new URL(".", import.meta.url));

/** @type {import('next').NextConfig} */
const config = {
  // indicatorul din colțul stânga-jos acoperea piciorul barei laterale
  devIndicators: false,
  outputFileTracingRoot: RADACINA,
  async rewrites() {
    return [
      { source: "/api/:cale*", destination: `${API}/api/:cale*` },
      { source: "/logos/:cale*", destination: `${API}/logos/:cale*` },
      { source: "/pdf", destination: `${API}/pdf` },
    ];
  },
};

export default config;
