/*
 * Logica paginii Produse & prețuri, fără HTML: din valorile din comparatie_libra
 * (servite de /api/comparatie_libra) în ce se afișează. Portată din app/index.html
 * (funcțiile pl*), cu aceleași reguli.
 */
import { num } from "@/lib/api";

export const CATEGORII = {
  CONT_CURENT: "Conturi & pachete", CONT_OPERATIUNI: "Operațiuni & plăți",
  CARDURI_ACQUIRING: "Carduri & POS", CREDIT_CAPITAL_LUCRU: "Credite & linii",
  CREDIT_INVESTITII: "Investiții & imobiliare", DEPOZITE: "Depozite",
  FX_HEDGING: "Schimb valutar", TRADE_FINANCE: "Garanții & acreditive",
};
export const SCURT = {
  libra: "Libra", bcr: "BCR", raiffeisen: "Raiffeisen", brd: "BRD", ing: "ING", "banca-transilvania": "BT",
};
export const MOTIV = {
  produs_inexistent: "banca nu are produsul", nepublicat: "nu îl publică pe site",
  nu_am_gasit: "negăsit pe site", potrivire_slaba: "fără echivalent sigur",
};
// etichetele de scenariu fără spațiu și fără diacritice sunt de regulă bucăți din codul
// scenariului („od”, „cl”, „0”); doar acestea câteva sunt lizibile
const ETICHETE_LIZIBILE = new Set(["standard", "Premium", "gold", "extra", "plus", "optim", "start-up", "lunar", "Max"]);

// potrivirea cu scenariul de referință (referinte_libra.json); „nespecificat” nu primește etichetă
const REF = {
  exact: { t: "referință", cls: "ref" }, aproximativ: { t: "≈ referință", cls: "ref ap" },
  alt: { t: "alt exemplu", cls: "alt" },
};
export const REF_TEXT = {
  exact: "este chiar scenariul de referință",
  aproximativ: "e foarte aproape de scenariul de referință",
  alt: "e pentru alt exemplu decât scenariul de referință: nu o compara direct cu celelalte",
  nespecificat: "documentul nu spune pentru ce sumă / perioadă / valută e: nu se știe dacă e scenariul de referință",
};
const RANG = { exact: 0, aproximativ: 1, nespecificat: 3, alt: 4 };
// întâi valorile pe scenariul de referință, apoi cele fără scenariu, la urmă alte exemple
export const rang = v => { const r = v.scenariu && v.scenariu.referinta; return r ? RANG[r.potrivire] : 2; };

const VALUTA_IC = { EUR: "euro", USD: "dolar", GBP: "lira", RON: "bancnota" };
function iconitaEticheta(x) {
  if (/asigur/i.test(x)) return "scut";
  if (/salariu/i.test(x)) return "servieta";
  if (/venit/i.test(x)) return "portofel";
  if (/perioad|luni|\ban\b/i.test(x)) return "calendar";
  if (/străin/i.test(x)) return "glob";
  if (/client nou/i.test(x)) return "clientNou";
  if (/premium|gold|max/i.test(x)) return "coroana";
  return "eticheta";
}

export function valoare(v) {
  if (v.valoare === null || v.valoare === undefined) return v.valoare_text || "—";
  const u = { "%": "%", pp: " pp", lei: " lei", eur: " EUR", usd: " USD", luni: " luni", ani: " ani",
    zile: " zile", numar: "" }[v.unitate];
  return num(v.valoare) + (u !== undefined ? u : (v.unitate ? " " + v.unitate : ""));
}

const ePromo = (s, v) => /promo/i.test([(s && s.cod) || "", ((s && s.etichete) || []).join(" "),
  (v && v.conditie) || ""].join(" "));

// etichetele de scenariu: {t: text, ic: iconiță, cls: clasă}; oferta e prima, ca să sară în ochi
export function etichete(s, v) {
  const e = [];
  if (ePromo(s, v)) e.push({ t: "Ofertă", ic: "oferta", cls: "of" });
  if (!s) return e;
  const ref = s.referinta && REF[s.referinta.potrivire];
  if (ref) e.push({ t: ref.t, ic: "tinta", cls: ref.cls });
  if (s.varianta) e.push({ t: s.varianta, ic: "straturi", cls: "var" });
  const bani = (n, m) => `${num(n, 0)} ${m === "EUR" ? "EUR" : m === "USD" ? "USD" : "lei"}`;
  if (s.valuta) { const c = s.valuta === "LEI" ? "RON" : s.valuta; e.push({ t: c, ic: VALUTA_IC[c] || "monede", cls: "val" }); }
  if (s.suma != null) e.push({ t: s.suma_max != null ? `${bani(s.suma, s.moneda)} – ${bani(s.suma_max, s.moneda)}`
    : bani(s.suma, s.moneda), ic: "monede" });
  if (s.perioada_luni != null) e.push({ t: `${s.perioada_luni} ${s.perioada_luni === 1 ? "lună" : "luni"}`, ic: "calendar" });
  if (s.perioada_zile != null) e.push({ t: `${s.perioada_zile} ${s.perioada_zile === 1 ? "zi" : "zile"}`, ic: "calendar" });
  if (s.fix_ani != null) e.push({ t: `fix ${s.fix_ani} ${s.fix_ani === 1 ? "an" : "ani"}`, ic: "lacat" });
  if (s.venit_min != null) e.push({ t: `venit ≥ ${num(s.venit_min, 0)} lei`, ic: "portofel" });
  (s.etichete || []).filter(x => x !== s.varianta && !/promo/i.test(x)
    && (/ /.test(x) || /[^ -~]/.test(x) || ETICHETE_LIZIBILE.has(x)))
    .slice(0, 3).forEach(x => e.push({ t: x, ic: iconitaEticheta(x) }));
  if (s.derivat) e.push({ t: "calculat", ic: "calculator", cls: "der" });
  return e;
}

// condițiile citite din document, fără codul de scenariu și fără valuta (afișate separat)
export function conditie(v) {
  let c = v.conditie || "";
  const cod = v.scenariu && v.scenariu.cod;
  if (cod && c.startsWith(cod)) c = c.slice(cod.length).replace(/^;\s*/, "");
  return c.replace(/^valuta [A-Z]{3};?\s*/, "");
}

export function vizibila(v, stare) {
  if (stare.amb === "1" && v.ambiguu) return false;
  if (stare.low === "1" && v.incredere != null && v.incredere < 0.85) return false;
  const ref = v.scenariu && v.scenariu.referinta;
  if (stare.ref === "1" && ref && (ref.potrivire === "alt" || ref.potrivire === "nespecificat")) return false;
  return true;
}
