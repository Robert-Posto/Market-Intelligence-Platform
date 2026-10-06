#!/usr/bin/env python3
"""
preturi.py — estimarea costului unei rulări, din tokenii raportați de API.

Un singur loc pentru tabelul de prețuri: `claudeCrawl.py`, `flow-html.py` și
`ruleaza-extractie.py` îl importă de aici. Trei tabele paralele ar divergea, și
divergența nu s-ar vedea — ar ieși doar o cifră greșită.

CE E ȘI CE NU E

  E o ESTIMARE din prețurile de listă, calculată din `usage` raportat de API.
  Nu e factura. Factura reală e în consola Anthropic și poate diferi: reduceri
  negociate, Batch API la jumătate de preț, sau un preț schimbat după data din
  `ACTUALIZAT` de mai jos.

  Tokenii de intrare includ tot ce a intrat în cerere, deci și conținutul adus
  de `web_fetch` și istoricul retrimis la fiecare tură a unei bucle agentice.
  De asta discovery-ul costă mai mult decât sugerează numărul de pagini: la
  tura 8, cererea conține și turele 1-7.
"""

from __future__ import annotations

# Prețuri de listă, dolari per milion de tokeni.
ACTUALIZAT = "2026-06-24"
PRETURI = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

# Multiplicatori față de prețul de intrare.
FACTOR_CITIRE_CACHE = 0.1
FACTOR_SCRIERE_CACHE = 1.25


def cost(model: str, intrare: int = 0, iesire: int = 0,
         citire_cache: int = 0, scriere_cache: int = 0) -> float | None:
    """
    Costul în dolari. `None` dacă modelul nu e în tabel — mai bine nicio cifră
    decât una inventată.
    """
    p = PRETURI.get(model)
    if p is None:
        return None
    pi, po = p
    return (
        intrare / 1e6 * pi
        + iesire / 1e6 * po
        + citire_cache / 1e6 * pi * FACTOR_CITIRE_CACHE
        + scriere_cache / 1e6 * pi * FACTOR_SCRIERE_CACHE
    )


def aduna_usage(acc: dict, usage) -> dict:
    """
    Adună un obiect `usage` din răspunsul API în acumulatorul dat.

    Câmpurile de cache lipsesc pe unele răspunsuri, deci se citesc cu getattr.
    """
    acc["intrare"] = acc.get("intrare", 0) + (getattr(usage, "input_tokens", 0) or 0)
    acc["iesire"] = acc.get("iesire", 0) + (getattr(usage, "output_tokens", 0) or 0)
    acc["citire_cache"] = acc.get("citire_cache", 0) + (
        getattr(usage, "cache_read_input_tokens", 0) or 0)
    acc["scriere_cache"] = acc.get("scriere_cache", 0) + (
        getattr(usage, "cache_creation_input_tokens", 0) or 0)
    acc["apeluri"] = acc.get("apeluri", 0) + 1
    return acc


def formateaza(model: str, u: dict, prefix: str = "  ") -> list[str]:
    """Liniile de raport pentru stderr. Lista, ca apelantul să decidă unde merg."""
    c = cost(model, u.get("intrare", 0), u.get("iesire", 0),
             u.get("citire_cache", 0), u.get("scriere_cache", 0))
    linii = [
        f"{prefix}model                {model}",
        f"{prefix}apeluri              {u.get('apeluri', 0):>10,}",
        f"{prefix}tokeni intrare       {u.get('intrare', 0):>10,}",
        f"{prefix}tokeni iesire        {u.get('iesire', 0):>10,}",
    ]
    if u.get("citire_cache"):
        linii.append(f"{prefix}citiri din cache     {u['citire_cache']:>10,}")
    if u.get("scriere_cache"):
        linii.append(f"{prefix}scrieri in cache     {u['scriere_cache']:>10,}")
    if c is None:
        linii.append(f"{prefix}cost                 necunoscut: {model} nu e in tabel")
    else:
        linii.append(f"{prefix}cost estimat         ${c:>9.2f}"
                     f"   (preturi de lista, {ACTUALIZAT})")
    return linii


if __name__ == "__main__":
    # Sanity check pe cifre cunoscute: 1M intrare + 1M iesire pe Sonnet 5 = 12 $
    assert abs(cost("claude-sonnet-5", 1_000_000, 1_000_000) - 12.0) < 1e-9
    assert abs(cost("claude-opus-5", 1_000_000, 0) - 5.0) < 1e-9
    assert cost("model-inexistent", 1000, 1000) is None
    print("preturi.py: verificarile trec")
