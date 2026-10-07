"""Garda pentru destinația unei cereri spre exterior: adresa trebuie să ducă
în internetul public, nu în rețeaua băncii.

De ce există: serverul și colectoarele rulează în rețeaua internă (172.16.x),
iar adresele pe care le cerem nu le alegem doar noi. Tabela `surse` ține și
adrese propuse de model și documente de pe alte domenii, iar orice bancă poate
răspunde cu un 302. Fără gardă, ruta /pdf urma redirectul spre 127.0.0.1, spre
169.254.169.254 (metadatele mașinii) sau spre un server intern, și întorcea
răspunsul prin noi (auditul de securitate, B3/B4).

Regula: doar http și https; gazda se rezolvă și adresa se refuză dacă ORICARE
dintre IP-uri nu e public. Un nume care dă și o adresă publică, și una internă
se refuză întreg: clientul HTTP o poate alege pe oricare.

Se verifică fiecare pas al unui redirect, nu doar adresa de plecare. Cine
cere (transport, server, extractor) apelează `verifica` înainte de fiecare pas.
"""

import ipaddress
import socket
from urllib.parse import urlparse

# Rezolvitorul de nume. Testele îl înlocuiesc (fără rețea reală): fie
# `mock.patch.object(destinatie, "rezolva", ...)`, fie `verifica(url, rezolvitor)`.
rezolva = socket.getaddrinfo

# CGNAT: nici privat, nici public. `is_global` îl exclude, dar îl numim explicit
# ca regula să nu depindă de definiția din versiunea de Python.
_CGNAT = ipaddress.ip_network("100.64.0.0/10")
# NAT64: 64:ff9b::7f00:1 ajunge, prin traducere, la 127.0.0.1.
_NAT64 = ipaddress.ip_network("64:ff9b::/96")


class DestinatieInterzisa(ValueError):
    """Adresa nu se cere: altă schemă decât http(s) sau o gazdă care nu e publică."""


class DestinatieNerezolvata(ConnectionError):
    """Numele nu s-a putut rezolva acum, deci nu s-a putut verifica; nu s-a
    trimis nicio cerere. E o eroare de rețea (se poate reîncerca), nu un refuz:
    o adresă de bancă cu DNS-ul căzut o clipă nu se exclude definitiv."""


def adresa_publica(ip):
    """True doar pentru un IP rutabil în internetul public."""
    ip = ipaddress.ip_address(str(ip).split("%", 1)[0])   # fără zona IPv6 (fe80::1%12)
    if ip.version == 6:
        # ::ffff:127.0.0.1 e tot 127.0.0.1
        if ip.ipv4_mapped is not None:
            return adresa_publica(ip.ipv4_mapped)
        if ip in _NAT64:
            return adresa_publica(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
    # `is_global` singur nu ajunge: pe Python 3.14, 224.0.0.1 și ff02::1
    # (multicast) și ::7f00:1 (rezervat) sunt „globale”.
    return (ip.is_global and ip not in _CGNAT
            and not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
                     or ip.is_reserved or ip.is_unspecified))


def verifica(url, rezolvitor=None):
    """Nimic dacă `url` se poate cere; altfel `DestinatieInterzisa` (nu se cere)
    sau `DestinatieNerezolvata` (numele nu se rezolvă acum).

    Risc asumat, DNS rebinding: clientul HTTP rezolvă numele din nou când se
    conectează, deci un DNS ostil poate da aici o adresă publică și la conectare
    una internă. IP-ul nu se fixează: ar cere un adaptor propriu și pentru
    requests, și pentru httpx (conectare la IP cu SNI și certificat pe nume).
    Atacatorul ar trebui să controleze DNS-ul unui domeniu deja aflat în `surse`
    sau în lanțul de redirecturi al unei bănci.
    """
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise DestinatieInterzisa(f"schemă nepermisă: {p.scheme or '(lipsă)'}")
    # `@`, `\` sau spații în autoritate: urllib, requests și httpx pot citi gazde
    # diferite din aceeași adresă (http://a.ro\@127.0.0.1/), iar garda ar
    # verifica alta decât cea la care se conectează clientul
    if "@" in p.netloc or "\\" in p.netloc or any(c.isspace() or ord(c) < 32 for c in p.netloc):
        raise DestinatieInterzisa(f"gazdă ambiguă: {p.netloc[:80]!r}")
    gazda = p.hostname
    if not gazda:
        raise DestinatieInterzisa("adresă fără gazdă")
    try:
        port = p.port or (443 if p.scheme == "https" else 80)
    except ValueError:
        raise DestinatieInterzisa(f"port invalid: {p.netloc[:80]!r}") from None
    try:
        literal = ipaddress.ip_address(gazda.split("%", 1)[0])
    except ValueError:
        literal = None
    if literal is not None:
        if not adresa_publica(literal):
            raise DestinatieInterzisa(f"adresă care nu e publică: {gazda}")
        return
    try:
        adrese = {i[4][0] for i in (rezolvitor or rezolva)(gazda, port, type=socket.SOCK_STREAM)}
    except (OSError, UnicodeError) as exc:
        raise DestinatieNerezolvata(f"{gazda} nu se rezolvă ({type(exc).__name__})") from None
    if not adrese:
        raise DestinatieNerezolvata(f"{gazda} nu se rezolvă (nicio adresă)")
    interne = sorted(a for a in adrese if not adresa_publica(a))
    if interne:
        raise DestinatieInterzisa(f"{gazda} duce la o adresă care nu e publică ({interne[0]})")
