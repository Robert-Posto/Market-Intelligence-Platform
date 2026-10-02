"use client";

/*
 * Produse & prețuri: fiecare produs Libra față de produsul echivalent de la
 * concurență, din comparatie_libra. Portat din R.produse (app/index.html), cu
 * aceleași reguli; starea filtrelor stă în URL, ca o vedere să se poată trimite.
 */
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ia, meta, num } from "@/lib/api";
import { etNume } from "@/lib/etichete";
import { VECHI } from "@/lib/pagini";
import { CATEGORII, MOTIV, SCURT, vizibila } from "@/lib/produse";
import { Despre } from "@/components/Antet";
import Celula from "./Celula";
import Iconita from "./Iconita";
import ModalDovada from "./ModalDovada";

const SEGMENTE = [["toate", "Toate"], ["PF", "Persoane fizice"], ["PJ", "Firme"]];

/* Tabelul se derulează în interiorul lui, nu pagina: capul cu băncile rămâne mereu
   vizibil. Înălțimea = spațiul rămas pe ecran sub carduri, plus 20% (restul se vede
   derulând puțin pagina). */
function potriveste(w) {
  const main = document.querySelector("main");
  if (!w || !main) return;
  const ingust = window.innerWidth < 860;
  const sus = w.getBoundingClientRect().top - main.getBoundingClientRect().top + main.scrollTop;
  w.style.maxHeight = Math.round(1.2 * (ingust ? window.innerHeight - 70
    : Math.max(380, main.clientHeight - sus - 24))) + "px";
}

