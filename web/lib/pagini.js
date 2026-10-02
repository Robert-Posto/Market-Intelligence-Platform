// Registrul paginilor, copiat din app/index.html. `PORTATE` sunt deja în Next.js; restul
// se deschid în aplicația veche (app/server.py), până se portează și ele.
export const PAGINI = [
  {grup:"Colectare", chei:[
    {id:"overview",  nume:"Overview",              pdf:"",    t:"Overview", l:"Ce date avem pe fiecare categorie, cât de proaspete sunt și ce lipsește la fiecare bancă."},
    {id:"produse",   nume:"Produse & prețuri",     pdf:"2.1", t:"Produse & prețuri", l:"Fiecare produs Libra față de produsul echivalent de la concurență: valorile, scenariul la care se aplică și citatul din document. Tabul „Comisioane pe bănci” păstrează matricea pe servicii."},
    {id:"rate",      nume:"Rate & indicatori",     pdf:"2.2", t:"Rate & indicatori", l:"Dobânda tipică a fiecărei bănci, pe termen (depozite) și pe produs (credite). Clic pe o celulă pentru dovezi."},
    {id:"mobil",     nume:"Aplicații & recenzii",  pdf:"2.3", t:"Aplicații mobile & recenzii", l:"Nota, distribuția pe stele și versiunea fiecărei aplicații, plus ce spun clienții în recenzii, cu răspunsurile băncilor."},
    {id:"campanii",  nume:"Campanii & marketing",  pdf:"2.4", t:"Campanii & marketing", l:"Campaniile de pe site-urile băncilor, comunicatele de presă, reclamele din bibliotecile oficiale Google și Bing (test, până la avizul juridic) și conturile de pe rețelele sociale."},
    {id:"retea",     nume:"Rețea & operațional",   pdf:"2.5", t:"Rețea & operațional", l:"Sucursalele și ATM-urile fiecărei bănci, cu harta interactivă."},
    {id:"context",   nume:"Context de piață",      pdf:"2.6", t:"Context de piață", l:"Indicii de referință BNR: ROBOR, ROBID și IRCC."},
  ]},
  {grup:"Analiză", chei:[
    {id:"versus",  nume:"Versus Libra", pdf:"", t:"Versus Libra", l:"Libra față de până la trei bănci alese — unde câștigă, unde pierde, pe prețuri, dobânzi, aplicație, rețea și recenzii."},
    {id:"banca",   nume:"Fișă bancă", pdf:"", t:"Fișă bancă", l:"Tot ce avem despre o bancă, într-un singur loc."},
    {id:"istoric", nume:"Istoric & schimbări", pdf:"", t:"Istoric și schimbări de preț", l:"Ce și-au schimbat băncile la prețuri: același serviciu, altă dată de vigoare, altă valoare."},
  ]},
  {grup:"Date & guvernanță", chei:[
    {id:"surse",  nume:"Surse",               pdf:"", t:"Surse", l:"De unde vine fiecare cifră: ce surse avem pe fiecare bancă, care au dat date și de ce nu au dat celelalte."},
    {id:"coada",  nume:"Coadă de verificare", pdf:"", t:"Coadă de verificare umană", l:"Valori care nu se publică automat: implauzibile, ambigue sau sub pragul de încredere."},
  ]},
];

export const PORTATE = new Set(["produse"]);
export const VECHI = process.env.NEXT_PUBLIC_MIP_VECHI || "http://localhost:8765";
export const toatePag = PAGINI.flatMap(g => g.chei);
export const pagina = id => toatePag.find(p => p.id === id);
export const href = id => (PORTATE.has(id) ? `/${id}` : `${VECHI}/#/${id}`);
