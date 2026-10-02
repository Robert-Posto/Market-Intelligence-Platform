"use client";

import { useEffect, useRef, useState } from "react";
import { etNume } from "@/lib/etichete";
import { num } from "@/lib/api";
import { REF_TEXT, SCURT, conditie, etichete, valoare } from "@/lib/produse";
import Iconita, { Eticheta } from "./Iconita";

const DURATA = 260;   // ms, aceeași cu tranziția din .pl-modal-cutie

/* Dovada unei valori într-un modal centrat: apare cu fade + scale + translateY(32px)
   și dispare la fel, invers; se demontează abia după ce s-a terminat tranziția. */
export default function ModalDovada({ v, inchide }) {
  const [afisat, setAfisat] = useState(null);
  const [deschis, setDeschis] = useState(false);
  const x = useRef(null);

  useEffect(() => {
    if (v) {
      setAfisat(v);
      // două cadre: întâi se montează în starea inițială, apoi pornește tranziția
      const r = requestAnimationFrame(() => requestAnimationFrame(() => setDeschis(true)));
      return () => cancelAnimationFrame(r);
    }
    setDeschis(false);
    const t = setTimeout(() => setAfisat(null), DURATA);
    return () => clearTimeout(t);
  }, [v]);

  useEffect(() => {
    if (!afisat) return;
    x.current && x.current.focus({ preventScroll: true });
    const esc = e => { if (e.key === "Escape") inchide(); };
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [afisat, inchide]);

  if (!afisat) return null;
  const a = afisat, sc = a.scenariu || {}, e = etichete(a.scenariu, a), cond = conditie(a);
  return (
    <div className={`pl-modal ${deschis ? "deschis" : ""}`}>
      <div className="pl-modal-fundal" onClick={inchide} />
      <div className="pl-modal-cutie" role="dialog" aria-modal="true" aria-labelledby="pl-modal-t">
        <div className="pl-modal-cap">
          <div>
            <h3 id="pl-modal-t">{SCURT[a.banca] || a.banca} · {etNume(a.camp)}</h3>
            <p className="note">{a.denumire_banca || ""}</p>
          </div>
          <button ref={x} className="pl-modal-x" aria-label="Închide" onClick={inchide}>×</button>
        </div>
        <p style={{ fontSize: 22, margin: "0 0 6px" }}><b>{valoare(a)}</b></p>
        {e.length ? <p className="pl-sc-mare">{e.map((x, i) => <Eticheta key={i} e={x} />)}</p> : null}
        {cond ? <p><b>Condiție:</b> {cond}</p> : null}
        {sc.referinta ? (
          <p className="pl-ref-linie"><Iconita n="tinta" /><span>Față de scenariul de referință
            (<b>{sc.referinta.nume}</b>): valoarea {REF_TEXT[sc.referinta.potrivire] || ""}
            {sc.referinta.motiv ? ` — ${sc.referinta.motiv}` : ""}.</span></p>
        ) : null}
        {(sc.reguli || []).length ? (
          <div className="pl-reguli"><b>Corectat automat</b> (reguli deterministe, fără model):
            <ul>{sc.reguli.map((r, i) => <li key={i}>{r}</li>)}</ul></div>
        ) : null}
        {sc.cod ? <p className="gri" style={{ fontSize: 12 }}>Scenariu: <span className="mono">{sc.cod}</span>
          {sc.din_trepte ? " (din treptele documentului)" : ""}</p> : null}
        <blockquote style={{ margin: "10px 0", padding: "8px 12px", borderLeft: "3px solid var(--accent)",
          background: "var(--bg)" }}>{a.citat || ""}</blockquote>
        <p>
          <a href={a.link || a.url} target="_blank" rel="noopener noreferrer">
            Deschide documentul{a.tip === "html" && a.link !== a.url ? " la paragraf" : ""} ↗</a>
          <span className="gri"> · {(a.tip || "").toUpperCase()}</span>
        </p>
        <p className="note">Încredere {a.incredere != null ? num(a.incredere) : "—"} · colectat {a.data_colectare || ""} ·
          {" "}{a.stare === "validat" ? "validat de un om" : "propunere, neverificată de un om"}</p>
        {a.ambiguu ? <p className="callout warn">{a.motiv_ambiguu || "Aceeași condiție are și alte valori în document."}</p> : null}
      </div>
    </div>
  );
}
