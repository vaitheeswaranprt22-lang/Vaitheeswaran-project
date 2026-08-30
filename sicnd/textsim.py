# -*- coding: utf-8 -*-
"""
String similarity and phonetic keying tuned for Indian names.

Why not Soundex/Metaphone: they are built for English orthography and actively
mangle Indian transliterations. Soundex('Mohammed')='M530' and
Soundex('Muhammad')='M530' happens to work, but Soundex('Choudhary')='C363' vs
Soundex('Chowdhury')='C363' works by luck while Soundex('Bhattacharya')='B326'
vs Soundex('Bhattacharjee')='B326'... and then Soundex('Nair')='N600' collides
with 'Nayar'='N600' but also with half the N-surnames in the corpus.

The real problem in Indian records is a small, well-understood set of
transliteration alternations (aspirated consonants written with or without 'h',
v/w, j/z, ee/i, oo/u, doubled consonants). Normalising those directly is more
precise than a generic English phonetic algorithm.
"""

from __future__ import annotations
import re
import unicodedata
from functools import lru_cache

_PUNCT = re.compile(r"[^a-z\s]")
_WS = re.compile(r"\s+")

# Extremely common abbreviated given names in Indian records. These are written
# forms of the same name, not similar names, so they are folded before keying.
_ABBREV = {
    "md": "mohammed", "mohd": "mohammed", "mohammad": "mohammed",
    "muhammad": "mohammed", "mohamed": "mohammed", "muhammed": "mohammed",
    "sk": "sheikh", "shk": "sheikh", "sd": "sayyed", "syed": "sayyed",
    "abd": "abdul", "abdool": "abdul", "krishnan": "krishna", "kishan": "krishna",
}

# Ordered alternations. ORDER IS LOad-BEARING:
#   vowel digraphs must run before w->v, or "chowdhury" turns into "covdhury"
#   and stops matching "choudhary"; consonant digraphs must run before the
#   single-letter substitutions for the same reason.
_ALTERNATIONS = [
    # 1. vowel digraphs
    ("aa", "a"), ("ee", "i"), ("ie", "i"), ("oo", "u"), ("ou", "u"),
    ("ow", "u"), ("au", "o"), ("ai", "e"), ("ay", "e"), ("ey", "e"),
    ("iy", "i"), ("uy", "u"),
    # 2. consonant digraphs (aspirates written with or without 'h')
    ("ph", "f"), ("bh", "b"), ("dh", "d"), ("gh", "g"), ("jh", "j"),
    ("kh", "k"), ("th", "t"), ("ch", "c"), ("sh", "s"), ("zh", "j"),
    ("ck", "k"), ("qu", "k"),
    # 3. single letters
    ("x", "ks"), ("q", "k"), ("w", "v"), ("z", "j"), ("y", "i"),
]


def normalize(s: str) -> str:
    """Lowercase, strip accents and punctuation, collapse whitespace."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace(".", " ").replace("-", " ").replace("'", "")
    s = _PUNCT.sub(" ", s)
    return _WS.sub(" ", s).strip()


@lru_cache(maxsize=100_000)
def phonetic_key(token: str) -> str:
    """
    Collapse a single name token to a transliteration-invariant key.
    Mohammed / Mohammad / Muhammad / Mohd -> same key.
    """
    t = normalize(token).replace(" ", "")
    if not t:
        return ""
    t = _ABBREV.get(t, t)
    for a, b in _ALTERNATIONS:
        t = t.replace(a, b)
    # collapse doubled letters
    out = []
    for ch in t:
        if not out or out[-1] != ch:
            out.append(ch)
    t = "".join(out)
    # keep the leading letter, drop interior vowels (they are the least stable
    # part of any transliteration)
    if len(t) > 1:
        t = t[0] + re.sub(r"[aeiou]", "", t[1:])
    return t or normalize(token)[:1]


@lru_cache(maxsize=100_000)
def phonetic_variants(token: str) -> frozenset:
    """
    A *set* of keys at decreasing precision. Blocking on any shared key gives
    recall on tails that differ (Bhattacharya / Bhattacharjee -> both 'btcr' at
    length 4) without forcing one coarse key on everything.
    """
    k = phonetic_key(token)
    if not k:
        return frozenset()
    out = {k}
    if len(k) > 4:
        out.add(k[:4])
    if len(k) > 3:
        out.add(k[:3])
    return frozenset(out)


def name_key(name: str) -> str:
    """Order-independent phonetic key for a full name (handles swapped order)."""
    toks = [phonetic_key(t) for t in normalize(name).split() if len(t) > 1]
    return " ".join(sorted(k for k in toks if k))


# --------------------------------------------------------------------------
# Jaro / Jaro-Winkler
# --------------------------------------------------------------------------
def jaro(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    l1, l2 = len(s1), len(s2)
    if l1 == 0 or l2 == 0:
        return 0.0
    window = max(l1, l2) // 2 - 1
    if window < 0:
        window = 0
    f1 = [False] * l1
    f2 = [False] * l2
    matches = 0
    for i in range(l1):
        lo = max(0, i - window)
        hi = min(i + window + 1, l2)
        for j in range(lo, hi):
            if f2[j] or s1[i] != s2[j]:
                continue
            f1[i] = f2[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0
    k = 0
    transpositions = 0
    for i in range(l1):
        if not f1[i]:
            continue
        while not f2[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    transpositions //= 2
    return (matches / l1 + matches / l2 +
            (matches - transpositions) / matches) / 3.0


def jaro_winkler(s1: str, s2: str, p: float = 0.1, max_prefix: int = 4) -> float:
    j = jaro(s1, s2)
    if j < 0.7:
        return j
    prefix = 0
    for a, b in zip(s1[:max_prefix], s2[:max_prefix]):
        if a != b:
            break
        prefix += 1
    return j + prefix * p * (1 - j)


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def edit_ratio(a: str, b: str) -> float:
    m = max(len(a), len(b))
    return 1.0 - levenshtein(a, b) / m if m else 1.0


# --------------------------------------------------------------------------
# Name-level comparison
# --------------------------------------------------------------------------
def token_set_similarity(a: str, b: str) -> float:
    """
    Best-pairing token similarity. Order independent, tolerant of a dropped
    surname or an initial standing in for a given name.
    """
    ta = [t for t in normalize(a).split() if t]
    tb = [t for t in normalize(b).split() if t]
    if not ta or not tb:
        return 0.0
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    used = set()
    total = 0.0
    for t in short:
        best, best_j = 0.0, -1
        for j, u in enumerate(long_):
            if j in used:
                continue
            # an initial matches any token starting with the same letter
            if len(t) == 1 or len(u) == 1:
                s = 0.85 if t[0] == u[0] else 0.0
            else:
                s = jaro_winkler(t, u)
                if s < 0.9 and phonetic_key(t) == phonetic_key(u):
                    s = max(s, 0.92)
            if s > best:
                best, best_j = s, j
        if best_j >= 0:
            used.add(best_j)
        total += best
    # Penalise unmatched extra tokens, but only mildly -- a dropped surname is
    # a routine record-keeping variation, not evidence of a different person.
    coverage = len(short) / len(long_)
    return (total / len(short)) * (0.80 + 0.20 * coverage)


def name_similarity(a: str, b: str) -> float:
    """Combined surface + phonetic name similarity in [0, 1]."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    surface = max(token_set_similarity(na, nb),
                  jaro_winkler(na.replace(" ", ""), nb.replace(" ", "")))
    phon = 1.0 if name_key(a) == name_key(b) else edit_ratio(name_key(a), name_key(b))
    return 0.72 * surface + 0.28 * phon
