import { pagina } from "@/lib/pagini";

// Titlul și descrierea paginii, din registrul PAGINI (ca #titlu / #lede în app/index.html).
export default function Antet({ id }) {
  const p = pagina(id) || {};
  return (
    <div className="cap">
      <h1>{p.t}</h1>
      <p className="lede">{p.l}</p>
    </div>
  );
}

export function Despre({ titlu = "Despre date", children }) {
  return (
    <details className="despre">
      <summary>{titlu}</summary>
      <div className="note">{children}</div>
    </details>
  );
}
