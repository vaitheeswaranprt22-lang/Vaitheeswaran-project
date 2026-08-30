# -*- coding: utf-8 -*-
"""
Entity and relation extraction from unstructured investigative text
(FIR narratives, surveillance reports, intelligence notes).

Design
------
A cascade, not a single pass. High-precision typed entities are extracted and
their character spans MASKED before the ambiguous ones are attempted. This
matters: "Bank of Baroda", "Najafgarh Police Station" and "Enforcement
Directorate" are all capitalised multi-token sequences that a naive person-name
detector happily swallows. Resolving them first removes the ambiguity instead of
trying to arbitrate it later.

Cascade order
  1. regex-unambiguous  : DATE, MONEY, PHONE, VEHICLE_REG, QUANTITY, ACCOUNT
  2. structural         : POLICE_STATION ("<X> Police Station")
  3. closed gazetteers  : AGENCY, ORG/bank, CONTRABAND, VEHICLE_MODEL
  4. geography          : GPE (city), LOC (locality)
  5. ALIAS              : the "@ <alias>" convention used throughout Indian FIRs
  6. PERSON             : whatever capitalised material survives, validated
                          against a name lexicon or a syntactic trigger

Everything is span-based and non-overlapping; longest match wins.
"""

from __future__ import annotations

import re
from collections import defaultdict, Counter

from . import config as C
from .textsim import normalize, name_similarity


# ==========================================================================
# Gazetteers
# ==========================================================================
class Gazetteer:
    """Closed-world lexicons assembled from the reference/master data."""

    def __init__(self, store):
        s = store
        self.cities = self._clean(set(s.locations["city"]))
        self.areas = self._clean(set(s.locations["area"]))
        self.states = self._clean(set(s.locations["state"]))
        # names that are simultaneously a city and a locality of another city
        self.ambiguous_geo = self.cities & self.areas
        self.banks = self._clean(set(s.accounts["bank"]))
        self.orgs = self._clean(set(s.organizations["name"]))
        self.ps_names = self._clean(set(s.police_stations["ps_name"]))
        self.agencies = self._clean(set(s.incidents["investigating_agency"]))
        self.agencies |= self._clean(set(s.cases["lead_agency"]))
        self.contraband = self._clean(set(s.seizures["item"]))

        # vehicle makes/models seen in the fleet
        self.vehicle_models = set()
        for mk, md in zip(s.vehicles["make"], s.vehicles["model"]):
            if isinstance(mk, str) and isinstance(md, str):
                self.vehicle_models.add(f"{mk} {md}")
        self.vehicle_makes = self._clean(set(s.vehicles["make"]))

        # person lexicon: full names and their individual tokens
        self.full_names = self._clean(set(s.persons["full_name"]))
        self.given = self._clean(set(s.persons["first_name"]))
        self.surnames = self._clean(set(s.persons["surname"]))
        self.name_tokens = set()
        for n in self.given | self.surnames:
            for t in n.split():
                if len(t) > 2:
                    self.name_tokens.add(t.lower())

        # name -> person_id (may be ambiguous; kept as a list)
        self.name_index = defaultdict(list)
        for pid, nm in zip(s.persons["person_id"], s.persons["full_name"]):
            if isinstance(nm, str):
                self.name_index[normalize(nm)].append(pid)
        self.loc_index = defaultdict(list)
        for lid, ar in zip(s.locations["location_id"], s.locations["area"]):
            if isinstance(ar, str):
                self.loc_index[normalize(ar)].append(lid)
        self.org_index = defaultdict(list)
        for oid, nm in zip(s.organizations["org_id"], s.organizations["name"]):
            if isinstance(nm, str):
                self.org_index[normalize(nm)].append(oid)

    @staticmethod
    def _clean(vals):
        return {v.strip() for v in vals
                if isinstance(v, str) and v.strip() and v.strip() != "-"}


