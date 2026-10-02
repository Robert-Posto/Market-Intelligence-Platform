"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { PAGINI, PORTATE, href } from "@/lib/pagini";
import { ia, num } from "@/lib/api";

// Piciorul barei spune cât e în bază, nu un slogan. Se cere o dată pe sesiune.
let piciorP = null;

export default function Meniu() {
  const cale = usePathname();
  const [picior, setPicior] = useState(null);

  useEffect(() => {
    if (!piciorP) {
      piciorP = ia("/api/sumar").then(s => {
        const g = c => (s.totaluri.find(x => x.ce === c) || {}).n || 0;
        return { banci: g("bănci"), surse: g("surse"), valori: g("observații") };
      }).catch(() => null);
    }
    piciorP.then(setPicior);
  }, []);

  return (
    <nav>
      <div className="marca">
        <span className="t">Marketing <i>Command</i> Center</span>
        <span className="s">Libra Bank · Monitorizare concurență</span>
      </div>
      <div>
        {PAGINI.map(g => (
          <div key={g.grup}>
            <h3>{g.grup}</h3>
            {g.chei.map(p => {
              const activ = cale === `/${p.id}`;
              const continut = <>{p.nume}{p.pdf ? <span className="pdf">{p.pdf}</span> : null}</>;
              // paginile încă neportate se deschid în aplicația veche (app/server.py)
              return PORTATE.has(p.id)
                ? <Link key={p.id} href={href(p.id)} className={activ ? "activ" : ""}>{continut}</Link>
                : <a key={p.id} href={href(p.id)} title="Încă neportată: se deschide în aplicația veche">{continut}</a>;
            })}
          </div>
        ))}
      </div>
      <div className="picior">
        {picior ? <>{num(picior.banci, 0)} bănci · {num(picior.surse, 0)} surse<br />
          {num(picior.valori, 0)} valori colectate</> : null}
      </div>
    </nav>
  );
}
