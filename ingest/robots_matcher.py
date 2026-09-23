"""
Matcher robots.txt conform RFC 9309, ca inlocuitor pentru
urllib.robotparser (biblioteca standard).

De ce nu urllib.robotparser: face doar potrivire pe prefix simplu, deci
rateaza complet tipare cu wildcard, ex. `Disallow: *.pdf` -- ratezi
sistematic documente interzise explicit, fara nicio eroare vizibila.

Reguli implementate (RFC 9309 §2.2.2):
  - `*` in tipar potriveste orice secventa de caractere (inclusiv nimic)
  - `$` la finalul tiparului ancoreaza la finalul caii
  - regula cea mai specifica (tiparul cel mai lung, ca text brut) castiga;
    la egalitate de lungime, Allow castiga in fata lui Disallow
  - grupul de user-agent se alege dupa potrivire exacta de token
    (case-insensitive); daca nu exista, se foloseste grupul `*`
  - fara nicio regula potrivita -> allow implicit
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class _Rule:
    pattern: str
    allow: bool
    regex: re.Pattern


@dataclass
class _Group:
    user_agents: list[str]
    rules: list[_Rule] = field(default_factory=list)
    crawl_delay: float | None = None


@dataclass
class RobotRules:
    groups: list[_Group] = field(default_factory=list)


def _pattern_to_regex(pattern: str) -> re.Pattern:
    anchored = pattern.endswith("$")
    core = pattern[:-1] if anchored else pattern
    parts = core.split("*")
    escaped = ".*".join(re.escape(p) for p in parts)
    if anchored:
        escaped += "$"
    return re.compile("^" + escaped)


def parse(text: str) -> RobotRules:
    groups: list[_Group] = []
    current: _Group | None = None
    # un bloc de User-agent consecutive (fara reguli intre ele) formeaza un
    # singur grup, cu toate directivele care urmeaza pana la urmatorul bloc
    expecting_agents = True

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field_name, _, value = line.partition(":")
        field_name = field_name.strip().lower()
        value = value.strip()

        if field_name == "user-agent":
            if current is None or not expecting_agents:
                current = _Group(user_agents=[])
                groups.append(current)
                expecting_agents = True
            current.user_agents.append(value.lower())
        elif field_name in ("allow", "disallow"):
            if current is None:
                continue
            expecting_agents = False
            if value == "" and field_name == "disallow":
                # "Disallow:" gol == nicio restrictie (echivalent Allow: /)
                continue
            current.rules.append(_Rule(pattern=value, allow=(field_name == "allow"), regex=_pattern_to_regex(value)))
        elif field_name == "crawl-delay":
            if current is None:
                continue
            expecting_agents = False
            try:
                current.crawl_delay = float(value)
            except ValueError:
                pass
        else:
            if current is not None:
                expecting_agents = False

    return RobotRules(groups=groups)


def _select_group(rules: RobotRules, user_agent: str) -> _Group | None:
    ua_token = user_agent.lower()
    wildcard_group = None
    for group in rules.groups:
        for agent in group.user_agents:
            if agent == "*":
                wildcard_group = wildcard_group or group
            elif agent in ua_token or ua_token in agent:
                return group
    return wildcard_group


def can_fetch(rules: RobotRules, user_agent: str, path: str) -> bool:
    group = _select_group(rules, user_agent)
    if group is None:
        return True

    best_len = -1
    best_allow = True
    for rule in group.rules:
        if rule.regex.match(path):
            length = len(rule.pattern)
            if length > best_len or (length == best_len and rule.allow):
                best_len = length
                best_allow = rule.allow
    return best_allow


def get_crawl_delay(rules: RobotRules, user_agent: str) -> float | None:
    group = _select_group(rules, user_agent)
    if group is None:
        return None
    return group.crawl_delay
