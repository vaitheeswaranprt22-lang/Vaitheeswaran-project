# -*- coding: utf-8 -*-
"""
Graph construction: turn fragmented feeds into one relationship map.

Five layers are built, then fused:

  intel      declared person-person relations (INTELLIGENCE_REPORT, FIR, ...)
  comm       who called whom, lifted from phone level to person level via CDR
  money      who paid whom, from transaction records
  co_event   co-accused in the same FIR
  co_place   observed at the same place around the same time

The fused person graph carries, for every edge, *which layers support it*. That
matters more than the weight: a pair joined by one weak intel note is a lead, a
pair joined independently by calls, money and a shared incident is a finding.
Corroboration count is the signal investigators actually act on, so it is a
first-class edge attribute rather than something buried in a score.
"""

from __future__ import annotations

import math
from collections import defaultdict, Counter

import networkx as nx
import pandas as pd

# Relative contribution of each evidence layer to the fused weight.
LAYER_WEIGHTS = {
    "intel": 1.00,
    "comm": 0.75,
    "money": 0.80,
    "co_event": 0.65,
    "co_place": 0.40,
}

# Which layers may ASSERT a relationship, and which may only corroborate one.
#
# This distinction is the difference between a usable graph and mush. Being
# recorded as an associate, calling someone repeatedly, or paying them is a
# relationship. Standing in the same locality on the same day is not -- tower
# dumps put hundreds of unconnected people in the same cell every hour. If
# co-location is allowed to create edges it swamps the graph (here: 7,243
# co-location edges against 2,763 intelligence edges) and dissolves exactly the
# command hierarchy the analysis is supposed to recover.
#
# Corroborating evidence therefore strengthens an edge that other evidence
# already supports, and otherwise becomes a *candidate* link for the review
# queue (see linkpred) rather than a silent assertion.
STRUCTURAL_LAYERS = ("intel", "comm", "money")
CORROBORATING_LAYERS = ("co_event", "co_place")

# Being charged together once, in a five-accused FIR, is weak. Being charged
# together repeatedly is a relationship in its own right.
CO_EVENT_ASSERT_MIN_INCIDENTS = 2


