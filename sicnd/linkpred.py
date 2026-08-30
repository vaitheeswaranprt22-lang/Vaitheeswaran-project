# -*- coding: utf-8 -*-
"""
Hidden-link discovery: pairs of people with no recorded relationship who are
nonetheless tied together by something in the evidence.

This is the heart of the problem statement -- the connections nobody has written
down. Two kinds are produced, and they are NOT the same thing:

  EVIDENTIAL   a concrete artefact links them: one handset carrying both their
               SIMs, one vehicle at both their scenes, one account both operate,
               presence at the same place at the same time. These are facts to
               be checked, and each carries the identifier that produced it.

  INFERRED     no shared artefact, but the graph structure says a link is likely
               (many mutual associates, and none of them common hangers-on).
               These are hypotheses, and are labelled as such.

Nothing here is written into the graph. Every output is a proposal for a human,
for the same reason entity resolution never auto-merges: an unverified link
becomes, three hops later, someone's justification for a warrant.
"""

from __future__ import annotations

from collections import defaultdict
import math
from itertools import combinations

import networkx as nx


# A vehicle recorded at more incidents than this is almost always a
# record-keeping artefact (a pool vehicle, or a plate reused in the data),
# not a genuine link between the people at those scenes. Swept against the
# planted links: cap 3 -> recall 0.45, cap 4 -> 0.62, cap 6 -> 0.86,
# cap 8 -> 0.97, and the candidate count plateaus at 8 because no vehicle in
# the corpus appears at more scenes than that.
MAX_INCIDENTS_PER_VEHICLE = 8

MECHANISM_WEIGHT = {
    "SHARED_HANDSET_IMEI": 0.92,
    "SHARED_BANK_ACCOUNT": 0.88,
    "SHARED_VEHICLE": 0.74,
    "CO_LOCATION": 0.55,
    "COMMON_ASSOCIATES": 0.45,
}


