# -*- coding: utf-8 -*-
"""
Entity resolution: find records that may describe the same person.

THE GOVERNING RULE
------------------
This module never merges anything. It produces *proposals* with an explicit
evidence breakdown and a confidence band, and stops. Merging is an action a
human takes. That is not timidity -- it is the only defensible design when the
cost of a false merge is attributing one person's crimes to another.

The hard part is not finding similar names. It is refusing to act on them.
This dataset deliberately contains 86 pairs of *different people with identical
full names*; any system that merges on name similarity fails on all 86.

Method
------
1. BLOCKING    -- candidate pairs from cheap keys (phonetic name, birth year,
                  district, shared phone). Avoids the 1.4M-pair full comparison.
2. SCORING     -- weighted evidence, each component reported separately.
3. BANDING     -- CONFIRM / REVIEW / WEAK. None of these means "merge".
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from . import config as C
from .textsim import (name_similarity, name_key, phonetic_variants,
                      normalize, jaro_winkler)


class EntityResolver:

    def __init__(self, store, verbose: bool = True):
        self.s = store
        self.verbose = verbose
        self.records = store.persons.fillna("").to_dict("records")
        self.by_id = {r["person_id"]: r for r in self.records}
        self._phone_index = self._build_phone_index()
        self._neighbours = store.neighbours

    def _log(self, m):
        if self.verbose:
            print(f"    {m}", flush=True)

    def _build_phone_index(self) -> dict[str, set]:
        """msisdn -> everyone associated with it (registered OR merely used)."""
        idx = defaultdict(set)
        msisdn = self.s.msisdn_of
        for r in self.s.person_phone.itertuples():
            n = msisdn.get(r.phone_id)
            if n:
                idx[n].add(r.person_id)
        return idx

    def _phones_of(self, pid) -> set:
        msisdn = self.s.msisdn_of
        return {msisdn.get(p) for p in self.s.phones_of.get(pid, [])} - {None}

    # ------------------------------------------------------------------
    # 1. Blocking
    # ------------------------------------------------------------------
    def blocking_keys(self, rec) -> set[str]:
        """
        Several independent keys, because no single one survives real data.
        A pair only has to collide on ONE key to be compared properly.
        """
        keys = set()
        name = rec.get("full_name", "")
        toks = [t for t in normalize(name).split() if len(t) > 1]
        variants = [phonetic_variants(t) for t in toks]

        nk = name_key(name)
        if nk:
            keys.add("NK|" + nk)

        dob = str(rec.get("date_of_birth", ""))[:4]
        state = normalize(rec.get("native_state", ""))
        city = normalize(rec.get("native_city", ""))

        # surname-ish key crossed with birth year / place
        for vset in variants:
            for v in vset:
                if dob:
                    keys.add(f"VY|{v}|{dob}")
                if city:
                    keys.add(f"VC|{v}|{city}")
                keys.add(f"VS|{v}|{state}")

        # any shared phone number is a block on its own
        for n in self._phones_of(rec["person_id"]):
            keys.add("PH|" + n)
        return keys

    def candidate_pairs(self, max_block: int = 220) -> set[tuple]:
        blocks = defaultdict(list)
        for rec in self.records:
            for k in self.blocking_keys(rec):
                blocks[k].append(rec["person_id"])

        pairs, skipped = set(), 0
        for k, members in blocks.items():
            if len(members) < 2:
                continue
            if len(members) > max_block:
                # A block this large is a bad key (e.g. a very common surname
                # in a big state); comparing it costs more than it finds.
                skipped += 1
                continue
            for a, b in combinations(sorted(set(members)), 2):
                pairs.add((a, b))
        self._log(f"blocking: {len(blocks):,} keys -> {len(pairs):,} candidate pairs "
                  f"({skipped} oversized blocks skipped; full comparison would be "
                  f"{len(self.records) * (len(self.records) - 1) // 2:,})")
        return pairs

    # ------------------------------------------------------------------
    # 2. Scoring
    # ------------------------------------------------------------------
    def score_pair(self, a_id: str, b_id: str) -> dict:
        a, b = self.by_id[a_id], self.by_id[b_id]
        E = C.ER
        ev = {}

        ev["name_similarity"] = round(name_similarity(a["full_name"], b["full_name"]), 4)
        ev["phonetic_match"] = int(name_key(a["full_name"]) == name_key(b["full_name"]))

        # date of birth
        da, db = str(a.get("date_of_birth", "")), str(b.get("date_of_birth", ""))
        if da and db:
            if da == db:
                dob = 1.0
            else:
                try:
                    ya, yb = int(da[:4]), int(db[:4])
                    dob = 1.0 if abs(ya - yb) == 0 else (0.65 if abs(ya - yb) <= 1
                                                         else max(0.0, 1 - abs(ya - yb) / 8))
                except ValueError:
                    dob = 0.0
        else:
            dob = 0.0
        ev["dob_score"] = round(dob, 4)

        same_state = a.get("native_state") == b.get("native_state")
        same_city = a.get("native_city") == b.get("native_city")
        ev["geo_score"] = 1.0 if same_city else (0.55 if same_state else 0.0)

        aa, ab = normalize(a.get("alias", "")), normalize(b.get("alias", ""))
        ev["alias_score"] = round(jaro_winkler(aa, ab), 4) if aa and ab else 0.0

        pa, pb = self._phones_of(a_id), self._phones_of(b_id)
        shared_phones = pa & pb
        ev["shared_phones"] = sorted(shared_phones)
        ev["phone_score"] = 1.0 if shared_phones else 0.0

        na = self._neighbours.get(a_id, set())
        nb = self._neighbours.get(b_id, set())
        shared_n = (na & nb) - {a_id, b_id}
        union = (na | nb) - {a_id, b_id}
        ev["shared_neighbours"] = sorted(shared_n)[:10]
        ev["neighbour_jaccard"] = round(len(shared_n) / len(union), 4) if union else 0.0

        base = (E.W_NAME * ev["name_similarity"] +
                E.W_PHONETIC * ev["phonetic_match"] +
                E.W_DOB * ev["dob_score"] +
                E.W_GEO * ev["geo_score"] +
                E.W_ALIAS * ev["alias_score"] +
                E.W_PHONE * ev["phone_score"] +
                E.W_NEIGHBOURS * min(1.0, ev["neighbour_jaccard"] * 3))

        bonus = 0.0
        if shared_phones:
            bonus += E.BONUS_SHARED_PHONE
        if len(shared_n) >= 1:
            bonus += E.BONUS_SHARED_NEIGHBOURS * min(1.0, len(shared_n) / 2.0)

        penalty = 0.0
        # Different district AND no hard identifier in common is the signature
        # of a coincidental namesake, which this corpus is full of.
        if not same_state and not shared_phones and not shared_n:
            penalty += E.PENALTY_DIFF_DISTRICT
        if ev["dob_score"] < 0.3 and da and db:
            penalty += E.PENALTY_DOB_FAR

        score = max(0.0, min(1.0, base + bonus - penalty))

        if score >= E.CONFIRM:
            band, action = "HIGH", "PROPOSE_MERGE_PENDING_HUMAN_CONFIRMATION"
        elif score >= E.REVIEW:
            band, action = "MEDIUM", "QUEUE_FOR_ANALYST_REVIEW"
        elif score >= E.WEAK:
            band, action = "LOW", "RETAIN_AS_POSSIBLE_MATCH_ONLY"
        else:
            band, action = "REJECTED", "NO_ACTION"

        return {
            "record_a": a_id, "name_a": a["full_name"], "dob_a": da,
            "district_a": a.get("native_city", ""),
            "record_b": b_id, "name_b": b["full_name"], "dob_b": db,
            "district_b": b.get("native_city", ""),
            "match_score": round(score, 4),
            "confidence_band": band,
            "recommended_action": action,
            "auto_merged": False,          # never true, by design
            "evidence": ev,
            "explanation": self._explain(ev, score, band),
        }

    @staticmethod
    def _explain(ev, score, band):
        bits = []
        if ev["name_similarity"] > 0.9:
            bits.append("names near-identical")
        elif ev["name_similarity"] > 0.7:
            bits.append("names similar")
        if ev["phonetic_match"]:
            bits.append("same phonetic key (transliteration variant)")
        if ev["shared_phones"]:
            bits.append(f"shares phone {ev['shared_phones'][0]}")
        if ev["shared_neighbours"]:
            bits.append(f"{len(ev['shared_neighbours'])} shared associate(s)")
        if ev["dob_score"] >= 0.99:
            bits.append("identical date of birth")
        elif ev["dob_score"] < 0.3:
            bits.append("dates of birth differ materially")
        if ev["geo_score"] == 0.0:
            bits.append("different state")
        head = {"HIGH": "Strong match", "MEDIUM": "Possible match",
                "LOW": "Weak match", "REJECTED": "Not a match"}[band]
        return f"{head} ({score:.2f}): " + "; ".join(bits) + \
               ". Human confirmation required before any merge."

    # ------------------------------------------------------------------
    def resolve(self, min_band: str = "LOW") -> list[dict]:
        order = {"REJECTED": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
        floor = order[min_band]
        out = []
        for a, b in self.candidate_pairs():
            r = self.score_pair(a, b)
            if order[r["confidence_band"]] >= floor:
                out.append(r)
        out.sort(key=lambda r: -r["match_score"])
        from collections import Counter
        bands = Counter(r["confidence_band"] for r in out)
        self._log("proposals: " + "  ".join(f"{k}={v:,}" for k, v in bands.most_common())
                  + "   (auto-merges performed: 0)")
        return out


# ==========================================================================
def evaluate_resolution(proposals: list[dict], truth_df) -> dict:
    """
    Scored against the shipped duplicate ground truth, which contains true
    duplicates AND deliberate namesakes. The namesake number is the one that
    matters: it is the false-merge rate a careless system would produce.
    """
    truth = {}
    for r in truth_df.to_dict("records"):
        key = tuple(sorted((r["record_a"], r["record_b"])))
        truth[key] = r["is_same_person"] == "1"

    pos = {k for k, v in truth.items() if v}
    neg = {k for k, v in truth.items() if not v}
    by_pair = {tuple(sorted((p["record_a"], p["record_b"]))): p for p in proposals}

    def band_at_least(p, level):
        order = {"REJECTED": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
        return order[p["confidence_band"]] >= order[level]

    res = {}
    for level in ("LOW", "MEDIUM", "HIGH"):
        flagged = {k for k, p in by_pair.items() if band_at_least(p, level)}
        tp = len(flagged & pos)
        fn = len(pos - flagged)
        fp_named = len(flagged & neg)        # namesakes wrongly escalated
        prec_vs_truth = tp / (tp + fp_named) if (tp + fp_named) else 0.0
        rec = tp / len(pos) if pos else 0.0
        res[level] = {
            "true_duplicates_found": tp,
            "true_duplicates_missed": fn,
            "recall": round(rec, 4),
            "namesakes_escalated": fp_named,
            "namesakes_total": len(neg),
            "namesake_escalation_rate": round(fp_named / len(neg), 4) if neg else 0.0,
            "precision_against_labelled_pairs": round(prec_vs_truth, 4),
            "f1": round(2 * prec_vs_truth * rec / (prec_vs_truth + rec), 4)
                  if (prec_vs_truth + rec) else 0.0,
            "total_flagged_pairs": len(flagged),
        }

    res["blocking_recall"] = round(
        len(pos & set(by_pair)) / len(pos), 4) if pos else 0.0
    res["auto_merges_performed"] = sum(1 for p in proposals if p["auto_merged"])
    return res
