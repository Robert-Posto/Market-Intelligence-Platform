"""Rulează fiecare pagină a aplicației în V8, cu date reale din API.

De ce există: o eroare de JavaScript lasă pagina complet albă, iar din
terminal arată identic cu „serverul merge" — serverul CHIAR merge, răspunde
200, doar că browserul nu poate executa scriptul. Exact așa a stat aplicația
moartă după o refactorizare: un ghilimet ASCII într-un șir delimitat cu
ghilimele închidea șirul devreme, iar tot blocul `<script>` cădea la parsare.
Verificarea de sintaxă din Python nu o prindea (parserele pure-Python nu
cunosc sintaxă modernă), iar fără browser nu se vedea nimic.

Scriptul face ce ar face un om care deschide fiecare pagină:
  1. parsează blocul <script> într-un V8 adevărat
  2. pune în locul DOM-ului și al lui `fetch` niște cioturi minime, iar
     `fetch` întoarce răspunsuri REALE, luate din serverul care rulează
  3. apelează fiecare renderer `R.<pagina>` și verifică că întoarce HTML

Rulare:  python app/verifica_pagini.py        (serverul trebuie pornit)
"""

import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from py_mini_racer import MiniRacer

AICI = os.path.dirname(os.path.abspath(__file__))
BAZA = os.environ.get("MIP_URL", "http://localhost:8765")

# Cioturi: doar cât să treacă inițializarea de top-level a paginii. Nu
# simulează un browser - dacă un renderer chiar are nevoie de DOM, se vede
# imediat ca eroare, ceea ce e tot un rezultat util.
CIOTURI = """
var __erori = [];
function __el(){ return {
  innerHTML: "", textContent: "", value: "", style: {},
  classList: {add: function(){}, remove: function(){}, contains: function(){return false;}},
  appendChild: function(){}, setAttribute: function(){}, addEventListener: function(){},
  selectedOptions: [], onclick: null, onchange: null,
}; }
var document = {
  getElementById: __el, querySelector: __el, querySelectorAll: function(){ return []; },
  createElement: __el, addEventListener: function(){}, title: "",
  body: __el(), documentElement: __el(),
};
var window = {addEventListener: function(){}, matchMedia: function(){ return {matches:false, addEventListener:function(){}}; }};
var location = {hash: "", search: "", href: ""};
var navigator = {userAgent: "verificare"};
var localStorage = {getItem: function(){return null;}, setItem: function(){}};
function URLSearchParams(x){
  this.toString = function(){ return ""; };
  this.get = function(){ return null; };
  this.entries = function(){ return []; };
}
"""


def offset(html, cod):
    """Câte linii sunt înaintea blocului <script>, ca să raportăm linia reală."""
    return html[:html.find(cod)].count("\n")


def localizeaza(cod, off, err):
    """Găsește bucata care nu se parsează, când V8 nu dă numărul liniei.

    Pentru o greșeală de șir (un ghilimet de închidere ASCII pus în loc de ” în
    interiorul unui șir delimitat cu ghilimele), V8 raportează doar
    „Unknown JavaScript error during parse", fără poziție — iar pagina rămâne
    complet albă. Fără localizare, singura variantă e căutarea manuală prin
    1.500 de linii; s-a întâmplat de două ori.

    Scriptul se taie în bucăți la declarațiile de la începutul liniei și se
    încearcă fiecare separat, învelită în funcție, ca o bucată incompletă
    sintactic să nu producă alarme false.
    """
    linii = cod.split("\n")
    start = sorted(set([0] + [
        i for i, l in enumerate(linii)
        if re.match(r"^(const |let |var |function |async function |R\.\w+\s*=|"
                    r"document\.|window\.|/\*)", l)
    ]))
    bucati = [(start[k], start[k + 1] if k + 1 < len(start) else len(linii))
              for k in range(len(start))]
    v8 = MiniRacer()
    gasit = False
    for a, b in bucati:
        frag = "\n".join(linii[a:b])
        try:
            v8.eval("(function(){" + frag + "\n})")
        except Exception:
            gasit = True
            err.write(f"BUCATA CARE NU SE PARSEAZĂ — liniile {off + a + 1}–{off + b}:\n")
            for k in range(a, min(b, a + 18)):
                err.write(f"  {off + k + 1:5d} | {linii[k]}\n")
            # cea mai frecventă cauză, verificată doar în bucata vinovată:
            for k in range(a, b):
                if "„" in linii[k]:
                    dupa = linii[k].split("„", 1)[1]
                    pa, pc = dupa.find('"'), dupa.find("”")
                    if pa >= 0 and (pc < 0 or pa < pc):
                        err.write(f"  ^ probabil linia {off + k + 1}: după „ apare un "
                                  f'ghilimet ASCII (") în loc de ”, care închide șirul devreme\n')
            err.write("\n")
    if not gasit:
        err.write("Bisecția nu a izolat bucata — greșeala e la îmbinarea dintre bucăți.\n")


