import { PL_IC } from "@/lib/iconite";

// Căile din PL_IC sunt constante din cod (Lucide), nu date venite din API.
export default function Iconita({ n }) {
  return (
    <svg className="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: PL_IC[n] || "" }} />
  );
}

export function Eticheta({ e }) {
  return <span className={`pl-sc ${e.cls || ""}`}><Iconita n={e.ic} />{e.t}</span>;
}