class NetworkBuilder:

    def __init__(self, store, verbose: bool = True):
        self.s = store
        self.verbose = verbose
        self.layers: dict[str, nx.Graph] = {}

    def _log(self, m):
        if self.verbose:
            print(f"    {m}", flush=True)

    # ------------------------------------------------------------------
    # Layer 1: declared intelligence relations
    # ------------------------------------------------------------------
    def build_intel(self) -> nx.Graph:
        G = nx.Graph()
        for r in self.s.person_person.itertuples():
            w = float(r.strength) * float(r.confidence)
            if G.has_edge(r.src_person_id, r.dst_person_id):
                e = G[r.src_person_id][r.dst_person_id]
                e["weight"] = max(e["weight"], w)
                e["relations"].add(r.relation)
                e["n_records"] += 1
                e["verified"] = max(e["verified"], int(r.is_verified))
            else:
                G.add_edge(r.src_person_id, r.dst_person_id, weight=w,
                           relations={r.relation}, n_records=1,
                           verified=int(r.is_verified),
                           sources={r.source_type})
        for _, _, d in G.edges(data=True):
            d["relations"] = sorted(d["relations"])
            d["sources"] = sorted(d.get("sources", []))
        self.layers["intel"] = G
        self._log(f"intel layer:     {G.number_of_nodes():>6,} nodes  "
                  f"{G.number_of_edges():>7,} edges")
        return G

    # ------------------------------------------------------------------
    # Layer 2: communications (CDR lifted phone -> person)
    # ------------------------------------------------------------------
    def build_comm(self, min_calls: int = 2) -> nx.Graph:
        cdr = self.s.cdr
        owner = self.s.phone_owner
        df = pd.DataFrame({
            "a": cdr["caller_person_id"].map(lambda x: x) if "caller_person_id" in cdr
                 else cdr["caller_phone_id"].map(owner),
            "b": cdr["callee_person_id"] if "callee_person_id" in cdr
                 else cdr["callee_phone_id"].map(owner),
            "dur": cdr["duration_sec"].astype(int),
        }).dropna()
        df = df[df["a"] != df["b"]]
        # undirected key
        lo = df[["a", "b"]].min(axis=1)
        hi = df[["a", "b"]].max(axis=1)
        df = df.assign(lo=lo, hi=hi)
        agg = df.groupby(["lo", "hi"]).agg(calls=("dur", "size"),
                                           total_dur=("dur", "sum")).reset_index()
        agg = agg[agg["calls"] >= min_calls]

        G = nx.Graph()
        mx = float(agg["calls"].max()) if len(agg) else 1.0
        for r in agg.itertuples():
            G.add_edge(r.lo, r.hi,
                       weight=round(math.log1p(r.calls) / math.log1p(mx), 4),
                       calls=int(r.calls), total_duration_sec=int(r.total_dur))
        self.layers["comm"] = G
        self._log(f"comm layer:      {G.number_of_nodes():>6,} nodes  "
                  f"{G.number_of_edges():>7,} edges  (>= {min_calls} calls)")
        return G

    # ------------------------------------------------------------------
    # Layer 3: money
    # ------------------------------------------------------------------
    def build_money(self, amount_percentile: float = 0.90) -> nx.DiGraph:
        """
        Materiality filter. A single ordinary-sized transfer between two people
        is a transaction, not a relationship -- treating every one as an edge
        buries the graph in noise (26k of 28.5k pairs here transact exactly
        once). Two limbs are required, because dropping the second would delete
        the very patterns worth finding:

          repeated  -- 2 or more transfers, i.e. an ongoing channel
          material  -- a single transfer at/above the 90th percentile, which is
                       what a layering hop or a round-trip leg looks like
        """
        tx = self.s.transactions
        df = tx[tx["src_person_id"] != tx["dst_person_id"]]
        agg = (df.groupby(["src_person_id", "dst_person_id"])
                 .agg(total=("amount_inr", "sum"), n=("amount_inr", "size"))
                 .reset_index())
        before = len(agg)
        cutoff = agg["total"].quantile(amount_percentile) if len(agg) else 0
        agg = agg[(agg["n"] >= 2) | (agg["total"] >= cutoff)]
        self._log(f"money materiality: kept {len(agg):,}/{before:,} pairs "
                  f"(>=2 transfers, or single transfer >= Rs.{cutoff:,.0f})")
        G = nx.DiGraph()
        mx = float(agg["total"].max()) if len(agg) else 1.0
        for r in agg.itertuples():
            G.add_edge(r.src_person_id, r.dst_person_id,
                       weight=round(math.log1p(r.total) / math.log1p(mx), 4),
                       total_amount_inr=int(r.total), n_transactions=int(r.n))
        self.layers["money"] = G
        self._log(f"money layer:     {G.number_of_nodes():>6,} nodes  "
                  f"{G.number_of_edges():>7,} edges")
        return G

    # ------------------------------------------------------------------
    # Layer 4: co-accused in the same incident
    # ------------------------------------------------------------------
    def build_co_event(self) -> nx.Graph:
        G = nx.Graph()
        pair_incidents = defaultdict(set)
        for inc, people in self.s.accused_of_incident.items():
            ppl = sorted(set(people))
            for i in range(len(ppl)):
                for j in range(i + 1, len(ppl)):
                    pair_incidents[(ppl[i], ppl[j])].add(inc)
        for (a, b), incs in pair_incidents.items():
            G.add_edge(a, b, weight=round(min(1.0, len(incs) / 3.0), 4),
                       n_incidents=len(incs), incident_ids=sorted(incs)[:10])
        self.layers["co_event"] = G
        self._log(f"co_event layer:  {G.number_of_nodes():>6,} nodes  "
                  f"{G.number_of_edges():>7,} edges")
        return G

    # ------------------------------------------------------------------
    # Layer 5: co-location
    # ------------------------------------------------------------------
    def build_co_place(self) -> nx.Graph:
        G = nx.Graph()
        # (a) explicit co-location observations
        for r in self.s.colocations.itertuples():
            G.add_edge(r.person_a, r.person_b,
                       weight=float(r.confidence), n_observations=1,
                       location_ids=[r.location_id])
        # (b) derived: two people placed at the same location on the same day
        pl = self.s.person_location.dropna(subset=["observed_on"])
        buckets = defaultdict(set)
        for r in pl.itertuples():
            buckets[(r.location_id, r.observed_on)].add(r.person_id)
        for (loc, day), people in buckets.items():
            if not (2 <= len(people) <= 8):     # skip mass events: no signal
                continue
            ppl = sorted(people)
            for i in range(len(ppl)):
                for j in range(i + 1, len(ppl)):
                    a, b = ppl[i], ppl[j]
                    if G.has_edge(a, b):
                        d = G[a][b]
                        d["n_observations"] += 1
                        d["weight"] = min(1.0, d["weight"] + 0.12)
                        if loc not in d["location_ids"]:
                            d["location_ids"].append(loc)
                    else:
                        G.add_edge(a, b, weight=0.35, n_observations=1,
                                   location_ids=[loc])
        for _, _, d in G.edges(data=True):
            d["location_ids"] = d["location_ids"][:10]
        self.layers["co_place"] = G
        self._log(f"co_place layer:  {G.number_of_nodes():>6,} nodes  "
                  f"{G.number_of_edges():>7,} edges")
        return G

    # ------------------------------------------------------------------
    # Fusion
    # ------------------------------------------------------------------
    def fuse(self, restrict_to_persons: bool = True) -> nx.Graph:
        if not self.layers:
            self.build_all_layers()
        F = nx.Graph()
        people = set(self.s.persons["person_id"])
        self.uncorroborated_observations = []

        def contribute(name, a, b, d, may_assert):
            if restrict_to_persons and (a not in people or b not in people):
                return
            if not F.has_edge(a, b):
                if not may_assert:
                    # Nothing else supports this pair. Not an edge -- a lead.
                    self.uncorroborated_observations.append(
                        {"person_a": a, "person_b": b, "layer": name,
                         "detail": _jsonable(d)})
                    return
                F.add_edge(a, b, weight=0.0, layers=[], detail={})
            e = F[a][b]
            e["weight"] += LAYER_WEIGHTS[name] * float(d.get("weight", 0.5))
            e["layers"].append(name)
            e["detail"][name] = {k: v for k, v in d.items()
                                 if k not in ("weight", "layers", "detail")}

        # Pass 1: structural layers assert edges.
        for name in STRUCTURAL_LAYERS:
            G = self.layers.get(name)
            if G is None:
                continue
            for a, b, d in (G.to_undirected() if G.is_directed() else G).edges(data=True):
                contribute(name, a, b, d, may_assert=True)

        # Pass 2: corroborating layers strengthen what already exists.
        for name in CORROBORATING_LAYERS:
            G = self.layers.get(name)
            if G is None:
                continue
            for a, b, d in G.edges(data=True):
                strong = (name == "co_event" and
                          d.get("n_incidents", 0) >= CO_EVENT_ASSERT_MIN_INCIDENTS)
                contribute(name, a, b, d, may_assert=strong)

        max_w = max((d["weight"] for _, _, d in F.edges(data=True)), default=1.0)
        for _, _, d in F.edges(data=True):
            d["raw_weight"] = round(d["weight"], 4)
            d["weight"] = round(d["weight"] / max_w, 4)
            d["corroboration"] = len(d["layers"])
            d["layers"] = sorted(set(d["layers"]))
            d["detail"] = {k: _jsonable(v) for k, v in d["detail"].items()}

        # node attributes
        for r in self.s.persons.fillna("").itertuples():
            if r.person_id in F:
                F.nodes[r.person_id].update({
                    "name": r.full_name, "alias": r.alias, "role": r.role,
                    "syndicate": r.syndicate_code, "risk": int(r.risk_score or 0),
                    "person_type": r.person_type, "city": r.native_city,
                    "state": r.native_state, "custody": r.custody_status,
                })
        self.fused = F
        self._log(f"FUSED graph:     {F.number_of_nodes():>6,} nodes  "
                  f"{F.number_of_edges():>7,} edges")
        corr = Counter(d["corroboration"] for _, _, d in F.edges(data=True))
        self._log("corroboration:   " +
                  "  ".join(f"{k} layer(s)={v:,}" for k, v in sorted(corr.items())))
        self._log(f"held back as leads (observation only, no supporting edge): "
                  f"{len(self.uncorroborated_observations):,}")
        return F

    def build_all_layers(self):
        self.build_intel()
        self.build_comm()
        self.build_money()
        self.build_co_event()
        self.build_co_place()
        return self.layers

    # ------------------------------------------------------------------
    # Heterogeneous graph (all entity types) -- used for path explanation
    # ------------------------------------------------------------------
    def build_heterogeneous(self) -> nx.MultiDiGraph:
        s = self.s
        H = nx.MultiDiGraph()

        def add_nodes(df, id_col, ntype, label_col, **extra):
            if df.empty:
                return
            for r in df.fillna("").to_dict("records"):
                H.add_node(r[id_col], node_type=ntype, label=str(r.get(label_col, "")),
                           **{k: r.get(v, "") for k, v in extra.items()})

        add_nodes(s.persons, "person_id", "Person", "full_name",
                  role="role", syndicate="syndicate_code", risk="risk_score",
                  city="native_city", alias="alias")
        add_nodes(s.organizations, "org_id", "Organization", "name", org_type="org_type")
        add_nodes(s.locations, "location_id", "Location", "area", city="city", state="state")
        add_nodes(s.phones, "phone_id", "Phone", "msisdn", operator="operator")
        add_nodes(s.devices, "device_id", "Device", "imei", make="make")
        add_nodes(s.accounts, "account_id", "BankAccount", "account_number", bank="bank")
        add_nodes(s.vehicles, "vehicle_id", "Vehicle", "registration_no", make="make")
        add_nodes(s.incidents, "incident_id", "Incident", "crime_type",
                  city="city", severity="severity", when="incident_datetime")
        add_nodes(s.cases, "case_id", "Case", "case_title")

        def add_edges(df, a, b, etype, **attrs):
            if df.empty:
                return
            for r in df.fillna("").itertuples():
                u, v = getattr(r, a), getattr(r, b)
                if u in H and v in H:
                    H.add_edge(u, v, key=etype, edge_type=etype,
                               **{k: getattr(r, val, "") for k, val in attrs.items()})

        add_edges(s.person_person, "src_person_id", "dst_person_id", "RELATED_TO",
                  relation="relation", strength="strength")
        add_edges(s.person_org, "person_id", "org_id", "MEMBER_OF", role="role_in_org")
        add_edges(s.person_phone, "person_id", "phone_id", "USES_PHONE", usage="usage_type")
        add_edges(s.phone_device, "phone_id", "device_id", "SIM_IN_DEVICE", imei="imei")
        add_edges(s.person_account, "person_id", "account_id", "CONTROLS_ACCOUNT",
                  relation="relation")
        add_edges(s.person_vehicle, "person_id", "vehicle_id", "OWNS_VEHICLE")
        add_edges(s.person_location, "person_id", "location_id", "PRESENT_AT",
                  association="association", on="observed_on")
        add_edges(s.person_incident, "person_id", "incident_id", "INVOLVED_IN",
                  role="role_in_incident")
        add_edges(s.incident_vehicle, "incident_id", "vehicle_id", "VEHICLE_INVOLVED")
        add_edges(s.incidents, "incident_id", "location_id", "OCCURRED_AT")
        add_edges(s.incidents, "incident_id", "case_id", "PART_OF_CASE")

        self.hetero = H
        self._log(f"heterogeneous:   {H.number_of_nodes():>6,} nodes  "
                  f"{H.number_of_edges():>7,} edges")
        return H


def _jsonable(d):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, (set, frozenset)):
            v = sorted(v)
        if isinstance(v, (list, tuple)):
            v = list(v)[:10]
        out[k] = v
    return out
