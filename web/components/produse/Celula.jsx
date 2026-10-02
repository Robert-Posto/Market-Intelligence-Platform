"use client";

import { useState } from "react";
import { num } from "@/lib/api";
import { etichete, rang, valoare, vizibila } from "@/lib/produse";
import { Eticheta } from "./Iconita";

const VIZIBILE = 3;

function Valoare({ v, deschide }) {
  const e = etichete(v.scenariu, v);
  return (
    <button className="pl-v" onClick={() => deschide(v)} title="citatul și linkul spre document">
      <span className="val">{valoare(v)}</span>
      {v.ambiguu ? <span className="pill amb">neclar</span> : null}
      {v.incredere != null && v.incredere < 0.85 ? <span className="pill">încr. {num(v.incredere)}</span> : null}
      {e.length ? <span className="sc">{e.map((x, i) => <Eticheta key={i} e={x} />)}</span> : null}
    </button>
  );
}

// O celulă bancă × câmp: primele 3 valori, restul la „+ încă N”.
export default function Celula({ lista, stare, deschide }) {
  const [toate, setToate] = useState(false);
  const l = (lista || []).filter(v => vizibila(v, stare)).sort((a, b) => rang(a) - rang(b));
  if (!l.length) {
    if ((lista || []).length) {
      return <span className="pl-gol">{stare.ref === "1" ? "doar alt exemplu" : "ascuns de filtre"}</span>;
    }
    return <span className="pl-gol">—</span>;
  }
  const arata = toate ? l : l.slice(0, VIZIBILE);
  return (
    <>
      {arata.map((v, i) => <Valoare key={i} v={v} deschide={deschide} />)}
      {!toate && l.length > VIZIBILE
        ? <button className="pl-mai" onClick={() => setToate(true)}>+ încă {l.length - VIZIBILE}</button> : null}
    </>
  );
}