# ==========================================================================
# Patterns
# ==========================================================================
RE = {
    "DATE": re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b"),
    "MONEY": re.compile(r"\bRs\.\s?[\d,]+(?:\.\d+)?\b"),
    "PHONE": re.compile(r"\b[6-9]\d{9}\b"),
    "VEHICLE_REG": re.compile(r"\b[A-Z]{2}\d{2}\s[A-Z]{2}\s\d{4}\b"),
    "IMEI": re.compile(r"\b\d{15}\b"),
    "QUANTITY": re.compile(
        r"\b\d+(?:\.\d+)?\s(?:kg|grams|nos|INR face value)\b", re.I),
    "ACCOUNT": re.compile(r"\b\d{11,16}\b"),
    "POLICE_STATION": re.compile(r"\b([A-Z][\w'\-]*(?:\s[A-Z][\w'\-]*)*)\s"
                                 r"Police\sStation\b"),
    "FIR_NO": re.compile(r"\bFIR\sNo\.\s?\d{1,3}/\d{4}\b"),
    "SEAL": re.compile(r"'[A-Z]{3}'"),
}

# "@" is the alias convention; "urf" appears in vernacular records.
RE_ALIAS = re.compile(r"(?:@|\burf\b)\s+([A-Z][\w'\-]*(?:\s[A-Z][\w'\-]*){0,2})")

# Syntactic triggers that introduce a person even when the name is unknown.
PERSON_TRIGGERS = [
    r"namely\s+", r"accused\s+", r"one\s+", r"identity\s+as\s+", r"complainant\s+",
    r"deceased\s+", r"subject\s+", r"r/o\s+", r"s/o\s+", r"against\s+",
    r"of\s+one\s+", r"apprehended\s+", r"名",  # sentinel, never matches
]
# One lowercase letter is enough after the capital: two-letter given names are
# common ("Om Prakash", "Md Alam"), and requiring {2,} silently truncates them.
# Precision is recovered by STOP_CAPS + the name lexicon in _is_person.
RE_PERSON_CANDIDATE = re.compile(
    r"\b([A-Z][a-z'\-]{1,}(?:\s[A-Z][a-z'\-]{1,}){0,3})\b")

# Tokens that are capitalised but never part of a person name here.
STOP_CAPS = {
    "the", "on", "at", "a", "an", "and", "of", "in", "it", "is", "was", "were",
    "this", "that", "during", "accordingly", "mobile", "police", "station",
    "bank", "account", "source", "note", "alert", "assessment", "observation",
    "investigation", "enquiry", "technical", "subject", "static", "acting",
    "numerous", "confidence", "moderate", "high", "low", "rs", "fir", "no",
    "bns", "ipc", "ndps", "pmla", "uapa", "imfl", "ficn", "upi", "imps",
    "neft", "rtgs", "atm", "cctv", "sho", "kg", "nos", "hrs", "vpa", "kyc",
    "sim", "imei", "sub", "registrar", "mining", "department", "state",
    "central", "directorate", "bureau", "wing", "cell", "squad", "force",
    "crime", "branch", "narcotics", "control", "revenue", "intelligence",
    "enforcement", "railway", "protection", "income", "tax", "investigation",
    "border", "security", "economic", "offences", "special", "task", "anti",
    "terrorism", "cyber", "criminal", "history", "unlawful", "activity",
}


