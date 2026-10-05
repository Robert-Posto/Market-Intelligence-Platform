"use client";

/*
 * Produsele concurenței fără echivalent în catalogul Libra, din products_discovery
 * (servite de /api/products_discovery). Grupate pe categorie; filtrele stau în URL.
 * Un rând cu banca Libra = produs de pe librabank.ro care nu e printre cele 57.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ia, meta } from "@/lib/api";
import { SCURT } from "@/lib/produse";
import { Despre } from "@/components/Antet";

const CATEGORII = {
  conturi: "Conturi", carduri: "Carduri", credite: "Credite", depozite_economii: "Depozite & economii",
  investitii: "Investiții", asigurari: "Asigurări", pensii: "Pensii", leasing: "Leasing",
  plati_digitale: "Plăți digitale", schimb_valutar: "Schimb valutar", trade_finance: "Garanții & acreditive",
  acceptare_plati: "Acceptare plăți", altele: "Altele",
};
const SEGMENTE = [["toate", "Toate"], ["PF", "Persoane fizice"], ["PJ", "Firme"]];
const PENTRU = { PF: "persoane fizice", PJ: "firme", "PF+PJ": "PF și firme" };

export default function ProduseConcurenta() {
  const sp = useSearchParams();
  const router = useRouter();
  const cale = usePathname();
  const stare = useMemo(() => Object.fromEntries(sp.entries()), [sp]);
  const [date, setDate] = useState(null);
  const [m, setM] = useState({ nume: {}, logo: {} });
  const [eroare, setEroare] = useState(null);
  const [cauta, setCauta] = useState("");

  const mergi = useCallback(k => {
    const q = new URLSearchParams(Object.entries({ ...stare, ...k }).filter(([, v]) => v !== "" && v != null));
    router.replace(`${cale}${q.toString() ? "?" + q : ""}`, { scroll: false });
  }, [stare, router, cale]);

  useEffect(() => {
    Promise.all([ia("/api/products_discovery"), meta()])
      .then(([d, mm]) => { setDate(d); setM(mm); })
      .catch(e => setEroare(e.message));
  }, []);

  if (eroare) return <section><p className="note" style={{ color: "var(--warn)" }}>Eroare: {eroare}</p></section>;
  if (!date) return <section><p className="note">se încarcă…</p></section>;
  if (!date.disponibil) {
    return <section><p className="note">Baza nu are încă tabela <code>products_discovery</code>. Se creează cu
      {" "}<code>extragere_produse_bancare/migrari/migration_030_products_discovery.sql</code>.</p></section>;
  }

  const seg = stare.segment || "toate", cat = stare.cat || "", banca = stare.banca || "";
  const t = cauta.trim().toLowerCase();
  const peSeg = date.produse.filter(p => seg === "toate" || p.segment === seg || p.segment === "PF+PJ");
  const nrCat = {}, nrBanca = {};
  peSeg.forEach(p => { nrCat[p.categorie] = (nrCat[p.categorie] || 0) + 1; nrBanca[p.banca] = (nrBanca[p.banca] || 0) + 1; });
  const vizibile = peSeg.filter(p => (!cat || p.categorie === cat) && (!banca || p.banca === banca)
    && (stare.noi !== "1" || p.nou)
    && (!t || `${p.denumire_produs} ${p.descriere_produs || ""}`.toLowerCase().includes(t)));
  const peCat = {};
  vizibile.forEach(p => { (peCat[p.categorie] = peCat[p.categorie] || []).push(p); });
  const nume = b => SCURT[b] || m.nume[b] || b;
  const banciCat = l => new Set(l.map(p => p.banca)).size;

  return (
    <>
      <div className="pl-filtre">
        <div className="taburi">
          {SEGMENTE.map(([s, n]) => (
            <button key={s} className={s === seg ? "activ" : ""} onClick={() => mergi({ segment: s })}>{n}</button>
          ))}
        </div>
        <input className="cauta" placeholder="Caută produs: copii, investiții, leasing…" value={cauta}
          onChange={e => setCauta(e.target.value)} />
        <label className="pl-bifa">
          <input type="checkbox" checked={stare.noi === "1"} onChange={() => mergi({ noi: stare.noi === "1" ? "" : "1" })} />
          {" "}Doar cele apărute luna asta
        </label>
      </div>

      <div className="pl-chipuri">
        <button className={`pl-chip ${!cat ? "activ" : ""}`} onClick={() => mergi({ cat: "" })}>Toate<span>{peSeg.length}</span></button>
        {Object.keys(CATEGORII).filter(c => nrCat[c]).map(c => (
          <button key={c} className={`pl-chip ${c === cat ? "activ" : ""}`} onClick={() => mergi({ cat: c })}>
            {CATEGORII[c]}<span>{nrCat[c]}</span></button>
        ))}
      </div>
      <div className="pl-chipuri">
        <button className={`pl-chip ${!banca ? "activ" : ""}`} onClick={() => mergi({ banca: "" })}>Toate băncile</button>
        {Object.keys(nrBanca).sort((a, b) => nrBanca[b] - nrBanca[a]).map(b => (
          <button key={b} className={`pl-chip ${b === banca ? "activ" : ""}`} onClick={() => mergi({ banca: b })}>
            {nume(b)}<span>{nrBanca[b]}</span></button>
        ))}
      </div>

      {!date.produse.length ? (
        <section><p className="note">Niciun produs încă. Se adaugă rulând
          {" "}<code>python descopera_produse.py --banca bcr</code> din <code>extragere_produse_bancare</code>.</p></section>
      ) : !vizibile.length ? (
        <section><p className="note">Niciun produs pentru filtrele alese.</p></section>
      ) : Object.keys(CATEGORII).filter(c => peCat[c]).map(c => (
        <section key={c} className="pc-sec">
          <h2>{CATEGORII[c]} <span className="gri" style={{ fontSize: 13, fontWeight: 400 }}>
            · {peCat[c].length} {peCat[c].length === 1 ? "produs" : "produse"} la {banciCat(peCat[c])}
            {" "}{banciCat(peCat[c]) === 1 ? "bancă" : "bănci"}</span></h2>
          <div className="pc-lista">
            {peCat[c].map(p => (
              <a key={p.id} className="pc-produs" href={p.link} target="_blank" rel="noopener noreferrer">
                <span className="pc-banca">
                  {m.logo[p.banca] ? <img src={m.logo[p.banca]} alt="" /> : null}{nume(p.banca)}
                </span>
                <span className="pc-nume">{p.denumire_produs}
                  {p.nou ? <span className="pill ok">nou</span> : null}
                  {p.retras ? <span className="pill amb" title={`ultima dată văzut la ${p.vazut_la}`}>retras?</span> : null}
                  {p.banca === "libra" ? <span className="pill amb">Libra îl are, dar nu e în catalog</span> : null}
                </span>
                {p.descriere_produs ? <span className="pc-desc">{p.descriere_produs}</span> : null}
                <span className="pc-jos">{PENTRU[p.segment] || p.segment || ""} · văzut la {p.vazut_la} ↗</span>
              </a>
            ))}
          </div>
        </section>
      ))}

      <section>
        <Despre>
          <b>Ce e aici.</b> Produsele de pe site-urile băncilor pentru care nu am găsit echivalent printre cele
          57 de produse din catalogul Libra. Un produs ajunge aici doar dacă pagina lui e un produs
          (nu un articol sau o campanie), citatul din pagină se regăsește literal și verdictul „fără echivalent” are
          încredere ≥ 0,7; cele nesigure rămân la verificare, în <code>inventare-produse/produse-*.json</code>.<br />
          <b>„nou”</b> = apărut în ultima lună; <b>„retras?”</b> = nu mai era pe site la ultima rulare a băncii.
          {" "}<b>Libra îl are, dar nu e în catalog</b> = pagină de pe librabank.ro fără produs în catalog.<br />
          <b>De unde.</b> Sitemap-urile și meniurile fiecărei bănci, cu robots.txt respectat la fiecare cerere;
          o bancă care răspunde 403 se oprește, nu se ocolește.
        </Despre>
      </section>
    </>
  );
}
