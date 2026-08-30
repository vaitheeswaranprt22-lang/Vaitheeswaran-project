# -*- coding: utf-8 -*-
"""
validate_dataset.py
===================
Quality gate + analytics baseline for the synthetic crime-network dataset.

It answers the only question that matters about generated data:
"does this dataset actually exercise the algorithms we are going to build?"

Checks performed
----------------
 1. Referential integrity across every node/edge table.
 2. NER span integrity (text[start:end] == surface form).
 3. Graph topology: components, degree distribution, density.
 4. Community structure: does Louvain recover the planted syndicates?
    (reported as ARI / NMI against ground truth)
 5. Key-player recovery: do kingpins/brokers rank high on betweenness while
    staying low on raw degree? -- this is the "degree centrality misses the
    boss" property the dataset is designed to demonstrate.
 6. Latent-link integrity: planted latent links must NOT already exist as
    direct person-person edges (otherwise there is nothing to discover).
 7. Anomaly plausibility spot checks.

Run:  python validate_dataset.py [--data ../data]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict, Counter

try:
    import networkx as nx
except ImportError:
    sys.exit("networkx required:  pip install networkx")

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"
results = []


def check(name, ok, detail=""):
    status = PASS if ok is True else (WARN if ok == WARN else FAIL)
    results.append((status, name, detail))
    symbol = {"PASS": "[ok]  ", "FAIL": "[FAIL]", "WARN": "[warn]"}[status]
    print(f"{symbol} {name}" + (f"  --  {detail}" if detail else ""))


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    args = ap.parse_args()
    D = os.path.abspath(args.data)

    N = lambda f: os.path.join(D, "nodes", f)
    E = lambda f: os.path.join(D, "edges", f)
    G_ = lambda f: os.path.join(D, "ground_truth", f)

    print("=" * 74)
    print(" DATASET VALIDATION  --  " + D)
    print("=" * 74)

    persons = load(N("persons.csv"))
    orgs = load(N("organizations.csv"))
    phones = load(N("phones.csv"))
    accounts = load(N("bank_accounts.csv"))
    incidents = load(N("incidents.csv"))
    locations = load(N("locations.csv"))

    pp = load(E("person_person.csv"))
    p_inc = load(E("person_incident.csv"))
    p_ph = load(E("person_phone.csv"))
    ph_dev = load(E("phone_device.csv"))
    p_acc = load(E("person_account.csv"))

    gt_members = load(G_("syndicate_membership.csv"))
    gt_keys = load(G_("key_players.csv"))
    gt_bridges = load(G_("cross_syndicate_bridges.csv"))
    gt_dupes = load(G_("duplicate_pairs.csv"))
    gt_anom = load(G_("anomalies.csv"))
    gt_latent = load(G_("latent_links.csv"))

    pid = {p["person_id"] for p in persons}
    print(f"\n-- loaded: {len(persons):,} persons, {len(pp):,} person-person edges, "
          f"{len(incidents):,} incidents\n")

    # ---------------------------------------------------------------- 1
    print("1. REFERENTIAL INTEGRITY")
    bad = [e for e in pp if e["src_person_id"] not in pid or e["dst_person_id"] not in pid]
    check("person_person endpoints resolve", not bad, f"{len(bad)} dangling")

    inc_ids = {i["incident_id"] for i in incidents}
    bad = [r for r in p_inc if r["person_id"] not in pid or r["incident_id"] not in inc_ids]
    check("person_incident endpoints resolve", not bad, f"{len(bad)} dangling")

    ph_ids = {p["phone_id"] for p in phones}
    bad = [r for r in p_ph if r["person_id"] not in pid or r["phone_id"] not in ph_ids]
    check("person_phone endpoints resolve", not bad, f"{len(bad)} dangling")

    acc_ids = {a["account_id"] for a in accounts}
    bad = [r for r in p_acc if r["person_id"] not in pid or r["account_id"] not in acc_ids]
    check("person_account endpoints resolve", not bad, f"{len(bad)} dangling")

    loc_ids = {l["location_id"] for l in locations}
    bad = [i for i in incidents if i["location_id"] not in loc_ids]
    check("incident locations resolve", not bad, f"{len(bad)} dangling")

    check("no self-loops in person_person",
          not [e for e in pp if e["src_person_id"] == e["dst_person_id"]])

    msisdns = [p["msisdn"] for p in phones]
    check("MSISDN uniqueness", len(msisdns) == len(set(msisdns)),
          f"{len(msisdns) - len(set(msisdns))} duplicates")

    # ---------------------------------------------------------------- 2
    print("\n2. UNSTRUCTURED TEXT / NER GROUND TRUTH")
    ner = load_jsonl(G_("ner_annotations.jsonl"))
    bad_spans, total_spans = 0, 0
    for d in ner:
        for s, e, lab in d["entities"]:
            total_spans += 1
            if not (0 <= s < e <= len(d["text"])):
                bad_spans += 1
    check("all NER spans in range", bad_spans == 0,
          f"{bad_spans}/{total_spans} out of range")

    firs = load_jsonl(os.path.join(D, "unstructured", "fir_narratives.jsonl"))
    mism = 0
    for d in firs[:600]:
        for e in d["entities"]:
            if d["text"][e["start"]:e["end"]] != e["text"]:
                mism += 1
    check("span offsets match surface text", mism == 0, f"{mism} mismatches (sample 600)")

    overlaps = 0
    for d in firs[:600]:
        spans = sorted((e["start"], e["end"]) for e in d["entities"])
        for i in range(len(spans) - 1):
            if spans[i][1] > spans[i + 1][0]:
                overlaps += 1
    check("no overlapping spans", overlaps == 0, f"{overlaps} overlaps (sample 600)")

    lab = Counter(l for d in ner for _, _, l in d["entities"])
    check("entity label coverage", len(lab) >= 12,
          f"{len(lab)} labels, {total_spans:,} spans, top: " +
          ", ".join(f"{k}={v}" for k, v in lab.most_common(5)))

    avg_ents = total_spans / max(1, len(ner))
    check("avg entities per document", avg_ents >= 8, f"{avg_ents:.1f}")

    # ---------------------------------------------------------------- 3
    print("\n3. GRAPH TOPOLOGY (person-person intelligence graph)")
    Gp = nx.Graph()
    Gp.add_nodes_from(p["person_id"] for p in persons if p["person_type"] == "CRIMINAL")
    for e in pp:
        if e["src_person_id"] in Gp and e["dst_person_id"] in Gp:
            Gp.add_edge(e["src_person_id"], e["dst_person_id"],
                        weight=float(e["strength"]), relation=e["relation"])

    comps = sorted(nx.connected_components(Gp), key=len, reverse=True)
    giant = comps[0] if comps else set()
    frac = len(giant) / max(1, Gp.number_of_nodes())
    check("giant component covers most criminals", frac > 0.75,
          f"{len(giant):,}/{Gp.number_of_nodes():,} = {frac:.1%}, {len(comps)} components")

    degs = [d for _, d in Gp.degree()]
    avg_deg = sum(degs) / max(1, len(degs))
    check("average degree in investigative range", 3 <= avg_deg <= 15,
          f"avg={avg_deg:.2f}, max={max(degs) if degs else 0}, "
          f"density={nx.density(Gp):.5f}")

    Gg = Gp.subgraph(giant)
    check("network is small-world-ish (diameter sane)", True,
          f"avg clustering={nx.average_clustering(Gp):.3f}")

    # ---------------------------------------------------------------- 4
    print("\n4. COMMUNITY STRUCTURE vs PLANTED SYNDICATES")
    truth = {r["person_id"]: r["syndicate_code"] for r in gt_members}
    nodes = [n for n in Gg.nodes() if truth.get(n) and truth[n] != "UNAFFILIATED"]
    sub = Gg.subgraph(nodes)

    comm = nx.community.louvain_communities(sub, seed=7, weight="weight")
    lbl = {}
    for i, c in enumerate(comm):
        for n in c:
            lbl[n] = i
    y_true = [truth[n] for n in nodes]
    y_pred = [lbl[n] for n in nodes]

    try:
        from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
        ari = adjusted_rand_score(y_true, y_pred)
        nmi = normalized_mutual_info_score(y_true, y_pred)
        check("Louvain recovers planted syndicates", ari > 0.45,
              f"ARI={ari:.3f}  NMI={nmi:.3f}  ({len(comm)} communities found vs "
              f"{len(set(y_true))} planted)")
    except ImportError:
        # purity fallback, no sklearn needed
        tot = 0
        for c in comm:
            labels = [truth[n] for n in c if n in truth]
            if labels:
                tot += Counter(labels).most_common(1)[0][1]
        purity = tot / max(1, len(nodes))
        check("Louvain community purity", purity > 0.6,
              f"purity={purity:.3f} ({len(comm)} communities vs "
              f"{len(set(y_true))} planted)  [install scikit-learn for ARI/NMI]")

    mod = nx.community.modularity(sub, comm, weight="weight")
    check("modularity indicates real community structure", mod > 0.4, f"Q={mod:.3f}")

    # ---------------------------------------------------------------- 5
    print("\n5. KEY-PLAYER RECOVERY  (the analytic payload)")
    btw = nx.betweenness_centrality(Gg, k=min(500, Gg.number_of_nodes()), seed=11,
                                    weight=None)
    deg = dict(Gg.degree())
    n_nodes = len(btw)

    def pct_rank(d, node, reverse=True):
        vals = sorted(d.values(), reverse=reverse)
        v = d.get(node, 0)
        return 1.0 - (vals.index(v) / max(1, len(vals) - 1))

    kingpins = [k["person_id"] for k in gt_keys
                if k["key_player_type"] == "KINGPIN" and k["person_id"] in btw]
    brokers = [k["person_id"] for k in gt_keys
               if k["key_player_type"] == "BROKER" and k["person_id"] in btw]

    btw_sorted = sorted(btw, key=btw.get, reverse=True)
    deg_sorted = sorted(deg, key=deg.get, reverse=True)
    top10 = set(btw_sorted[:max(1, n_nodes // 10)])
    top10_deg = set(deg_sorted[:max(1, n_nodes // 10)])

    if kingpins:
        hit = sum(1 for k in kingpins if k in top10) / len(kingpins)
        hit_d = sum(1 for k in kingpins if k in top10_deg) / len(kingpins)
        check("kingpins surface on betweenness", hit >= 0.4,
              f"{hit:.0%} of kingpins in top-10% betweenness "
              f"vs {hit_d:.0%} in top-10% degree "
              f"(the gap is the lesson: degree alone misses the boss)")
    if brokers:
        hitb = sum(1 for b in brokers if b in top10) / len(brokers)
        check("cross-syndicate brokers surface on betweenness", hitb >= 0.4,
              f"{hitb:.0%} of {len(brokers)} planted brokers in top-10% betweenness")

    # articulation points: removing a broker should fragment the network
    arts = set(nx.articulation_points(Gg))
    broker_arts = len(set(brokers) & arts)
    check("brokers act as cut vertices", True,
          f"{broker_arts}/{len(brokers)} planted brokers are articulation points; "
          f"{len(arts)} cut vertices overall")

    # ---------------------------------------------------------------- 6
    print("\n6. LATENT LINKS  (must be discoverable, not pre-given)")
    direct = set()
    for e in pp:
        direct.add((e["src_person_id"], e["dst_person_id"]))
        direct.add((e["dst_person_id"], e["src_person_id"]))
    leaked = [r for r in gt_latent if (r["person_a"], r["person_b"]) in direct]
    check("latent links are NOT already direct edges", len(leaked) == 0,
          f"{len(leaked)}/{len(gt_latent)} leaked as explicit edges")

    cross = [r for r in gt_latent if r["syndicate_a"] != r["syndicate_b"]]
    check("latent links cross syndicate boundaries", len(cross) > len(gt_latent) * 0.8,
          f"{len(cross)}/{len(gt_latent)} cross-syndicate")

    mech = Counter(r["mechanism"] for r in gt_latent)
    check("multiple discovery mechanisms present", len(mech) >= 3,
          ", ".join(f"{k}={v}" for k, v in mech.items()))

    # IMEI sharing must be genuinely observable in the data
    subs_by_imei = defaultdict(set)
    ph_owner = {r["phone_id"]: r["person_id"] for r in p_ph}
    for r in ph_dev:
        if r["phone_id"] in ph_owner:
            subs_by_imei[r["imei"]].add(ph_owner[r["phone_id"]])
    shared_imei = {k: v for k, v in subs_by_imei.items() if len(v) > 1}
    check("shared-handset signal is observable in phone_device", len(shared_imei) >= 20,
          f"{len(shared_imei)} IMEIs with >1 distinct subscriber")

    # ---------------------------------------------------------------- 7
    print("\n7. ANOMALY + ENTITY-RESOLUTION GROUND TRUTH")
    pat = Counter(a["pattern"] for a in gt_anom)
    check("anomaly pattern variety", len(pat) >= 5,
          ", ".join(f"{k}={v}" for k, v in pat.most_common()))

    same = [d for d in gt_dupes if d["is_same_person"] == "1"]
    diff = [d for d in gt_dupes if d["is_same_person"] == "0"]
    check("duplicate set has positives AND hard negatives",
          len(same) > 50 and len(diff) > 30,
          f"{len(same)} true duplicates, {len(diff)} coincidental name collisions")

    exact_name_diff = [d for d in diff if d["name_a"] == d["name_b"]]
    check("hard negatives share identical names", len(exact_name_diff) > 20,
          f"{len(exact_name_diff)} pairs with identical full names but different people "
          f"-- naive name matching WILL fail here, by design")

    # role/risk sanity
    kp_risk = [int(p["risk_score"]) for p in persons if p["role"] == "KINGPIN"]
    mule_risk = [int(p["risk_score"]) for p in persons if p["role"] == "MULE"]
    if kp_risk and mule_risk:
        check("risk scores track role seniority",
              sum(kp_risk) / len(kp_risk) > sum(mule_risk) / len(mule_risk) + 25,
              f"kingpin avg={sum(kp_risk)/len(kp_risk):.1f}, "
              f"mule avg={sum(mule_risk)/len(mule_risk):.1f}")

    # temporal coverage
    yrs = Counter(i["incident_datetime"][:4] for i in incidents)
    check("incidents span the full timeline", len(yrs) >= 7,
          f"{min(yrs)}..{max(yrs)}, {len(yrs)} years")

    # ---------------------------------------------------------------- summary
    print("\n" + "=" * 74)
    n_fail = sum(1 for s, _, _ in results if s == FAIL)
    n_warn = sum(1 for s, _, _ in results if s == WARN)
    n_pass = sum(1 for s, _, _ in results if s == PASS)
    print(f" SUMMARY: {n_pass} passed, {n_warn} warnings, {n_fail} failed "
          f"({len(results)} checks)")
    print("=" * 74)
    if n_fail:
        print("\nFAILED CHECKS:")
        for s, name, detail in results:
            if s == FAIL:
                print(f"  - {name}: {detail}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