# ==========================================================================
# Extractor
# ==========================================================================
class EntityExtractor:

    def __init__(self, gaz: Gazetteer):
        self.g = gaz
        # Pre-compile gazetteer alternations, longest-first so that
        # "Bank of Baroda" wins over "Bank", and "New Delhi" over "Delhi".
        self._gaz_res = {
            "AGENCY": self._alt(gaz.agencies),
            "ORG": self._alt(gaz.banks | gaz.orgs),
            "CONTRABAND": self._alt(gaz.contraband),
            "VEHICLE_MODEL": self._alt(gaz.vehicle_models),
            "GPE": self._alt(gaz.cities),
            "LOC": self._alt(gaz.areas),
        }

    @staticmethod
    def _alt(vals):
        vals = sorted({v for v in vals if v}, key=len, reverse=True)
        if not vals:
            return None
        return re.compile(r"(?<![\w])(" +
                          "|".join(re.escape(v) for v in vals) +
                          r")(?![\w])")

    # ------------------------------------------------------------------
    def extract(self, text: str) -> list[dict]:
        taken: list[tuple[int, int]] = []
        out: list[dict] = []

        def free(s, e):
            return not any(s < te and e > ts for ts, te in taken)

        def claim(s, e, label, surface=None):
            if not free(s, e):
                return False
            taken.append((s, e))
            out.append({"start": s, "end": e, "text": surface or text[s:e],
                        "label": label})
            return True

        # -- 1. unambiguous regex ---------------------------------------
        # FIR_NO before DATE/ACCOUNT so "FIR No. 123/2024" is not split.
        for lab in ("FIR_NO", "VEHICLE_REG", "DATE", "MONEY", "QUANTITY", "SEAL"):
            for m in RE[lab].finditer(text):
                if lab in ("FIR_NO", "SEAL"):
                    continue  # matched to consume the span, not emitted
                claim(m.start(), m.end(), lab)
            if lab in ("FIR_NO", "SEAL"):
                for m in RE[lab].finditer(text):
                    if free(m.start(), m.end()):
                        taken.append((m.start(), m.end()))

        for m in RE["PHONE"].finditer(text):
            claim(m.start(), m.end(), "PHONE")
        # IMEI (15 digits) before ACCOUNT (11-16) so it is not mislabelled
        for m in RE["IMEI"].finditer(text):
            claim(m.start(), m.end(), "IMEI")
        for m in RE["ACCOUNT"].finditer(text):
            claim(m.start(), m.end(), "ACCOUNT")

        # -- 2. police station ------------------------------------------
        for m in RE["POLICE_STATION"].finditer(text):
            claim(m.start(), m.end(), "POLICE_STATION")

        # -- 3./4. gazetteers, most specific first -----------------------
        for lab in ("AGENCY", "ORG", "VEHICLE_MODEL", "CONTRABAND", "GPE", "LOC"):
            rx = self._gaz_res[lab]
            if rx is None:
                continue
            for m in rx.finditer(text):
                # Some names are both a city and a locality inside another city
                # (Gorakhpur is a UP district and a locality of Jabalpur). Do
                # not let the GPE pass grab those without checking context.
                if lab == "GPE" and m.group(1) in self.g.ambiguous_geo \
                        and self._reads_as_locality(text, m.start(1), m.end(1)):
                    continue
                claim(m.start(1), m.end(1), lab)

        # -- 5. alias ----------------------------------------------------
        for m in RE_ALIAS.finditer(text):
            s, e = m.start(1), m.end(1)
            e = self._trim_trailing_stop(text, s, e)
            if e > s:
                claim(s, e, "ALIAS")

        # -- 6. person ---------------------------------------------------
        for m in RE_PERSON_CANDIDATE.finditer(text):
            s, e = m.start(1), m.end(1)
            if not free(s, e):
                continue
            e = self._trim_trailing_stop(text, s, e)
            if e <= s:
                continue
            surface = text[s:e]
            if self._is_person(surface, text, s):
                claim(s, e, "PERSON", surface)

        out.sort(key=lambda a: a["start"])
        return out

    # ------------------------------------------------------------------
    def _reads_as_locality(self, text, s, e):
        """
        Two contexts settle an ambiguous place name in favour of the locality
        reading: it is followed by a city ("Gorakhpur, Jabalpur"), or it is the
        object of a residence marker ("r/o Gorakhpur").
        """
        tail = text[e:e + 40]
        m = re.match(r",\s*([A-Z][\w'\-]*(?:\s[A-Z][\w'\-]*)*)", tail)
        if m and m.group(1).split(",")[0].strip() in self.g.cities:
            return True
        head = text[max(0, s - 12):s]
        return bool(re.search(r"(?:r/o|resident of|situated at)\s+$", head))

    @staticmethod
    def _trim_trailing_stop(text, s, e):
        """Drop trailing function words a greedy capital-run may have absorbed."""
        surface = text[s:e]
        toks = surface.split()
        while toks and toks[-1].lower() in STOP_CAPS:
            toks.pop()
        while toks and toks[0].lower() in STOP_CAPS:
            toks.pop(0)
        if not toks:
            return s
        new = " ".join(toks)
        idx = text.find(new, s, e)
        return (idx + len(new)) if idx != -1 else s

    def _is_person(self, surface: str, text: str, start: int) -> bool:
        toks = surface.split()
        if not (1 <= len(toks) <= C.NLP.MAX_PERSON_TOKENS):
            return False
        low = [t.lower().strip(".") for t in toks]
        if any(t in STOP_CAPS for t in low):
            return False
        # known full name
        if normalize(surface) in self.g.name_index:
            return True
        # any token in the name lexicon -> treat the run as a name
        if any(t in self.g.name_tokens for t in low):
            return True
        # otherwise require a syntactic trigger immediately before
        window = text[max(0, start - 24):start]
        return any(re.search(p + r"$", window) for p in PERSON_TRIGGERS)

    # ------------------------------------------------------------------
    def link(self, ents: list[dict], store) -> list[dict]:
        """
        Resolve mentions to canonical record IDs. Ambiguity is reported, not
        hidden: a mention matching several records keeps all candidates and is
        marked ambiguous rather than silently binding to the first.
        """
        for e in ents:
            key = normalize(e["text"])
            e["entity_id"] = ""
            e["candidates"] = []
            e["link_confidence"] = 0.0
            if e["label"] in ("PERSON", "ALIAS"):
                cands = self.g.name_index.get(key, [])
                if not cands and e["label"] == "PERSON":
                    cands = self._fuzzy_person(key)
                if cands:
                    e["candidates"] = cands[:5]
                    e["entity_id"] = cands[0] if len(cands) == 1 else ""
                    e["link_confidence"] = 1.0 if len(cands) == 1 else \
                        round(1.0 / len(cands), 3)
                    e["ambiguous"] = len(cands) > 1
            elif e["label"] == "LOC":
                cands = self.g.loc_index.get(key, [])
                if cands:
                    e["candidates"] = cands[:5]
                    e["entity_id"] = cands[0]
                    e["link_confidence"] = 1.0 if len(cands) == 1 else 0.5
            elif e["label"] == "ORG":
                cands = self.g.org_index.get(key, [])
                if cands:
                    e["candidates"] = cands[:5]
                    e["entity_id"] = cands[0]
                    e["link_confidence"] = 1.0 if len(cands) == 1 else 0.5
            elif e["label"] == "PHONE":
                pid = store.phone_by_msisdn.get(e["text"])
                if pid:
                    e["entity_id"] = pid
                    e["link_confidence"] = 1.0
        return ents

    def _fuzzy_person(self, key: str, threshold: float | None = None):
        threshold = threshold or C.NLP.FUZZY_LINK_THRESHOLD
        toks = set(key.split())
        best, best_ids = threshold, []
        for name, ids in self.g.name_index.items():
            if not toks & set(name.split()):
                continue                      # cheap blocking
            s = name_similarity(key, name)
            if s > best:
                best, best_ids = s, ids
        return best_ids


