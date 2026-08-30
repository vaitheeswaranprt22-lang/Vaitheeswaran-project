# -*- coding: utf-8 -*-
"""
End-to-end pipeline.

Runs every stage in dependency order, writes the derived artefacts the API and
UI read, and scores each stage against the ground truth so the run tells you
whether it actually worked -- not merely that it finished.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

import networkx as nx

from . import config as C
from .ingest import Store
from .nlp import Gazetteer, EntityExtractor, RelationExtractor, evaluate_ner
from .graphbuild import NetworkBuilder
from .analytics import (NetworkAnalyzer, CommandAnalyzer, PathExplainer,
                        rank_quality)
from .resolution import EntityResolver, evaluate_resolution
from .anomaly import AnomalyDetector, evaluate_anomalies
from .linkpred import LinkPredictor, evaluate_links


def _w(name, obj):
    path = os.path.join(C.DERIVED, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, default=str)
    return path


class Pipeline:

    def __init__(self, verbose: bool = True, ner_sample: int = 800,
                 skip_ner: bool = False):
        self.verbose = verbose
        self.ner_sample = ner_sample
        self.skip_ner = skip_ner
        self.timings: dict[str, float] = {}
        self.scorecard: dict[str, dict] = {}

    def _stage(self, title):
        if self.verbose:
            print(f"\n[{title}]", flush=True)
        return time.time()

    def _done(self, title, t0):
        self.timings[title] = round(time.time() - t0, 2)
        if self.verbose:
            print(f"    ... {self.timings[title]}s", flush=True)

    # ------------------------------------------------------------------
    def run(self) -> dict:
        overall = time.time()
        sys.setrecursionlimit(20000)

        # 1 -- ingest -------------------------------------------------
        t = self._stage("1/8  INGEST")
        self.store = Store(verbose=self.verbose).load_all()
        s = self.store
        self._done("ingest", t)

        # 2 -- NLP ----------------------------------------------------
        t = self._stage("2/8  ENTITY & RELATION EXTRACTION")
        self.gaz = Gazetteer(s)
        self.extractor = EntityExtractor(self.gaz)
        self.rel_extractor = RelationExtractor(self.gaz)
        docs = s.documents()
        extracted_entities, extracted_relations = [], []
        for d in docs:
            ents = self.extractor.extract(d["text"])
            ents = self.extractor.link(ents, s)
            rels = self.rel_extractor.extract(d["text"], ents, d["doc_id"])
            extracted_relations += [r for r in rels
                                    if r["relation"] != "CO_MENTIONED_WITH"]
            extracted_entities.append({"doc_id": d["doc_id"],
                                       "doc_type": d["doc_type"],
                                       "entities": ents})
        if self.verbose:
            print(f"    {len(docs):,} documents -> "
                  f"{sum(len(e['entities']) for e in extracted_entities):,} entity "
                  f"mentions, {len(extracted_relations):,} asserted relations",
                  flush=True)
        if not self.skip_ner:
            self.scorecard["ner"] = evaluate_ner(docs, self.extractor,
                                                 limit=self.ner_sample)
            n = self.scorecard["ner"]
            if self.verbose:
                print(f"    NER (typed) P={n['typed']['precision']:.3f} "
                      f"R={n['typed']['recall']:.3f} F1={n['typed']['f1']:.3f}",
                      flush=True)
        self.extracted_relations = extracted_relations
        self._done("nlp", t)

        # 3 -- graph --------------------------------------------------
        t = self._stage("3/8  GRAPH CONSTRUCTION")
        self.builder = NetworkBuilder(s, verbose=self.verbose)
        self.builder.build_all_layers()
        self.G = self.builder.fuse()
        self.H = self.builder.build_heterogeneous()
        self._done("graph", t)

        # 4 -- analytics ----------------------------------------------
        t = self._stage("4/8  NETWORK ANALYTICS")
        self.analyzer = NetworkAnalyzer(self.G, verbose=self.verbose)
        self.analyzer.compute_centrality()
        self.analyzer.detect_communities()
        ca = CommandAnalyzer(s, extracted_relations, verbose=self.verbose)
        self.command = ca.scores()
        self.proposed_relations = ca.proposed_relations
        intel = NetworkAnalyzer(nx.Graph(self.builder.layers["intel"]),
                                verbose=False)
        intel.compute_centrality()
        intel.detect_communities()
        self.broker = intel.broker_scores()
        self.key_players = self.analyzer.key_players(command=self.command,
                                                     broker=self.broker)
        self.communities = self.analyzer.community_profile(s)
        self.disruption = self.analyzer.disruption_simulation(
            [r["person_id"] for r in self.analyzer.ranked_by("influence")])
        self._score_key_players(s)
        self._done("analytics", t)

        # 5 -- entity resolution --------------------------------------
        t = self._stage("5/8  ENTITY RESOLUTION")
        self.resolver = EntityResolver(s, verbose=self.verbose)
        self.proposals = self.resolver.resolve()
        self.scorecard["entity_resolution"] = evaluate_resolution(
            self.proposals, s.truth("gt_duplicates"))
        self._done("resolution", t)

        # 6 -- anomalies ----------------------------------------------
        t = self._stage("6/8  ANOMALY DETECTION")
        self.findings = AnomalyDetector(s, verbose=self.verbose).run_all()
        self.scorecard["anomalies"] = evaluate_anomalies(
            self.findings, s.truth("gt_anomalies"))
        self._done("anomaly", t)

        # 7 -- hidden links -------------------------------------------
        t = self._stage("7/8  HIDDEN LINK DISCOVERY")
        self.links = LinkPredictor(s, self.G, verbose=self.verbose).run_all()
        self.scorecard["hidden_links"] = evaluate_links(
            self.links, s.truth("gt_latent"))
        self._done("linkpred", t)

        # 8 -- persist ------------------------------------------------
        t = self._stage("8/8  WRITING ARTEFACTS")
        self._persist(extracted_entities)
        self._done("persist", t)

        self.total_seconds = round(time.time() - overall, 2)
        if self.verbose:
            self.print_scorecard()
        return self.scorecard

    # ------------------------------------------------------------------
    def _score_key_players(self, s):
        gt = s.truth("gt_key_players")
        if gt.empty:
            return
        targets = {
            "KINGPIN": set(gt[gt.key_player_type == "KINGPIN"].person_id),
            "LIEUTENANT": set(gt[gt.key_player_type == "LIEUTENANT"].person_id),
            "BROKER": set(gt[gt.key_player_type == "BROKER"].person_id),
            "ANY_KEY_PLAYER": set(gt.person_id),
        }
        out = {}
        for ranking, target in (("influence", "ANY_KEY_PLAYER"),
                                ("command", "KINGPIN"),
                                ("command", "LIEUTENANT"),
                                ("broker", "BROKER")):
            ids = [r["person_id"] for r in self.analyzer.ranked_by(ranking)]
            out[f"{ranking}_vs_{target}"] = rank_quality(ids, targets[target])
        # community recovery
        truth_map = {r["person_id"]: r["syndicate_code"]
                     for r in s.truth("gt_membership").to_dict("records")}
        nodes = [n for n in self.analyzer.communities
                 if truth_map.get(n) and truth_map[n] != "UNAFFILIATED"]
        if nodes:
            y_true = [truth_map[n] for n in nodes]
            y_pred = [self.analyzer.communities[n] for n in nodes]
            try:
                from sklearn.metrics import (adjusted_rand_score,
                                             normalized_mutual_info_score)
                out["community_detection"] = {
                    "adjusted_rand_index": round(adjusted_rand_score(y_true, y_pred), 4),
                    "normalized_mutual_info": round(
                        normalized_mutual_info_score(y_true, y_pred), 4),
                    "communities_found": len(self.analyzer.community_sets),
                    "syndicates_planted": len(set(y_true)),
                    "modularity": round(self.analyzer.modularity, 4),
                }
            except ImportError:
                out["community_detection"] = {
                    "modularity": round(self.analyzer.modularity, 4)}
        self.scorecard["network_analytics"] = out

    # ------------------------------------------------------------------
    def _persist(self, extracted_entities):
        G = self.G
        nodes = [{"id": v, **{k: (list(x) if isinstance(x, (set, frozenset)) else x)
                              for k, x in d.items()}}
                 for v, d in G.nodes(data=True)]
        edges = [{"source": a, "target": b, "weight": d.get("weight", 0),
                  "layers": d.get("layers", []),
                  "corroboration": d.get("corroboration", 1),
                  "detail": d.get("detail", {})}
                 for a, b, d in G.edges(data=True)]

        _w("graph_nodes.json", nodes)
        _w("graph_edges.json", edges)
        _w("key_players.json", self.key_players)
        _w("communities.json", self.communities)
        _w("disruption_simulation.json", self.disruption)
        _w("resolution_proposals.json", self.proposals)
        _w("anomaly_findings.json", self.findings)
        _w("hidden_links.json", self.links)
        _w("extracted_relations.json", self.extracted_relations)
        _w("proposed_relations.json", self.proposed_relations)
        _w("extracted_entities.json", extracted_entities[:400])
        _w("scorecard.json", self.scorecard)

        node_comm = {v: self.analyzer.communities.get(v, -1) for v in G.nodes()}
        _w("node_communities.json", node_comm)

        summary = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "graph": {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
                      "communities": len(self.analyzer.community_sets),
                      "modularity": round(self.analyzer.modularity, 4)},
            "counts": {
                "persons": len(self.store.persons),
                "incidents": len(self.store.incidents),
                "documents": len(self.store.documents()),
                "key_players_ranked": len(self.key_players),
                "resolution_proposals": len(self.proposals),
                "anomaly_findings": len(self.findings),
                "hidden_links": len(self.links),
                "auto_merges_performed": 0,
                "auto_confirmed_links": 0,
                "text_relations_pending_review": len(self.proposed_relations),
            },
            "timings_seconds": self.timings,
        }
        _w("run_summary.json", summary)
        if self.verbose:
            print(f"    wrote 13 artefacts to {C.DERIVED}", flush=True)

    # ------------------------------------------------------------------
    def print_scorecard(self):
        sc = self.scorecard
        line = "=" * 78
        print(f"\n{line}\n SCORECARD  (every number measured against the shipped "
              f"ground truth)\n{line}")

        if "ner" in sc:
            n = sc["ner"]
            print(f"\n ENTITY EXTRACTION      ({n['documents']:,} documents)")
            print(f"   typed  P={n['typed']['precision']:.3f}  "
                  f"R={n['typed']['recall']:.3f}  F1={n['typed']['f1']:.3f}")
            print(f"   strict P={n['strict']['precision']:.3f}  "
                  f"R={n['strict']['recall']:.3f}  F1={n['strict']['f1']:.3f}"
                  f"   (strict penalises repeat mentions the corpus annotates once)")

        if "network_analytics" in sc:
            na = sc["network_analytics"]
            print("\n KEY PLAYER IDENTIFICATION")
            for k, v in na.items():
                if k == "community_detection":
                    continue
                print(f"   {k:<32} P@10={v['precision@10']:.2f}  "
                      f"P@25={v['precision@25']:.2f}  R@100={v['recall@100']:.2f}  "
                      f"AP={v['average_precision']:.3f}")
            cd = na.get("community_detection", {})
            if cd:
                print(f"\n COMMUNITY DETECTION")
                print(f"   ARI={cd.get('adjusted_rand_index', '-')}  "
                      f"NMI={cd.get('normalized_mutual_info', '-')}  "
                      f"Q={cd.get('modularity')}  "
                      f"{cd.get('communities_found')} found / "
                      f"{cd.get('syndicates_planted')} planted")

        if "entity_resolution" in sc:
            er = sc["entity_resolution"]
            print(f"\n ENTITY RESOLUTION      "
                  f"(blocking recall {er['blocking_recall']:.3f}, "
                  f"auto-merges {er['auto_merges_performed']})")
            for band in ("LOW", "MEDIUM", "HIGH"):
                d = er[band]
                print(f"   {band:<7} recall={d['recall']:.3f}  "
                      f"F1={d['f1']:.3f}  "
                      f"namesakes wrongly escalated="
                      f"{d['namesakes_escalated']}/{d['namesakes_total']}")

        if "anomalies" in sc:
            an = sc["anomalies"]
            print(f"\n ANOMALY DETECTION")
            for k, v in sorted(an.items()):
                if k.startswith("_"):
                    continue
                print(f"   {k:<26} {v['detected']:>3}/{v['planted']:<4} "
                      f"recall={v['recall']:.2f}   ({v['findings_raised']} raised)")
            o = an["_overall"]
            print(f"   {'OVERALL':<26} {o['detected']:>3}/{o['planted']:<4} "
                  f"recall={o['recall']:.2f}")

        if "hidden_links" in sc:
            hl = sc["hidden_links"]
            print(f"\n HIDDEN LINK DISCOVERY")
            for k, v in sorted(hl.items()):
                if k.startswith("_"):
                    continue
                print(f"   {k:<26} {v['found']:>3}/{v['planted']:<4} "
                      f"recall={v['recall']:.2f}")
            o = hl["_overall"]
            print(f"   {'OVERALL':<26} {o['found']:>3}/{o['planted']:<4} "
                  f"recall={o['recall']:.2f}   "
                  f"({o['total_candidates_raised']} candidates raised)")

        print(f"\n{line}")
        print(f" Total runtime {getattr(self, 'total_seconds', 0)}s   |   "
              f"auto-merges: 0   auto-confirmed links: 0   "
              f"(every proposal awaits a human)")
        print(line)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="SICND analysis pipeline")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--ner-sample", type=int, default=800,
                    help="documents to score NER on (0 = all)")
    ap.add_argument("--skip-ner-eval", action="store_true")
    a = ap.parse_args()
    p = Pipeline(verbose=not a.quiet,
                 ner_sample=a.ner_sample or None,
                 skip_ner=a.skip_ner_eval)
    p.run()


if __name__ == "__main__":
    main()
