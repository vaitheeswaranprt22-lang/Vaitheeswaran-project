# -*- coding: utf-8 -*-
"""
Network analytics: who matters, which group they belong to, and what breaks if
they are removed.

The central design claim: **no single centrality measure identifies the
important people.** Degree finds the loud middle management. Betweenness finds
brokers but also random cut vertices. Eigenvector finds whoever sits next to
someone important. The key-player score fuses them and adds a cross-community
reach term, because in an organised-crime graph the people worth arresting are
the ones whose removal disconnects the network, not the ones with many friends.
"""

from __future__ import annotations

import math
from collections import defaultdict, Counter

import networkx as nx
import numpy as np

from . import config as C


# ==========================================================================
def _pct_rank(values: dict) -> dict:
    """Percentile-rank a score dict into [0,1]; ties share the mean rank."""
    if not values:
        return {}
    items = sorted(values.items(), key=lambda kv: kv[1])
    n = len(items)
    out, i = {}, 0
    while i < n:
        j = i
        while j + 1 < n and items[j + 1][1] == items[i][1]:
            j += 1
        rank = (i + j) / 2.0
        for k in range(i, j + 1):
            out[items[k][0]] = rank / (n - 1) if n > 1 else 1.0
        i = j + 1
    return out


class NetworkAnalyzer:

    def __init__(self, G: nx.Graph, verbose: bool = True):
        self.G = G
        self.verbose = verbose
        self.metrics: dict[str, dict] = {}
        self.communities: dict[str, int] = {}
        self._giant = None

    def _log(self, m):
        if self.verbose:
            print(f"    {m}", flush=True)

    @property
    def giant(self) -> nx.Graph:
        if self._giant is None:
            if self.G.number_of_nodes() == 0:
                self._giant = self.G
            else:
                comp = max(nx.connected_components(self.G), key=len)
                self._giant = self.G.subgraph(comp).copy()
        return self._giant

    # ------------------------------------------------------------------
    def compute_centrality(self, weight="weight") -> dict:
        G, Gg = self.G, self.giant
        n = Gg.number_of_nodes()

        deg = dict(G.degree())
        wdeg = dict(G.degree(weight=weight))

        # Exact when affordable: pivot sampling perturbs the top of the ranking,
        # which is the only part of a key-player list anyone reads.
        if n <= C.KeyPlayer.BETWEENNESS_EXACT_MAX_NODES:
            k, mode = None, "exact"
        else:
            k = min(C.KeyPlayer.BETWEENNESS_SAMPLE, n)
            mode = f"sampled k={k}"
        btw = nx.betweenness_centrality(Gg, k=k, seed=C.SEED, normalized=True)
        self._log(f"betweenness: {mode} on {n:,}-node component")

        try:
            eig = nx.eigenvector_centrality_numpy(Gg, weight=weight)
        except Exception:
            eig = nx.eigenvector_centrality(Gg, max_iter=1000, tol=1e-6)
        pr = nx.pagerank(G, weight=weight)
        core = nx.core_number(nx.Graph(G))
        clus = nx.clustering(G, weight=weight)

        self.metrics = {
            "degree": deg, "weighted_degree": wdeg, "betweenness": btw,
            "eigenvector": eig, "pagerank": pr, "kcore": core, "clustering": clus,
        }
        return self.metrics

    # ------------------------------------------------------------------
    def detect_communities(self, weight="weight", resolution=1.0) -> dict:
        comms = nx.community.louvain_communities(
            self.G, weight=weight, seed=C.SEED, resolution=resolution)
        self.community_sets = sorted(comms, key=len, reverse=True)
        self.communities = {}
        for i, c in enumerate(self.community_sets):
            for node in c:
                self.communities[node] = i
        try:
            self.modularity = nx.community.modularity(self.G, comms, weight=weight)
        except Exception:
            self.modularity = float("nan")
        self._log(f"communities: {len(comms)} found, modularity Q={self.modularity:.3f}")
        return self.communities

    # ------------------------------------------------------------------
    def cross_community_reach(self) -> dict:
        """
        How many distinct communities a node touches, normalised. This is the
        term that separates a broker from a hub: a lieutenant with 40 contacts
        inside one cell scores 0; a financier with 6 contacts spread over four
        syndicates scores high.
        """
        if not self.communities:
            self.detect_communities()
        out = {}
        for v in self.G.nodes():
            own = self.communities.get(v)
            others = {self.communities.get(u) for u in self.G.neighbors(v)}
            others.discard(None)
            out[v] = len(others - {own})
        mx = max(out.values()) if out else 1
        return {k: (v / mx if mx else 0.0) for k, v in out.items()}

    # ------------------------------------------------------------------
    def broker_scores(self) -> dict[str, float]:
        """
        Brokerage measured on THIS graph's communities.

        Run this on the intelligence layer, not the fused graph. Measured here:
        cross-community reach scores AP 0.272 on the intel layer and 0.095 once
        communications and money are fused in. The reason is the same one that
        hides command -- mules and payment hubs touch many groups incidentally,
        so incidental co-transaction swamps the deliberate cross-syndicate ties
        that make someone a conduit. Brokerage is a claim about relationships,
        so it is measured over asserted relationships.

        Reach dominates; betweenness only breaks ties between equal-reach nodes
        (a weight sweep put the optimum at pure reach).
        """
        if not self.metrics:
            self.compute_centrality()
        if not self.communities:
            self.detect_communities()
        r_reach = _pct_rank(self.cross_community_reach())
        r_btw = _pct_rank(self.metrics["betweenness"])
        return {v: round(0.85 * r_reach.get(v, 0) + 0.15 * r_btw.get(v, 0), 4)
                for v in self.G.nodes()}

    def key_players(self, top_n: int | None = None,
                    command: dict[str, dict] | None = None,
                    broker: dict[str, float] | None = None) -> list[dict]:
        if not self.metrics:
            self.compute_centrality()
        if not self.communities:
            self.detect_communities()
        command = command or {}

        W = C.KeyPlayer
        r_btw = _pct_rank(self.metrics["betweenness"])
        r_eig = _pct_rank(self.metrics["eigenvector"])
        r_pr = _pct_rank(self.metrics["pagerank"])
        r_deg = _pct_rank(self.metrics["degree"])
        r_core = _pct_rank(self.metrics["kcore"])
        reach = self.cross_community_reach()
        r_reach = _pct_rank(reach)

        arts = set(nx.articulation_points(self.giant))

        rows = []
        for v in self.G.nodes():
            structural = (W.W_BETWEENNESS * r_btw.get(v, 0) +
                          W.W_EIGENVECTOR * r_eig.get(v, 0) +
                          W.W_PAGERANK * r_pr.get(v, 0) +
                          W.W_DEGREE * r_deg.get(v, 0) +
                          W.W_KCORE * r_core.get(v, 0) +
                          W.W_BRIDGE * r_reach.get(v, 0))
            cmd = command.get(v, {})
            cmd_score = cmd.get("command_score", 0.0)
            # A broker is the opposite shape to a commander: wide cross-group
            # reach, not many local contacts. Scored separately (and preferably
            # on the intel layer) so the command term cannot bury the people
            # holding otherwise-separate networks together.
            broker_s = (broker or {}).get(
                v, 0.45 * r_btw.get(v, 0) + 0.40 * r_reach.get(v, 0) +
                   0.15 * (1.0 - r_deg.get(v, 0)))
            # Structural centrality and command authority answer different
            # questions and are kept visible separately; the blend is what the
            # ranked list uses.
            score = (1 - W.W_COMMAND) * structural + W.W_COMMAND * cmd_score
            attrs = self.G.nodes[v]
            rows.append({
                "person_id": v,
                "name": attrs.get("name", ""),
                "alias": attrs.get("alias", ""),
                "role_recorded": attrs.get("role", ""),
                "syndicate_recorded": attrs.get("syndicate", ""),
                "influence_score": round(score, 4),
                "structural_score": round(structural, 4),
                "command_score": round(cmd_score, 4),
                "broker_score": round(broker_s, 4),
                "direct_subordinates": cmd.get("direct_subordinates", 0),
                "subordinate_span": cmd.get("subordinate_span", 0),
                "hierarchy_depth": cmd.get("hierarchy_depth", 0),
                "betweenness": round(self.metrics["betweenness"].get(v, 0), 6),
                "eigenvector": round(self.metrics["eigenvector"].get(v, 0), 6),
                "pagerank": round(self.metrics["pagerank"].get(v, 0), 6),
                "degree": self.metrics["degree"].get(v, 0),
                "kcore": self.metrics["kcore"].get(v, 0),
                "communities_touched": reach.get(v, 0),
                "is_articulation_point": int(v in arts),
                "community": self.communities.get(v, -1),
                "inferred_role": self._infer_role(v, r_btw, r_deg, reach, arts, cmd),
            })
        rows.sort(key=lambda r: -r["influence_score"])
        for i, r in enumerate(rows, 1):
            r["rank"] = i
        self._ranked = rows
        return rows[:top_n] if top_n else rows

    def ranked_by(self, kind: str = "influence", top_n: int | None = None) -> list[dict]:
        """
        Three answers to three different questions, deliberately not collapsed
        into one list:

          command   who gives orders           -- authority flow, subordinate span
          broker    who connects the groups    -- betweenness + cross-community reach
          influence overall importance         -- blended

        Forcing these into a single ranking makes each one worse: on this data,
        blending drove broker average-precision from 0.40 down to 0.12 because
        conduits have no subordinates to score on.
        """
        key = {"command": "command_score", "broker": "broker_score",
               "influence": "influence_score",
               "structural": "structural_score"}[kind]
        # NB: not getattr(self, "_ranked", self.key_players()) -- Python
        # evaluates that default eagerly, which would re-run the ranking
        # without the command scores and silently discard them.
        if getattr(self, "_ranked", None) is None:
            self.key_players()
        rows = sorted(self._ranked, key=lambda r: -r[key])
        out = []
        for i, r in enumerate(rows, 1):
            r = dict(r)
            r[f"{kind}_rank"] = i
            out.append(r)
        return out[:top_n] if top_n else out

    def _infer_role(self, v, r_btw, r_deg, reach, arts, cmd=None):
        """
        Structural role, inferred from position alone -- never read off the
        recorded 'role' column. This is what the system would have to do on real
        data where nobody is labelled.
        """
        b, d = r_btw.get(v, 0), r_deg.get(v, 0)
        cross = reach.get(v, 0) > 0.25
        cmd = cmd or {}
        # Command evidence outranks topology: someone with subordinates
        # reporting up to them is a controller regardless of how the
        # communications graph happens to look.
        direct = cmd.get("direct_subordinates", 0)
        span = cmd.get("subordinate_span", 0)
        # Span far exceeding direct reports is the signature of an insulated
        # apex: few contacts, but authority reaching deep through layers.
        if direct >= 2 and span >= max(8, 3 * direct):
            return "APEX / INSULATED CONTROLLER"
        if direct >= 8:
            return "CELL COMMANDER"
        if span >= 4 and d < 0.85:
            return "CELL LEADER"
        if b > 0.97 and cross:
            return "BROKER / CUT-VERTEX"
        if b > 0.92 and d < 0.80:
            return "INSULATED CONTROLLER"     # high flow, few contacts
        if d > 0.95:
            return "OPERATIONAL HUB"
        if v in arts and b > 0.75:
            return "SINGLE POINT OF FAILURE"
        if d < 0.30 and b < 0.30:
            return "PERIPHERAL"
        return "CORE MEMBER"

    # ------------------------------------------------------------------
    def disruption_simulation(self, ranked_ids: list[str], budgets=(1, 5, 10, 20, 40)):
        """
        Remove the top-k ranked people and measure what happens to the network.
        This is the question a commander actually asks: not "who is important"
        but "if I can arrest ten people, which ten hurt this network most".
        Compared against a degree-ranked baseline so the number means something.
        """
        base_nodes = self.giant.number_of_nodes()
        deg_rank = [v for v, _ in sorted(self.G.degree(),
                                         key=lambda kv: -kv[1])]

        def measure(removed):
            H = self.G.copy()
            H.remove_nodes_from(removed)
            if H.number_of_nodes() == 0:
                return {"largest_component": 0, "n_components": 0, "efficiency": 0.0}
            comps = list(nx.connected_components(H))
            largest = max(len(c) for c in comps)
            return {
                "largest_component": largest,
                "largest_component_pct": round(100 * largest / base_nodes, 2),
                "n_components": len(comps),
            }

        out = []
        for k in budgets:
            tgt = ranked_ids[:k]
            base = deg_rank[:k]
            out.append({
                "budget": k,
                "key_player_targeting": measure(tgt),
                "degree_baseline": measure(base),
            })
        return out

    # ------------------------------------------------------------------
    def community_profile(self, store) -> list[dict]:
        """Describe each detected community by what its members actually do."""
        if not self.communities:
            self.detect_communities()
        pid = store.person_by_id
        inc_of = store.incidents_of_person
        inc_by = store.incident_by_id

        rows = []
        for i, members in enumerate(self.community_sets):
            crimes, states, roles, syn = Counter(), Counter(), Counter(), Counter()
            risks = []
            for m in members:
                p = pid.get(m)
                if not p:
                    continue
                roles[p.get("role") or "-"] += 1
                syn[p.get("syndicate_code") or "-"] += 1
                states[p.get("native_state") or "-"] += 1
                try:
                    risks.append(float(p.get("risk_score") or 0))
                except (TypeError, ValueError):
                    pass
                for inc in inc_of.get(m, []):
                    c = inc_by.get(inc)
                    if c:
                        crimes[c["crime_type"]] += 1
            leaders = sorted(members,
                             key=lambda v: -self.metrics.get("betweenness", {}).get(v, 0))[:5]
            rows.append({
                "community": i,
                "size": len(members),
                "avg_risk": round(sum(risks) / len(risks), 1) if risks else 0.0,
                "top_crimes": [c for c, _ in crimes.most_common(4)],
                "top_states": [s for s, _ in states.most_common(3)],
                "role_mix": dict(roles.most_common(5)),
                "dominant_recorded_syndicate": syn.most_common(1)[0][0] if syn else "-",
                "purity": round(syn.most_common(1)[0][1] / len(members), 3) if syn else 0.0,
                "likely_leaders": [{"person_id": v,
                                    "name": self.G.nodes[v].get("name", "")}
                                   for v in leaders],
            })
        return rows