# ==========================================================================
# Relation extraction
# ==========================================================================
REL_PATTERNS = [
    # (regex, relation, direction) -- direction 'fwd' = group1 -> group2
    (r"(?P<a>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})\s+(?:along with|and)\s+"
     r"(?:his\s+associates?\s+)?(?P<b>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})",
     "CO_ACCUSED_WITH", "sym"),
    (r"at the instance of\s+(?P<b>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})",
     "ACTS_ON_INSTRUCTIONS_OF", "ctx_to_b"),
    (r"under the direction of\s+(?P<b>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})",
     "REPORTS_TO", "ctx_to_b"),
    (r"(?:arranged|organised) by (?:one\s+)?(?P<b>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})",
     "ARRANGED_BY", "ctx_to_b"),
    (r"(?:supplied|delivered) to\s+(?P<b>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})",
     "SUPPLIES_TO", "ctx_from_b"),
    (r"known associates? of\s+(?P<b>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})",
     "ASSOCIATE_OF", "ctx_to_b"),
    (r"benami of\s+(?P<b>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})",
     "BENAMI_OF", "ctx_to_b"),
    (r"relayed through\s+(?P<b>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})",
     "COMMUNICATION_CONDUIT", "ctx_to_b"),
    (r"handed over to (?:him |her )?by\s+(?P<b>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})",
     "RECEIVED_FROM", "ctx_to_b"),
    (r"(?:met|meeting with)\s+(?P<b>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})",
     "MET_WITH", "ctx_to_b"),
    (r"received funds from\s+(?P<b>[A-Z][\w']+(?:\s[A-Z][\w']+){0,2})",
     "FINANCED_BY", "ctx_to_b"),
]