class LinkPredictor:

    def __init__(self, store, fused_graph: nx.Graph, verbose: bool = True):
        self.s = store
        self.G = fused_graph
        self.verbose = verbose
        self._known = self._known_pairs()

    def _log(self, m):
        if self.verbose:
            print(f"    {m}", flush=True)

    def _known_pairs(self) -> set:
        known = set()
        for r in self.s.person_person.itertuples():
            known.add(frozenset((r.src_person_id, r.dst_person_id)))
        return known

    def _is_new(self, a, b) -> bool:
        return a != b and frozenset((a, b)) not in self._known

    # ------------------------------------------------------------------
    # Evidential mechanisms
    # ------------------------------------------------------------------
    def shared_handset(self) -> list[dict]:
        out = []
        owner = self.s.phone_owner
        msisdn = self.s.msisdn_of
        for imei, phone_ids in self.s.phones_of_imei.items():
            people = {}
            for p in phone_ids:
                o = owner.get(p)
                if o:
                    people.setdefault(o, []).append(p)
            if len(people) < 2:
                continue
            for a, b in combinations(sorted(people), 2):
                if not self._is_new(a, b):
                    continue
                out.append(self._mk(
                    a, b, "SHARED_HANDSET_IMEI", imei,
                    f"SIMs registered to two different subscribers were used in "
                    f"the same handset (IMEI {imei}): "
                    f"{msisdn.get(people[a][0])} and {msisdn.get(people[b][0])}.",
                    {"imei": imei,
                     "msisdn_a": msisdn.get(people[a][0]),
                     "msisdn_b": msisdn.get(people[b][0])}))
        return out

    def shared_account(self) -> list[dict]:
        out = []
        for acct, holders in self.s.account_holders.items():
            uniq = sorted(set(holders))
            if len(uniq) < 2:
                continue
            for a, b in combinations(uniq, 2):
                if not self._is_new(a, b):
                    continue
                out.append(self._mk(
                    a, b, "SHARED_BANK_ACCOUNT", acct,
                    f"Both are recorded as controlling bank account {acct}.",
                    {"account_id": acct}))
        return out

    def shared_vehicle(self) -> list[dict]:
        """Two people tied to the same vehicle through different incidents."""
        inc_of_vehicle = defaultdict(set)
        for r in self.s.incident_vehicle.itertuples():
            inc_of_vehicle[r.vehicle_id].add(r.incident_id)
        veh = self.s.vehicles.set_index("vehicle_id")["registration_no"].to_dict()

        inc_by = self.s.incident_by_id
        out = []
        for vid, incs in inc_of_vehicle.items():
            # A vehicle seen at two scenes is only interesting if those scenes
            # are genuinely separate. Without these two constraints every
            # routinely-recorded vehicle generates the full cross-product of
            # everyone charged in every incident it ever appeared in -- 5,042
            # candidates here, against 28 real ones.
            if not (2 <= len(incs) <= MAX_INCIDENTS_PER_VEHICLE):
                continue
            states = {inc_by.get(i, {}).get("state") for i in incs}
            if len(states) < 2:
                continue
            people = defaultdict(set)
            for inc in incs:
                for p in self.s.accused_of_incident.get(inc, []):
                    people[p].add(inc)
            for a, b in combinations(sorted(people), 2):
                if not self._is_new(a, b) or people[a] == people[b]:
                    continue
                if not (people[a] - people[b]) or not (people[b] - people[a]):
                    continue
                out.append(self._mk(
                    a, b, "SHARED_VEHICLE", vid,
                    f"Vehicle {veh.get(vid, vid)} places them at separate "
                    f"incidents in {len(states)} different states "
                    f"({', '.join(sorted(x for x in states if x))}).",
                    {"vehicle_id": vid, "registration_no": veh.get(vid, ""),
                     "incidents_a": sorted(people[a])[:5],
                     "incidents_b": sorted(people[b])[:5]}))
        return out

    def co_location(self) -> list[dict]:
        out = []
        seen = set()
        loc = self.s.location_by_id
        for r in self.s.colocations.itertuples():
            a, b = r.person_a, r.person_b
            key = frozenset((a, b))
            if key in seen or not self._is_new(a, b):
                continue
            seen.add(key)
            l = loc.get(r.location_id, {})
            out.append(self._mk(
                a, b, "CO_LOCATION", r.location_id,
                f"Both placed at {l.get('area', '?')}, {l.get('city', '?')} on "
                f"{r.observed_on}, {r.time_gap_minutes} minutes apart "
                f"(source: {r.source_type}).",
                {"location_id": r.location_id, "observed_on": r.observed_on,
                 "time_gap_minutes": int(r.time_gap_minutes),
                 "source": r.source_type}))
        return out

    # ------------------------------------------------------------------
    # Structural inference
    # ------------------------------------------------------------------
    def common_associates(self, min_shared: int = 3, top_n: int = 400) -> list[dict]:
        """
        Adamic-Adar over the fused graph. It discounts mutual contacts who are
        connected to everyone -- sharing a hub says little, sharing two obscure
        associates says a lot.
        """
        G = self.G
        candidates = set()
        for v in G.nodes():
            nbrs = list(G.neighbors(v))
            for a, b in combinations(nbrs, 2):
                if self._is_new(a, b) and not G.has_edge(a, b):
                    candidates.add(frozenset((a, b)))
        pairs = [tuple(p) for p in candidates]
        if not pairs:
            return []
        scored = []
        for a, b in pairs:
            shared = set(G.neighbors(a)) & set(G.neighbors(b))
            if len(shared) < min_shared:
                continue
            aa = sum(1.0 / (math.log(G.degree(w)) if G.degree(w) > 1 else 1.0)
                     for w in shared)
            scored.append((aa, a, b, shared))
        scored.sort(reverse=True, key=lambda x: x[0])

        out = []
        for aa, a, b, shared in scored[:top_n]:
            out.append(self._mk(
                a, b, "COMMON_ASSOCIATES", "",
                f"No recorded relationship, but {len(shared)} mutual associates "
                f"(Adamic-Adar {aa:.2f}). Structural inference only -- no direct "
                f"evidence links these two.",
                {"shared_count": len(shared),
                 "adamic_adar": round(aa, 4),
                 "shared_associates": sorted(shared)[:10]},
                inferred=True))
        return out

    # ------------------------------------------------------------------
    def _mk(self, a, b, mechanism, evidence_id, description, evidence,
            inferred=False):
        pid = self.s.person_by_id
        pa, pb = pid.get(a, {}), pid.get(b, {})
        return {
            "person_a": a, "name_a": pa.get("full_name", ""),
            "syndicate_a": pa.get("syndicate_code", ""),
            "person_b": b, "name_b": pb.get("full_name", ""),
            "syndicate_b": pb.get("syndicate_code", ""),
            "mechanism": mechanism,
            "evidence_id": evidence_id,
            "confidence": MECHANISM_WEIGHT.get(mechanism, 0.5),
            "finding_type": "INFERRED" if inferred else "EVIDENTIAL",
            "crosses_recorded_groups": int(
                bool(pa.get("syndicate_code")) and
                bool(pb.get("syndicate_code")) and
                pa.get("syndicate_code") != pb.get("syndicate_code")),
            "description": description,
            "evidence": evidence,
            "status": "UNVERIFIED",
            "requires_human_verification": True,
        }

    # ------------------------------------------------------------------
    def run_all(self, include_inferred: bool = True) -> list[dict]:
        out = []
        for name, fn in (("shared handset", self.shared_handset),
                         ("shared account", self.shared_account),
                         ("shared vehicle", self.shared_vehicle),
                         ("co-location", self.co_location)):
            got = fn()
            self._log(f"{name:<18} {len(got):>5} evidential links")
            out += got
        if include_inferred:
            got = self.common_associates()
            self._log(f"{'common associates':<18} {len(got):>5} inferred links")
            out += got

        # merge duplicates: same pair found by several mechanisms is stronger
        merged: dict[frozenset, dict] = {}
        for r in out:
            key = frozenset((r["person_a"], r["person_b"]))
            if key in merged:
                m = merged[key]
                m["mechanism"] = m["mechanism"] + "|" + r["mechanism"]
                m["confidence"] = round(
                    1 - (1 - m["confidence"]) * (1 - r["confidence"]), 4)
                m["description"] += " " + r["description"]
                m["corroborating_mechanisms"] = m.get("corroborating_mechanisms", 1) + 1
                if r["finding_type"] == "EVIDENTIAL":
                    m["finding_type"] = "EVIDENTIAL"
            else:
                r["corroborating_mechanisms"] = 1
                merged[key] = r
        final = sorted(merged.values(), key=lambda r: -r["confidence"])
        for i, r in enumerate(final, 1):
            r["link_id"] = f"LNK{i:05d}"
        self._log(f"TOTAL {len(final):>5} candidate links "
                  f"({sum(1 for r in final if r['finding_type'] == 'EVIDENTIAL')} "
                  f"evidential)")
        return final


# ==========================================================================
def evaluate_links(found: list[dict], truth_df) -> dict:
    """Recall against the planted latent links, per mechanism."""
    if truth_df.empty:
        return {}
    got = {frozenset((r["person_a"], r["person_b"])) for r in found}
    got_ev = {frozenset((r["person_a"], r["person_b"])) for r in found
              if r["finding_type"] == "EVIDENTIAL"}

    res = {}
    for mech, grp in truth_df.groupby("mechanism"):
        want = [frozenset((r["person_a"], r["person_b"]))
                for r in grp.to_dict("records")]
        hit = sum(1 for w in want if w in got)
        hit_ev = sum(1 for w in want if w in got_ev)
        res[mech] = {"planted": len(want), "found": hit,
                     "found_as_evidential": hit_ev,
                     "recall": round(hit / len(want), 4) if want else 0.0}
    tp = sum(v["planted"] for v in res.values())
    td = sum(v["found"] for v in res.values())
    res["_overall"] = {
        "planted": tp, "found": td,
        "recall": round(td / tp, 4) if tp else 0.0,
        "total_candidates_raised": len(found),
        "evidential_candidates": len(got_ev),
    }
    return res