# ==========================================================================
# Command / authority analysis
# ==========================================================================
#
# Why this exists as a separate analysis:
#
# Measured on this dataset, kingpins sit at median betweenness rank 8 in the
# intelligence layer but rank 123 once communications and money are fused in.
# That is not a defect in the fusion -- it is a property of the evidence.
# Everyone in a cell phones everyone else, and those lateral calls create
# shortcuts that route around the person giving the orders. Topology alone,
# on undirected fused evidence, systematically hides command.
#
# Command is recoverable because the *relation types* carry direction and
# authority: "reports to", "handler of", "recruited by" are not symmetric.
# Collapsing them into an undirected edge throws away the only signal that
# distinguishes a boss from a busy subordinate.
#
# Edges here always point SUBORDINATE -> SUPERIOR, so authority accumulates
# upward and PageRank on this graph reads as "who does influence flow to".

AUTHORITY_RELATIONS = {
    # relation            : (orientation, weight)
    #   'as_is'   src is the subordinate, dst the superior
    #   'reverse' src is the superior, dst the subordinate
    "REPORTS_TO":               ("as_is", 1.00),
    "HANDLER_OF":               ("reverse", 0.90),
    "RECRUITED_BY":             ("reverse", 0.70),
    "ACTS_ON_INSTRUCTIONS_OF":  ("as_is", 0.85),
    "FINANCES":                 ("as_is", 0.45),
    "SUPPLIES_TO":              ("reverse", 0.40),
    "COMMUNICATION_CONDUIT":    ("as_is", 0.50),
    "BENAMI_OF":                ("as_is", 0.75),
}

