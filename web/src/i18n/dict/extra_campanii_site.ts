/** Texte adăugate la mutarea paginii în React (în afara extragerii din 02.10.2026). */
export const extra_campanii_site = {
  // singularul lipsea: „1 comunicate” pe chip
  "campanii.comunicate.chip_tooltip_1": ["{n} comunicat · clic: filtrează lista (încă un clic: toate)", "{n} press release · click: filter the list (click again: all)"],

  // Motivele „de verificat” (ingest/normalizeaza_campanii.py), trimise de server în română și
  // lipite cu „; ”: pagina le desparte și traduce fiecare bucată prin deLaServer. Cele scurte
  // („act adițional”, „treapta B”) sunt cheile din „cele mai dese” din Despre date.
  "server.campanii.motiv.an_lipsa": ["anul lipsește din text", "the year is missing from the text"],
  "server.campanii.motiv.an_dedus": ["dedus din calea documentului", "inferred from the document's path"],
  "server.campanii.motiv.fara_cuvant": ["date fără cuvânt de perioadă în jur", "dates without a period keyword around them"],
  "server.campanii.motiv.o_singura_data": ["o singură dată în etichetă: ziua campaniei sau data publicării?", "a single date in the label: the campaign day or the publication date?"],
  "server.campanii.motiv.o_singura_data_scurt": ["o singură dată în etichetă", "a single date in the label"],
  "server.campanii.motiv.peste_3_ani": ["fereastră de peste 3 ani", "a window of more than 3 years"],
  "server.campanii.motiv.act_aditional": ["act adițional: sfârșitul poate fi modificat", "addendum: the end date may have been changed"],
  "server.campanii.motiv.act_aditional_scurt": ["act adițional", "addendum"],
  "server.campanii.motiv.neadus": ["documentul nu s-a putut aduce", "the document could not be fetched"],
  "server.campanii.motiv.neadus_verdict": ["documentul nu s-a putut aduce: {verdicte}", "the document could not be fetched: {verdicte}"],
  "server.campanii.motiv.doar_eticheta": ["fereastra doar din etichetă sau URL", "the window only from the label or URL"],
  "server.campanii.motiv.incepe_dupa": ["începe după data rulării", "starts after the run date"],
  "server.campanii.motiv.fara_termen": ["fără termen în text: „{citat}”", "no end date in the text: “{citat}”"],
  "server.campanii.motiv.fara_termen_scurt": ["fără termen în text", "no end date in the text"],
  "server.campanii.motiv.treapta_b": ["treapta B: cea mai recentă dată din text e {data}", "tier B: the most recent date in the text is {data}"],
  "server.campanii.motiv.treapta_b_scurt": ["treapta B", "tier B"],
  "server.campanii.motiv.fara_text": ["fără strat de text (PDF scanat sau pagină randată în JS)", "no text layer (scanned PDF or page rendered in JS)"],
  "server.campanii.motiv.fara_perioada": ["fără perioadă în text", "no period in the text"],

  // Motivul fiecărei bănci fără campanii (ingest/campanii_config.py, stare_banca), la hover în
  // „Băncile fără campanii”; un motiv nou, fără intrare aici, apare în română.
  "server.campanii.banca.waf": ["blocat, HTTP 403 (WAF), 24.09.2026", "blocked, HTTP 403 (WAF), 24.09.2026"],
  "server.campanii.banca.waf_intesa": ["blocat, HTTP 403 (WAF), 24.09.2026 (robots.txt permite tot, WAF-ul refuză)", "blocked, HTTP 403 (WAF), 24.09.2026 (robots.txt allows everything, the WAF refuses)"],
  "server.campanii.banca.robots_banorient": ["blocat de robots.txt: „User-agent: * / Disallow: /” (date/robots/banorient.txt, 23.09.2026)", "blocked by robots.txt: “User-agent: * / Disallow: /” (date/robots/banorient.txt, 23.09.2026)"],
  "server.campanii.banca.f5_cetelem": ["tratată ca blocată (decizia lui Robert, §9.2): robots.txt prin HTTP a întors respingerea F5 „Request Rejected” (date/robots/cetelem.txt, 23.09.2026)", "treated as blocked (Robert's decision, §9.2): robots.txt over HTTP returned the F5 rejection “Request Rejected” (date/robots/cetelem.txt, 23.09.2026)"],
  "server.campanii.banca.afara_citibank": ["în afara scopului: fără retail în România (Nicolae, §6.1)", "out of scope: no retail in Romania (Nicolae, §6.1)"],
  "server.campanii.banca.afara_bnpparibas": ["în afara scopului: sucursală corporate (Nicolae, §6.1)", "out of scope: corporate branch (Nicolae, §6.1)"],
  "server.campanii.banca.afara_bid": ["în afara scopului: fără retail (Nicolae, §6.1)", "out of scope: no retail (Nicolae, §6.1)"],
  "server.campanii.banca.afara_bankofchina": ["în afara scopului: corporate (Nicolae, §6.1)", "out of scope: corporate (Nicolae, §6.1)"],
  "server.campanii.banca.afara_pko": ["în afara scopului: piața poloneză (Nicolae, §6.1)", "out of scope: the Polish market (Nicolae, §6.1)"],
  "server.campanii.banca.revolut": ["decizie în așteptare (Nicolae, §9.2): conținut de grup, Next.js; robots.txt interzice `*?*`, `/api/`, `/*.json$`; fără nicio pagină-listă găsită", "decision pending (Nicolae, §9.2): group content, Next.js; robots.txt disallows `*?*`, `/api/`, `/*.json$`; no list page found"],
  "server.campanii.banca.reper": ["reper (banca noastră)", "reference (our bank)"],
  "server.campanii.banca.fara_config": ["fără configurație", "no configuration"],
} as const
