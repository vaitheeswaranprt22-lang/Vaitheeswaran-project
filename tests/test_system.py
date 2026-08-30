# -*- coding: utf-8 -*-
"""
Regression tests.

These lock down the behaviours that are easy to break silently -- especially
the safety rules (no auto-merge, no auto-confirmed links) and the bugs that
were actually hit while building this system, each of which is noted at the
test that guards it.

Run:  python -m pytest tests -q      (or: python tests/test_system.py)
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sicnd.ingest import get_store
from sicnd.textsim import (phonetic_key, phonetic_variants, name_similarity,
                           name_key, jaro_winkler)
from sicnd.nlp import Gazetteer, EntityExtractor, evaluate_ner
from sicnd.graphbuild import NetworkBuilder
from sicnd.analytics import NetworkAnalyzer, CommandAnalyzer, rank_quality
from sicnd.resolution import EntityResolver, evaluate_resolution
from sicnd.linkpred import LinkPredictor, evaluate_links


@pytest.fixture(scope="module")
def store():
    return get_store(verbose=False)


@pytest.fixture(scope="module")
def graph(store):
    nb = NetworkBuilder(store, verbose=False)
    nb.build_all_layers()
    return nb, nb.fuse()


# ==========================================================================
# Data integrity
# ==========================================================================
def test_identifiers_load_as_strings(store):
    """A phone number read as int64 stops joining against the same number
    read as text. This broke CDR->subscriber resolution once already."""
    assert store.cdr["caller_msisdn"].dtype == object
    assert store.transactions["src_account_no"].dtype == object
    assert store.phones["msisdn"].dtype == object


def test_cdr_resolves_to_known_subscribers(store):
    known = set(store.phones["msisdn"])
    seen = set(store.cdr["caller_msisdn"].unique())
    assert seen <= known


def test_cdr_respects_sim_service_life(store):
    """Calls must not appear on a SIM before issue or after surrender --
    the registry and the traffic have to agree."""
    import pandas as pd
    ph = store.phones.set_index("phone_id")
    c = store.cdr.sample(min(20000, len(store.cdr)), random_state=1).copy()
    c["ts"] = pd.to_datetime(c["timestamp"])
    m = c.join(ph[["activation_date", "deactivation_date"]], on="caller_phone_id")
    a = pd.to_datetime(m["activation_date"])
    d = pd.to_datetime(m["deactivation_date"])
    bad = ((m["ts"] < a) | (d.notna() & (m["ts"] > d))).sum()
    assert bad == 0


def test_referential_integrity(store):
    pid = set(store.persons["person_id"])
    assert set(store.person_person["src_person_id"]) <= pid
    assert set(store.person_person["dst_person_id"]) <= pid
    assert set(store.person_incident["person_id"]) <= pid


# ==========================================================================
# String similarity
# ==========================================================================
@pytest.mark.parametrize("a,b", [
    ("Mohammed", "Mohammad"), ("Mohammed", "Muhammad"), ("Mohammed", "Mohd"),
    ("Mohammed", "Md"), ("Choudhary", "Chowdhury"), ("Sheikh", "Shaikh"),
    ("Qureshi", "Kureshi"), ("Nair", "Nayar"), ("Gowda", "Gouda"),
    ("Biswas", "Bishwas"), ("Halder", "Haldar"),
])
def test_transliteration_variants_share_a_key(a, b):
    assert phonetic_key(a) == phonetic_key(b), f"{a}/{b} must collapse"


@pytest.mark.parametrize("a,b", [
    ("Bhattacharya", "Bhattacharjee"), ("Rathore", "Rathod"),
])
def test_hard_variants_at_least_block_together(a, b):
    """Different tails; exact keys may differ but blocking must still pair
    them so the scorer gets a chance."""
    assert phonetic_variants(a) & phonetic_variants(b) or \
        name_similarity(a, b) > 0.7


@pytest.mark.parametrize("a,b", [("Sharma", "Verma"), ("Khan", "Kaur"),
                                 ("Nair", "Naik"), ("Reddy", "Rao")])
def test_distinct_surnames_do_not_collide(a, b):
    assert phonetic_key(a) != phonetic_key(b)


def test_name_order_swap_is_recognised():
    assert name_similarity("Ramesh Yadav", "Yadav Ramesh") > 0.95


def test_jaro_winkler_bounds():
    assert jaro_winkler("", "") == 1.0
    assert 0.0 <= jaro_winkler("abc", "xyz") <= 1.0


# ==========================================================================
# NLP
# ==========================================================================
def test_ner_quality(store):
    ex = EntityExtractor(Gazetteer(store))
    r = evaluate_ner(store.documents(), ex, limit=200)
    assert r["typed"]["f1"] > 0.95
    assert r["typed"]["precision"] > 0.95


def test_two_letter_given_names_survive(store):
    """'Om Prakash Bhardwaj' was being truncated to 'Prakash Bhardwaj'
    because the candidate regex demanded 2+ lowercase letters."""
    ex = EntityExtractor(Gazetteer(store))
    text = ("It is alleged that Naseer Ahmed and Om Prakash Bhardwaj committed "
            "the offence at Sohna, Gurugram on 27.11.2021.")
    names = {e["text"] for e in ex.extract(text) if e["label"] == "PERSON"}
    assert "Om Prakash Bhardwaj" in names


def test_gazetteer_terms_are_not_mistaken_for_people(store):
    ex = EntityExtractor(Gazetteer(store))
    text = ("A complaint dated 21.06.2022 was forwarded by the Enforcement "
            "Directorate to Melur Police Station, Coimbatore, and account "
            "43766277286409 of Karur Vysya Bank has been frozen.")
    ents = ex.extract(text)
    persons = {e["text"] for e in ents if e["label"] == "PERSON"}
    labels = {e["text"]: e["label"] for e in ents}
    assert not persons
    assert labels.get("Enforcement Directorate") == "AGENCY"
    assert labels.get("Melur Police Station") == "POLICE_STATION"
    assert labels.get("Karur Vysya Bank") == "ORG"
    assert labels.get("43766277286409") == "ACCOUNT"


# ==========================================================================
# Graph
# ==========================================================================
def test_corroborating_layers_do_not_invent_edges(store, graph):
    """Co-location must never create a relationship on its own -- tower dumps
    put unconnected people in the same cell constantly."""
    nb, F = graph
    for a, b, d in F.edges(data=True):
        if set(d["layers"]) <= {"co_place"}:
            pytest.fail(f"{a}-{b} asserted from co-location alone")


def test_uncorroborated_observations_are_retained(graph):
    nb, F = graph
    assert len(nb.uncorroborated_observations) > 0


def test_fused_graph_is_connected_enough(graph):
    import networkx as nx
    nb, F = graph
    giant = max(nx.connected_components(F), key=len)
    assert len(giant) / F.number_of_nodes() > 0.85


# ==========================================================================
# Analytics
# ==========================================================================
def test_command_span_excludes_commercial_relations(store):
    """'Supplies to' is leverage, not command. Letting it propagate gave a
    cell lieutenant 658 subordinates in an 889-node graph."""
    sc = CommandAnalyzer(store, verbose=False).scores()
    pid = store.person_by_id
    lieut = [d["subordinate_span"] for v, d in sc.items()
             if pid.get(v, {}).get("role") == "LIEUTENANT"]
    kings = [d["subordinate_span"] for v, d in sc.items()
             if pid.get(v, {}).get("role") == "KINGPIN"]
    assert max(lieut) < 60, "lieutenant span implausibly large"
    assert sum(kings) / len(kings) > sum(lieut) / len(lieut), \
        "kingpins must out-span lieutenants"


def test_kingpins_have_fewer_direct_reports_but_deeper_span(store):
    sc = CommandAnalyzer(store, verbose=False).scores()
    pid = store.person_by_id
    k = [(d["direct_subordinates"], d["subordinate_span"]) for v, d in sc.items()
         if pid.get(v, {}).get("role") == "KINGPIN"]
    l = [(d["direct_subordinates"], d["subordinate_span"]) for v, d in sc.items()
         if pid.get(v, {}).get("role") == "LIEUTENANT"]
    assert sum(x[0] for x in k) / len(k) < sum(x[0] for x in l) / len(l)
    assert sum(x[1] for x in k) / len(k) > sum(x[1] for x in l) / len(l)


def test_key_player_ranking_beats_random(store, graph):
    nb, F = graph
    cmd = CommandAnalyzer(store, verbose=False).scores()
    an = NetworkAnalyzer(F, verbose=False)
    an.compute_centrality()
    an.detect_communities()
    an.key_players(command=cmd)
    gt = store.truth("gt_key_players")
    truth = set(gt.person_id)
    ids = [r["person_id"] for r in an.ranked_by("influence")]
    q = rank_quality(ids, truth)
    base = len(truth) / F.number_of_nodes()
    assert q["precision@25"] > base * 5


def test_ranked_by_preserves_command_scores(store, graph):
    """getattr(self,'_ranked', self.key_players()) evaluated the default
    eagerly and silently discarded the command scores."""
    nb, F = graph
    cmd = CommandAnalyzer(store, verbose=False).scores()
    an = NetworkAnalyzer(F, verbose=False)
    an.compute_centrality()
    an.detect_communities()
    an.key_players(command=cmd)
    assert any(r["command_score"] > 0 for r in an.ranked_by("command"))
    assert any(r["subordinate_span"] > 0 for r in an.ranked_by("command"))


def test_community_detection_recovers_syndicates(store, graph):
    nb, F = graph
    an = NetworkAnalyzer(F, verbose=False)
    an.detect_communities()
    truth = {r["person_id"]: r["syndicate_code"]
             for r in store.truth("gt_membership").to_dict("records")}
    nodes = [n for n in an.communities
             if truth.get(n) and truth[n] != "UNAFFILIATED"]
    try:
        from sklearn.metrics import adjusted_rand_score
        ari = adjusted_rand_score([truth[n] for n in nodes],
                                  [an.communities[n] for n in nodes])
        assert ari > 0.6
    except ImportError:
        assert an.modularity > 0.5


# ==========================================================================
# Entity resolution -- the safety-critical part
# ==========================================================================
def test_resolution_never_auto_merges(store):
    er = EntityResolver(store, verbose=False)
    props = er.resolve()
    assert all(p["auto_merged"] is False for p in props)
    assert all("HUMAN" in p["recommended_action"] or
               p["recommended_action"] in ("QUEUE_FOR_ANALYST_REVIEW",
                                           "RETAIN_AS_POSSIBLE_MATCH_ONLY",
                                           "NO_ACTION")
               for p in props)


def test_identical_names_different_people_are_not_escalated(store):
    """The corpus contains people who share a full name exactly. Escalating
    any of them to the top band is the failure this system exists to avoid."""
    er = EntityResolver(store, verbose=False)
    res = evaluate_resolution(er.resolve(), store.truth("gt_duplicates"))
    assert res["MEDIUM"]["namesakes_escalated"] == 0
    assert res["HIGH"]["namesakes_escalated"] == 0


def test_resolution_recall_and_blocking(store):
    er = EntityResolver(store, verbose=False)
    res = evaluate_resolution(er.resolve(), store.truth("gt_duplicates"))
    assert res["blocking_recall"] > 0.95
    assert res["MEDIUM"]["recall"] > 0.90


def test_blocking_is_cheaper_than_full_comparison(store):
    er = EntityResolver(store, verbose=False)
    pairs = er.candidate_pairs()
    n = len(store.persons)
    assert len(pairs) < n * (n - 1) / 2 * 0.02


# ==========================================================================
# Hidden links
# ==========================================================================
def test_hidden_links_are_not_already_known(store, graph):
    nb, F = graph
    lp = LinkPredictor(store, F, verbose=False)
    links = lp.run_all()
    known = lp._known
    for l in links:
        assert frozenset((l["person_a"], l["person_b"])) not in known


def test_hidden_links_require_verification(store, graph):
    nb, F = graph
    links = LinkPredictor(store, F, verbose=False).run_all()
    assert all(l["requires_human_verification"] for l in links)
    assert all(l["status"] == "UNVERIFIED" for l in links)


def test_hidden_link_recall(store, graph):
    nb, F = graph
    links = LinkPredictor(store, F, verbose=False).run_all()
    res = evaluate_links(links, store.truth("gt_latent"))
    assert res["_overall"]["recall"] > 0.90


def test_evidential_and_inferred_are_distinguished(store, graph):
    nb, F = graph
    links = LinkPredictor(store, F, verbose=False).run_all()
    kinds = {l["finding_type"] for l in links}
    assert kinds == {"EVIDENTIAL", "INFERRED"}


# ==========================================================================
# Anomalies
# ==========================================================================
def test_anomaly_recall(store):
    from sicnd.anomaly import AnomalyDetector, evaluate_anomalies
    sys.setrecursionlimit(20000)
    f = AnomalyDetector(store, verbose=False).run_all()
    res = evaluate_anomalies(f, store.truth("gt_anomalies"))
    assert res["_overall"]["recall"] > 0.85
    for p in ("STRUCTURING_SMURFING", "MULE_FANOUT", "ROUND_TRIPPING",
              "PRE_INCIDENT_CALL_BURST"):
        assert res[p]["recall"] >= 0.9, f"{p} regressed"


def test_findings_carry_evidence(store):
    from sicnd.anomaly import AnomalyDetector
    f = AnomalyDetector(store, verbose=False).run_all()
    assert all(x["evidence"] for x in f)
    assert all(x["requires_human_review"] for x in f)


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.dirname(os.path.abspath(__file__)), "-q"]))