# Of those, the ones that constitute an actual chain of command -- the only
# relations allowed to propagate authority transitively (see CommandAnalyzer).
COMMAND_CHAIN_RELATIONS = {
    "REPORTS_TO", "HANDLER_OF", "RECRUITED_BY", "ACTS_ON_INSTRUCTIONS_OF",
}


class CommandAnalyzer:
    """Recovers hierarchy from directed, authority-bearing relations."""

    def __init__(self, store, extracted_relations: list[dict] | None = None,
                 verbose: bool = True):
        self.s = store
        self.verbose = verbose
        self.A = self._build(extracted_relations or [])

    def _log(self, m):
        if self.verbose:
            print(f"    {m}", flush=True)

    def _build(self, extracted) -> nx.DiGraph:
        A = nx.DiGraph()
        rows = [{"src": r.src_person_id, "dst": r.dst_person_id,
                 "rel": r.relation, "conf": float(r.confidence)}
                for r in self.s.person_person.itertuples()]

        # Relations pattern-matched out of narrative text are UNVERIFIED
        # assertions, and the same rule applies to them as to co-location: they
        # may corroborate a relationship that is already recorded, but they may
        # not assert a new one into the command hierarchy on their own.
        # Admitting them freely put a mule at the top of the ranking with a
        # transitive span of 517, built entirely out of "nearest person before
        # the phrase" guesses chained end to end.
        declared = set()
        for r in self.s.person_person.itertuples():
            declared.add((r.src_person_id, r.dst_person_id))
            declared.add((r.dst_person_id, r.src_person_id))
        self.proposed_relations = []
        for r in extracted:
            pair = (r["src_person_id"], r["dst_person_id"])
            if pair in declared:
                rows.append({"src": pair[0], "dst": pair[1],
                             "rel": r["relation"], "conf": r["confidence"]})
            else:
                self.proposed_relations.append(
                    {**r, "status": "UNVERIFIED",
                     "requires_human_verification": True,
                     "note": "Extracted from text; no recorded relationship "
                             "between these two corroborates it."})
        for r in rows:
            spec = AUTHORITY_RELATIONS.get(r["rel"])
            if not spec:
                continue
            orient, w = spec
            u, v = (r["src"], r["dst"]) if orient == "as_is" else (r["dst"], r["src"])
            w = w * r["conf"]
            if A.has_edge(u, v):
                A[u][v]["weight"] = max(A[u][v]["weight"], w)
            else:
                A.add_edge(u, v, weight=w, relation=r["rel"])
        self._log(f"command graph:   {A.number_of_nodes():>6,} nodes  "
                  f"{A.number_of_edges():>7,} authority edges  "
                  f"({len(self.proposed_relations):,} text-extracted relations "
                  f"held back as proposals)")
        return A

    def scores(self) -> dict[str, dict]:
        A = self.A
        if A.number_of_nodes() == 0:
            return {}
        # Authority flows up these edges, so PageRank on A concentrates on
        # superiors. Damping is high because chains are short.
        pr = nx.pagerank(A, alpha=0.9, weight="weight")
        direct = {v: A.in_degree(v, weight="weight") for v in A.nodes()}

        # Transitive span: everyone reachable by following subordinate->superior
        # edges *backwards* is somebody this person sits above.
        #
        # Only true chain-of-command relations may propagate transitively.
        # Commercial leverage does not: with "supplies to" counted as authority,
        # a supplier inherited the whole downstream organisation of every buyer
        # and spans exploded across syndicate boundaries (a cell lieutenant came
        # out with 658 "subordinates" in a 889-node graph). Being someone's
        # supplier or financier is leverage over them, not command of their crew.
        chain = nx.DiGraph()
        chain.add_nodes_from(A.nodes())
        chain.add_edges_from(
            (u, v) for u, v, d in A.edges(data=True)
            if d.get("relation") in COMMAND_CHAIN_RELATIONS)
        R = chain.reverse(copy=False)
        span, depth = {}, {}
        for v in chain.nodes():
            reach = nx.descendants(R, v)
            span[v] = len(reach)
            if reach:
                lengths = nx.single_source_shortest_path_length(R, v)
                depth[v] = max(lengths.values())
            else:
                depth[v] = 0

        r_pr, r_direct, r_span = _pct_rank(pr), _pct_rank(direct), _pct_rank(span)
        out = {}
        for v in A.nodes():
            out[v] = {
                "command_score": round(0.40 * r_pr.get(v, 0) +
                                       0.30 * r_span.get(v, 0) +
                                       0.30 * r_direct.get(v, 0), 4),
                "authority_pagerank": round(pr.get(v, 0), 6),
                "direct_subordinates": int(A.in_degree(v)),
                "subordinate_span": span.get(v, 0),
                "hierarchy_depth": depth.get(v, 0),
            }
        return out