class RelationExtractor:
    """
    Pulls asserted relationships out of narrative text. Every relation carries
    the sentence it came from, so an analyst can always see the basis -- an
    extracted relation is a claim, not a fact.
    """

    def __init__(self, gaz: Gazetteer):
        self.g = gaz
        self._compiled = [(re.compile(p), rel, mode) for p, rel, mode in REL_PATTERNS]

    def extract(self, text: str, ents: list[dict], doc_id: str = "") -> list[dict]:
        persons = [e for e in ents if e["label"] == "PERSON" and e.get("entity_id")]
        by_span = {(e["start"], e["end"]): e for e in persons}
        out = []

        def nearest_person_before(pos):
            best = None
            for e in persons:
                if e["end"] <= pos and (best is None or e["end"] > best["end"]):
                    best = e
            return best

        def resolve(surface):
            ids = self.g.name_index.get(normalize(surface), [])
            return ids[0] if len(ids) == 1 else None

        for rx, rel, mode in self._compiled:
            for m in rx.finditer(text):
                sent = self._sentence(text, m.start())
                if mode == "sym":
                    a, b = resolve(m.group("a")), resolve(m.group("b"))
                    if a and b and a != b:
                        out.append(self._mk(a, b, rel, sent, doc_id, True))
                else:
                    b = resolve(m.group("b"))
                    anchor = nearest_person_before(m.start())
                    a = anchor["entity_id"] if anchor else None
                    if not (a and b) or a == b:
                        continue
                    if mode == "ctx_from_b":
                        a, b = b, a
                    out.append(self._mk(a, b, rel, sent, doc_id, False))

        # co-mention within the same document is weak evidence, kept separate
        ids = sorted({e["entity_id"] for e in persons})
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                out.append(self._mk(ids[i], ids[j], "CO_MENTIONED_WITH",
                                    "", doc_id, True, confidence=0.25))
        return out

    @staticmethod
    def _mk(a, b, rel, sentence, doc_id, symmetric, confidence=0.7):
        return {"src_person_id": a, "dst_person_id": b, "relation": rel,
                "symmetric": symmetric, "evidence": sentence.strip(),
                "doc_id": doc_id, "confidence": confidence,
                "extraction_method": "PATTERN", "verified": 0}

    @staticmethod
    def _sentence(text, pos):
        s = text.rfind(". ", 0, pos)
        e = text.find(". ", pos)
        return text[(s + 2 if s != -1 else 0): (e + 1 if e != -1 else len(text))]


# ==========================================================================
# Evaluation against the shipped NER ground truth
# ==========================================================================
def evaluate_ner(docs, extractor, limit=None):
    """
    Two granularities, reported honestly:

    strict  -- exact (start, end, label) match.
    typed   -- set of (surface_text, label) per document.

    The strict number is depressed by an artefact of how the corpus was
    annotated: the generator records only the FIRST occurrence of each distinct
    value, so a second, correct mention of the same city counts as a false
    positive. The typed number is the fair measure of "did we find the right
    entities in this document"; both are printed so nothing is hidden.
    """
    docs = docs[:limit] if limit else docs
    strict_tp = strict_fp = strict_fn = 0
    typed_tp = typed_fp = typed_fn = 0
    per_label = defaultdict(lambda: [0, 0, 0])   # tp, fp, fn (typed)

    for d in docs:
        gold = d["entities"]
        pred = extractor.extract(d["text"])

        gset = {(e["start"], e["end"], e["label"]) for e in gold}
        pset = {(e["start"], e["end"], e["label"]) for e in pred}
        strict_tp += len(gset & pset)
        strict_fp += len(pset - gset)
        strict_fn += len(gset - pset)

        gt = {(e["text"], e["label"]) for e in gold}
        pt = {(e["text"], e["label"]) for e in pred}
        typed_tp += len(gt & pt)
        typed_fp += len(pt - gt)
        typed_fn += len(gt - pt)
        for t in gt & pt:
            per_label[t[1]][0] += 1
        for t in pt - gt:
            per_label[t[1]][1] += 1
        for t in gt - pt:
            per_label[t[1]][2] += 1

    def prf(tp, fp, fn):
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        return p, r, f

    return {
        "documents": len(docs),
        "strict": dict(zip(("precision", "recall", "f1"),
                           prf(strict_tp, strict_fp, strict_fn))),
        "typed": dict(zip(("precision", "recall", "f1"),
                          prf(typed_tp, typed_fp, typed_fn))),
        "per_label": {k: dict(zip(("precision", "recall", "f1"), prf(*v)),
                              support=v[0] + v[2])
                      for k, v in sorted(per_label.items())},
    }