export default function ProduseLibra() {
  const sp = useSearchParams();
  const router = useRouter();
  const cale = usePathname();
  const stare = useMemo(() => Object.fromEntries(sp.entries()), [sp]);

  const [lista, setLista] = useState(null);
  const [m, setM] = useState({ nume: {}, logo: {} });
  const [d, setD] = useState(null);
  const [eroare, setEroare] = useState(null);
  const [cauta, setCauta] = useState("");
  const [deschis, setDeschis] = useState(null);
  const track = useRef(null), tw = useRef(null);

  const mergi = useCallback(k => {
    const q = new URLSearchParams(Object.entries({ ...stare, ...k }).filter(([, v]) => v !== "" && v != null));
    router.replace(`${cale}${q.toString() ? "?" + q : ""}`, { scroll: false });
  }, [stare, router, cale]);

  useEffect(() => {
    Promise.all([ia("/api/comparatie_libra"), meta()])
      .then(([l, mm]) => { setLista(l); setM(mm); })
      .catch(e => setEroare(e.message));
  }, []);

  // ce se vede, din răspunsul /api/comparatie_libra și filtrele din URL
  const v = useMemo(() => {
    if (!lista || !lista.disponibil) return null;
    const seg = stare.segment || "toate", cat = stare.cat || "";
    const acop = {}, cmp = {}, nf = {};
    (lista.acoperire || []).forEach(a => { (acop[a.cod] = acop[a.cod] || {})[a.banca] = a; });
    (lista.comparabile || []).forEach(c => { cmp[c.cod] = c.n; });
    (lista.negasite || []).forEach(x => { (nf[x.cod] = nf[x.cod] || {})[x.banca] = x; });
    const banci = (lista.banci || []).map(b => b.slug);
    const peSeg = (lista.produse || []).filter(p => seg === "toate" || p.segment === seg || p.segment === "PF+PJ");
    const produse = peSeg.filter(p => !cat || p.categorie_cod === cat);
    // implicit: produsul cu cele mai multe câmpuri comparabile
    const ales = produse.find(p => p.cod === stare.produs)
      || [...produse].sort((a, b) => (cmp[b.cod] || 0) - (cmp[a.cod] || 0))[0];
    const nrCat = {};
    peSeg.forEach(p => { nrCat[p.categorie_cod] = (nrCat[p.categorie_cod] || 0) + 1; });
    return { seg, cat, acop, cmp, nf, banci, peSeg, produse, ales, nrCat };
  }, [lista, stare]);

  const codAles = v && v.ales ? v.ales.cod : null;
  useEffect(() => {
    if (!codAles) { setD(null); return; }
    let viu = true;
    ia(`/api/comparatie_libra?produs=${encodeURIComponent(codAles)}`)
      .then(x => { if (viu) setD({ cod: codAles, ...x }); })
      .catch(e => viu && setEroare(e.message));
    return () => { viu = false; };
  }, [codAles]);

  // cardul ales stă la mijlocul sliderului — doar când se schimbă produsul, nu la fiecare
  // tastă din căutare; tabelul ocupă restul ecranului de fiecare dată când se redesenează
  const nrProduse = v ? v.produse.length : 0;
  useLayoutEffect(() => {
    const t = track.current, a = t && t.querySelector(".pl-card.activ");
    if (a) t.scrollLeft = a.offsetLeft - (t.clientWidth - a.offsetWidth) / 2;
  }, [codAles, nrProduse]);
  useLayoutEffect(() => { potriveste(tw.current); }, [d, stare]);
  useEffect(() => {
    const f = () => potriveste(tw.current);
    window.addEventListener("resize", f);
    return () => window.removeEventListener("resize", f);
  }, []);
  /* Rotița verticală deasupra sliderului îl mută pe orizontală (altfel derula pagina).
     La capete o lasă să deruleze pagina, ca să nu „blocheze” mouse-ul. */
  useEffect(() => {
    const t = track.current;
    if (!t) return;
    const f = e => {
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
      const max = t.scrollWidth - t.clientWidth;
      if ((e.deltaY < 0 && t.scrollLeft <= 0) || (e.deltaY > 0 && t.scrollLeft >= max - 1)) return;
      e.preventDefault();
      t.scrollLeft += e.deltaY;
    };
    t.addEventListener("wheel", f, { passive: false });
    return () => t.removeEventListener("wheel", f);
  }, [v !== null]);

  const inchide = useCallback(() => setDeschis(null), []);
  const comutator = (
    <div className="taburi pl-vedere">
      <button className="activ">Comparație cu Libra</button>
      {/* matricea pe servicii nu e portată încă: se deschide în aplicația veche */}
      <a className="pl-tab-vechi" href={`${VECHI}/#/produse?vedere=matrice`}
        title="Încă neportată: se deschide în aplicația veche">Comisioane pe bănci ↗</a>
    </div>
  );

  if (eroare) return <section><p className="note" style={{ color: "var(--warn)" }}>Eroare: {eroare}</p></section>;
  if (!lista) return <section><p className="note">se încarcă…</p></section>;
  if (!lista.disponibil) {
    return <>
      <div style={{ marginBottom: 12 }}>{comutator}</div>
      <section><p className="note">Baza nu are încă tabelele comparației cu Libra (<code>produse_libra</code>,
        {" "}<code>comparatie_libra</code>). Se creează cu migrările din <code>extragere_produse_bancare/migrari</code>.</p></section>
    </>;
  }

  const { seg, cat, acop, cmp, nf, banci, peSeg, produse, ales, nrCat } = v;
  const nume = b => SCURT[b] || m.nume[b] || b;
  const logo = (b, cls = "") => (m.logo[b] ? <img className={cls} src={m.logo[b]} alt={nume(b)} /> : null);
  const chk = (k, txt) => (
    <label className="pl-bifa">
      <input type="checkbox" checked={stare[k] === "1"} onChange={() => mergi({ [k]: stare[k] === "1" ? "" : "1" })} /> {txt}
    </label>
  );
  const t = cauta.trim().toLowerCase();
  const dd = d && ales && d.cod === ales.cod ? d : null;

  return (
    <>
      <div className="pl-filtre">
        <div className="taburi">
          {SEGMENTE.map(([s, n]) => (
            <button key={s} className={s === seg ? "activ" : ""} onClick={() => mergi({ segment: s, produs: "" })}>{n}</button>
          ))}
        </div>
        <input className="cauta" placeholder="Caută produs: depozit, card, credit…" value={cauta}
          onChange={e => setCauta(e.target.value)} />
        {comutator}
      </div>

      <div className="pl-chipuri">
        <button className={`pl-chip ${!cat ? "activ" : ""}`} onClick={() => mergi({ cat: "", produs: "" })}>
          Toate<span>{peSeg.length}</span></button>
        {Object.keys(CATEGORII).filter(c => nrCat[c]).map(c => (
          <button key={c} className={`pl-chip ${c === cat ? "activ" : ""}`} onClick={() => mergi({ cat: c, produs: "" })}>
            {CATEGORII[c]}<span>{nrCat[c]}</span></button>
        ))}
      </div>

      <div className="pl-slider">
        <button className="pl-sag" aria-label="Produsele anterioare"
          onClick={() => track.current.scrollBy({ left: -track.current.clientWidth * 0.8, behavior: "smooth" })}>‹</button>
        <div className="pl-track" ref={track}>
          {produse.length ? produse.map(p => (
            <button key={p.cod} className={`pl-card ${ales && p.cod === ales.cod ? "activ" : ""}`}
              hidden={!!t && !(p.denumire + " " + p.cod).toLowerCase().includes(t)}
              onClick={() => mergi({ produs: p.cod })}>
              <span className="cat">{p.segment || ""} · {CATEGORII[p.categorie_cod] || "Altele"}</span>
              <span className="n">{p.denumire}</span>
              <span className="lg">
                {banci.map(b => {
                  const a = (acop[p.cod] || {})[b], n = (nf[p.cod] || {})[b];
                  const titlu = `${nume(b)}: ${a ? a.n + " valori" : n ? MOTIV[n.motiv] || "fără echivalent" : "fără date"}`;
                  return <span key={b} className={`pl-lg ${a ? "da" : n ? "nu" : ""}`} title={titlu}>
                    {logo(b) || nume(b).slice(0, 3)}</span>;
                })}
                {cmp[p.cod]
                  ? <span className="cmp" title="câmpuri cu valori și la Libra, și la concurență">{cmp[p.cod]} comp.</span>
                  : <span className="gri" title="niciun câmp cu valori și la Libra, și la concurență">—</span>}
              </span>
            </button>
          )) : <p className="note">Niciun produs.</p>}
        </div>
        <button className="pl-sag" aria-label="Produsele următoare"
          onClick={() => track.current.scrollBy({ left: track.current.clientWidth * 0.8, behavior: "smooth" })}>›</button>
      </div>

      <section className="pl-sec">
        {ales ? <CapProdus ales={ales} d={dd} chk={chk} /> : null}
        {!ales ? <p className="note">Niciun produs pentru filtrele alese.</p>
          : !dd ? <p className="note">se încarcă…</p>
          : <Tabel d={dd} ales={ales} banci={banci} nf={nf} stare={stare} nume={nume} logo={logo} deschide={setDeschis} tw={tw} />}
        <Despre>
          <b>Ce e aici.</b> Pentru fiecare produs din catalogul Libra, valorile produsului <b>echivalent</b> găsit la
          fiecare bancă (numele lui e în capul coloanei). Nu e toată lista de prețuri a băncii, ci doar produsul care
          corespunde. Pe carduri: logo întreg = avem valori, logo tăiat = banca nu are produsul sau nu îl publică,
          logo estompat = fără date.<br />
          <b>Scenariul.</b> Etichetele de sub o valoare (valută, sumă, perioadă, venit) arată la ce caz se aplică.
          Codul complet al scenariului e în panoul deschis la clic.<br />
          <b>Scenariul de referință.</b> La credite, depozite și schimb valutar, DAE și dobânzile se compară doar pe
          același exemplu (sumă, perioadă, valută): „referință”, „≈ referință” sau „alt exemplu”. Bifa „Doar scenariul
          de referință” le ascunde pe celelalte.<br />
          <b>Corecții automate.</b> Reguli fără model: un 0 rămâne doar dacă citatul spune „0 / gratuit / fără
          comision / inclus”; „negociabil” și „nelimitat” rămân text; dobânda minimă / maximă își are câmpul ei;
          dobânda penalizatoare nu e dobânda produsului; perioadele sunt în luni. Ce s-a respins e în
          {" "}<code>inventare-libra/respinse-reguli-*.json</code>.<br />
          <b>Cât de sigure sunt.</b> Fiecare cifră are citatul regăsit literal în document și încredere ≥ 0,6. Cele
          sub 0,85 au eticheta cu încrederea; „neclar” = aceeași condiție are și alte cifre în document. Toate sunt
          {" "}<b>propuneri</b>, neverificate încă de un om.<br />
          <b>De unde vin.</b> {(lista.banci || []).map(b => `${nume(b.slug)}: ${num(b.n, 0)}`).join(" · ")} valori.
          BT răspunde 403 pe site-ul principal, de aceea are foarte puține.
        </Despre>
      </section>

      <ModalDovada v={deschis} inchide={inchide} />
    </>
  );
}