# ==========================================================================
# Relationship pathfinding -- "how is A connected to B?"
# ==========================================================================
class PathExplainer:
    """
    Answers the single most-asked investigative question: *how* are these two
    connected. Returns the path with every hop described in words, over the
    heterogeneous graph so a chain can run person -> phone -> device -> phone
    -> person and still be explainable.
    """

    HOP_PHRASING = {
        "RELATED_TO": "is recorded as {relation} of",
        "MEMBER_OF": "is a member/officer ({role}) of",
        "USES_PHONE": "uses phone",
        "SIM_IN_DEVICE": "which was used in handset",
        "CONTROLS_ACCOUNT": "controls account",
        "OWNS_VEHICLE": "owns vehicle",
        "PRESENT_AT": "was observed at",
        "INVOLVED_IN": "is {role} in",
        "VEHICLE_INVOLVED": "involved vehicle",
        "OCCURRED_AT": "occurred at",
        "PART_OF_CASE": "belongs to case",
    }

    def __init__(self, hetero: nx.MultiDiGraph):
        self.H = hetero
        self.U = nx.Graph(hetero)   # undirected view for traversal

    def shortest(self, a: str, b: str, max_len: int = 8) -> dict | None:
        if a not in self.U or b not in self.U:
            return None
        try:
            path = nx.shortest_path(self.U, a, b)
        except nx.NetworkXNoPath:
            return None
        if len(path) - 1 > max_len:
            return None
        return {"length": len(path) - 1, "nodes": self._describe_nodes(path),
                "narrative": self._narrate(path)}

    def all_paths(self, a: str, b: str, cutoff: int = 4, limit: int = 8) -> list[dict]:
        if a not in self.U or b not in self.U:
            return []
        out = []
        for p in nx.all_simple_paths(self.U, a, b, cutoff=cutoff):
            out.append({"length": len(p) - 1, "nodes": self._describe_nodes(p),
                        "narrative": self._narrate(p)})
            if len(out) >= limit:
                break
        return sorted(out, key=lambda x: x["length"])

    def _describe_nodes(self, path):
        out = []
        for n in path:
            d = self.H.nodes.get(n, {})
            out.append({"id": n, "type": d.get("node_type", "?"),
                        "label": d.get("label", n)})
        return out

    def _edge_between(self, u, v):
        """Return (data, forward) -- forward is False when the stored edge runs
        v->u and we are walking it backwards."""
        if self.H.has_edge(u, v):
            return next(iter(self.H[u][v].values())), True
        if self.H.has_edge(v, u):
            return next(iter(self.H[v][u].values())), False
        return {}, True

    def _narrate(self, path):
        parts = []
        for u, v in zip(path, path[1:]):
            d, forward = self._edge_between(u, v)
            et = d.get("edge_type", "linked to")
            phrase = self.HOP_PHRASING.get(et, et.replace("_", " ").lower())
            try:
                phrase = phrase.format(**{k: (v_ or "?") for k, v_ in d.items()})
            except (KeyError, IndexError):
                phrase = phrase.split("{")[0].strip()
            lu = self.H.nodes.get(u, {}).get("label", u)
            lv = self.H.nodes.get(v, {}).get("label", v)
            # The phrasing belongs to the edge's own direction. Walking a
            # person->location edge backwards and keeping the forward wording
            # produced sentences like "Jharia was observed at Arun Chauhan";
            # naming the subject correctly gives "Arun Chauhan was observed at
            # Jharia" instead.
            parts.append(f"{lu} {phrase} {lv}" if forward
                         else f"{lv} {phrase} {lu}")
        return "; ".join(parts) + "."


# ==========================================================================
# Evaluation helpers
# ==========================================================================
def rank_quality(ranked_ids: list[str], truth_ids: set, ks=(10, 25, 50, 100)) -> dict:
    """Precision@k / recall@k plus average precision for a ranked list."""
    truth = set(truth_ids)
    out = {}
    hits = 0
    ap, found = 0.0, 0
    for i, pid in enumerate(ranked_ids, 1):
        if pid in truth:
            found += 1
            ap += found / i
        if i in ks:
            hits = sum(1 for p in ranked_ids[:i] if p in truth)
            out[f"precision@{i}"] = round(hits / i, 4)
            out[f"recall@{i}"] = round(hits / len(truth), 4) if truth else 0.0
    out["average_precision"] = round(ap / len(truth), 4) if truth else 0.0
    return out
