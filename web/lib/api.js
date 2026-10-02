// Cererile merg la /api/*, pe care next.config.mjs le trimite la app/server.py.

export async function ia(u) {
  const r = await fetch(u);
  const d = await r.json();
  if (d && d.eroare) throw new Error(d.eroare);
  return d;
}

/* Numele și logoul băncii apar în aproape fiecare pagină: se cer o dată pe
   sesiune, nu la fiecare navigare (ca `meta()` din app/index.html). */
let metaP = null;
export function meta() {
  if (!metaP) {
    metaP = Promise.all([ia("/api/banci"), ia("/api/logos")])
      .then(([b, l]) => ({ nume: Object.fromEntries(b.map(x => [x.slug, x.nume])), logo: l || {} }))
      .catch(e => { metaP = null; throw e; });
  }
  return metaP;
}

export const num = (v, z = 2) => (v === null || v === undefined ? "—"
  : Number(v).toLocaleString("ro-RO", { maximumFractionDigits: z }));