def ia_api(cale):
    try:
        with urllib.request.urlopen(BAZA + cale, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        return {"eroare": f"{exc.__class__.__name__}: {exc}"}


def main():
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", write_through=True)
    html = io.open(os.path.join(AICI, "index.html"), encoding="utf-8").read()
    cod = re.search(r"<script>([\s\S]*?)</script>", html).group(1)
    pagini = re.findall(r'\{id:"(\w+)"', html)

    v8 = MiniRacer()
    v8.eval(CIOTURI)
    try:
        v8.eval(cod)
    except Exception as exc:
        err.write(f"EȘEC LA PARSARE/INIȚIALIZARE: {exc}\n")
        err.write("Pagina ar fi complet albă în browser.\n\n")
        localizeaza(cod, offset(html, cod), err)
        return 1
    err.write("scriptul se parsează și se inițializează\n\n")

    # `fetch` întoarce date reale: pagina se testează pe ce va vedea omul, nu
    # pe date inventate care ar putea ascunde exact cazul care crapă.
    cerute = []

    def punte(cale):
        cerute.append(cale)
        return json.dumps(ia_api(cale), ensure_ascii=False, default=str)

    # MiniRacer nu expune callback-uri Python, deci se pre-încarcă răspunsurile
    # într-un dicționar și `fetch` doar caută în el. Rutele cerute se
    # descoperă din cod, cu parametrii impliciți ai fiecărei pagini.
    rute = sorted(set(re.findall(r'ia\(\s*[`"\']([^`"\'$]*)', cod)))
    fixe = ["/api/banci", "/api/logos", "/api/stare", "/api/mobil", "/api/indici",
            "/api/sentiment", "/api/istoric", "/api/versus_extra", "/api/locatii",
            "/api/surse?limit=300&banca=&stare=&rol=", "/api/coada?limit=250&motiv=&banca=",
            "/api/matrice?grup=cont_curent&segment=pf&unitate=lei",
            "/api/matrice?grup=carduri&segment=pf&unitate=lei",
            "/api/matrice?grup=transferuri&segment=pf&unitate=lei",
            "/api/rate?categorie=depozite", "/api/rate?categorie=credite",
            "/api/rate?categorie=conturi_carduri", "/api/sumar"]
    cache = {}
    for r in sorted(set(rute + fixe)):
        if r.startswith("/api/"):
            cache[r] = ia_api(r)

    v8.eval("var __cache = " + json.dumps(cache, ensure_ascii=False, default=str) + ";")
    # Se înlocuiește `fetch`, nu `ia`: `ia` e declarat `const` în pagină, deci
    # o reatribuire ar arunca. Ciotul intră exact unde intră și rețeaua, deci
    # se testează inclusiv tratarea erorilor din `ia`.
    v8.eval("""
    var __lipsa = [];
    function __caut(u){
      if(__cache[u] !== undefined) return __cache[u];
      // potrivire pe prefixul de rută, ca parametrii impliciți să nu blocheze
      var cale = String(u).split("?")[0];
      for(var k in __cache){ if(k.split("?")[0] === cale) return __cache[k]; }
      __lipsa.push(String(u));
      return {};
    }
    fetch = function(u){
      var d = __caut(u);
      return Promise.resolve({ ok: true, status: 200,
        json: function(){ return Promise.resolve(d); } });
    };
    """)

    rezultate, esecuri = [], 0
    for p in pagini:
        v8.eval("var __r = null, __e = null;")
        try:
            v8.eval(f"""
            (function(){{
              try {{
                var out = R["{p}"]({{}});
                if(out && typeof out.then === "function"){{
                  out.then(function(x){{ __r = x; }}, function(e){{ __e = String(e && e.stack || e); }});
                }} else {{ __r = out; }}
              }} catch(e) {{ __e = String(e && e.stack || e); }}
            }})();
            """)
            # Rendererele sunt `async`, deci rezultatul apare după ce se golește
            # coada de microtask-uri. Fiecare `eval` o pompează, iar lanțul are
            # mai multe `await` (Promise.all peste 3-5 cereri), deci se pompează
            # de mai multe ori până se stabilizează.
            for _ in range(40):
                v8.eval("0")
                if v8.eval("__e !== null || __r !== null"):
                    break
            e = v8.eval("__e")
            r = v8.eval("__r")
            if e:
                esecuri += 1
                rezultate.append((p, "EROARE", str(e)[:180]))
            elif r:
                rezultate.append((p, "OK", f"{len(str(r))} caractere HTML"))
            else:
                rezultate.append((p, "NEDETERMINAT", "promisiune nerezolvată în V8"))
        except Exception as exc:
            esecuri += 1
            rezultate.append((p, "EROARE", f"{exc.__class__.__name__}: {exc}"[:180]))

    for p, stare, detaliu in rezultate:
        marcaj = {"OK": "  ok  ", "EROARE": " EȘEC ", "NEDETERMINAT": "  ??  "}[stare]
        err.write(f"[{marcaj}] {p:12s} {detaliu}\n")

    lipsa = v8.eval("JSON.stringify(__lipsa)")
    if lipsa and lipsa != "[]":
        err.write(f"\nrute cerute și neîncărcate în cache: {lipsa}\n")

    # Harta e o pagină separată, cu propriul script. Nu se poate randa aici
    # (are nevoie de MapLibre și de un canvas real), dar se poate verifica cel
    # puțin că scriptul ei se parsează — adică exact greșeala care lasă o
    # pagină complet albă.
    for nume in ("harta.html",):
        cale = os.path.join(AICI, nume)
        if not os.path.exists(cale):
            continue
        h2 = io.open(cale, encoding="utf-8").read()
        blocuri = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>", h2)
        for i, b in enumerate(blocuri):
            try:
                MiniRacer().eval("(function(){" + b + "\n})")
                err.write(f"[  ok  ] {nume} bloc {i}: se parsează\n")
            except Exception as exc:
                esecuri += 1
                err.write(f"[ EȘEC ] {nume} bloc {i}: {exc}\n")
                localizeaza(b, offset(h2, b), err)

    err.write(f"\n{esecuri} pagini cu erori din {len(pagini)}\n")
    return 1 if esecuri else 0


if __name__ == "__main__":
    sys.exit(main())