function CapProdus({ ales, d, chk }) {
  const ref = d && (d.valori || []).map(x => x.scenariu && x.scenariu.referinta).find(Boolean);
  return (
    <div className="pl-cap">
      <h2>{ales.denumire}</h2>
      <span className="gri mono" style={{ fontSize: 11 }}>
        {ales.cod} · {ales.segment || ""}{ales.prioritar ? " · prioritar" : ""}</span>
      {ref ? <span className="pl-ref" title="DAE, dobânzile și ratele se compară doar pe același exemplu de sumă, perioadă și valută">
        <Iconita n="tinta" />Scenariu de referință: <b>{ref.nume}</b></span> : null}
      <span className="pl-bife">
        {ref ? chk("ref", "Doar scenariul de referință") : null}
        {chk("toate", "Și câmpurile necomparabile")}
        {chk("low", "Ascunde încrederea sub 0,85")}
        {chk("amb", "Ascunde valorile neclare")}
      </span>
    </div>
  );
}

// tabelul produsului ales: un rând per câmp, o coloană per bancă
function Tabel({ d, ales, banci, nf, stare, nume, logo, deschide, tw }) {
  const pc = {};
  (d.valori || []).forEach(x => { ((pc[x.camp] = pc[x.camp] || {})[x.banca] = pc[x.camp][x.banca] || []).push(x); });
  const vede = l => (l || []).some(x => vizibila(x, stare));
  let campuri = Object.keys(pc);
  // în modul „doar referința” rândul rămâne și când Libra n-are cifra pe referință:
  // tocmai asta e informația (Libra publică alt exemplu), nu un motiv să dispară rândul
  if (stare.toate !== "1") {
    campuri = campuri.filter(c => (stare.ref === "1"
      ? banci.some(b => vede(pc[c][b])) && (pc[c].libra || []).length > 0
      : vede(pc[c].libra) && banci.some(b => b !== "libra" && vede(pc[c][b]))));
  }
  campuri.sort((a, b) => (a === "altele") - (b === "altele") || etNume(a).localeCompare(etNume(b), "ro"));
  if (!campuri.length) {
    return <p className="note">{stare.toate === "1" ? "Nicio valoare pentru filtrele alese."
      : "Niciun câmp nu are valori și la Libra, și la o altă bancă. Bifează „Și câmpurile necomparabile” ca să vezi tot ce s-a colectat."}</p>;
  }
  const ech = {};
  (d.echivalente || []).forEach(e => { ech[e.banca] = e; });
  const nfp = nf[ales.cod] || {};
  return (
    <div className="pl-tw" ref={tw}>
      <table className="pl" style={{ minWidth: 170 + 148 * banci.length }}>
        <thead>
          <tr>
            <th className="camp colt">Ce se compară<small>{campuri.length} câmpuri</small></th>
            {banci.map(b => (
              <th key={b} className={b === "libra" ? "libra" : ""}>
                <span className="bk">{logo(b, "lg")}<b>{nume(b)}</b></span>
                {ech[b] ? <span className="eq" title={ech[b].denumire_la_banca || ""}>{ech[b].denumire_la_banca || ""}</span>
                  : nfp[b] ? <span className="eq sus">{MOTIV[nfp[b].motiv] || "fără echivalent"}</span>
                  : <span className="eq">fără date</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {campuri.map(c => (
            <tr key={c}>
              <th className="camp" scope="row">{etNume(c)}<small>{c}</small></th>
              {banci.map(b => (
                <td key={b} className={b === "libra" ? "libra" : ""}>
                  <Celula key={`${ales.cod}-${c}-${b}`} lista={pc[c][b]} stare={stare} deschide={deschide} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
