import "./globals.css";
import Meniu from "@/components/Meniu";

export const metadata = {
  title: "Marketing Command Center · Libra Bank",
  description: "Monitorizarea concurenței bancare: produsele Libra față de concurență, din date publice.",
};

export default function Layout({ children }) {
  return (
    <html lang="ro">
      <head>
        {/* aceleași fonturi ca în app/index.html, ca portarea să nu schimbe aspectul */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" />
      </head>
      <body>
        <Meniu />
        <main>{children}</main>
      </body>
    </html>
  );
}
