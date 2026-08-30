# -*- coding: utf-8 -*-
"""
Suspicious-pattern detection over financial and communication records.

Seven detectors, each targeting a documented typology. Every finding carries the
records that triggered it, so an analyst can reject it in seconds -- an alert
without its evidence is worse than no alert, because it still costs the time.

Detectors
  1 STRUCTURING_SMURFING   deposits parked just below a reporting threshold
  2 LAYERING_CHAIN         rapid multi-hop pass-through with value decay
  3 MULE_FANOUT            hub fans small transfers to many accounts, cashed out
  4 ROUND_TRIPPING         funds return to origin after a laundering circuit
  5 DORMANT_REACTIVATION   long-idle account suddenly moves a large sum through
  6 PRE_INCIDENT_CALL_BURST  co-ordination spike before an offence, then silence
  7 BURNER_SIM_ROTATION    SIM discarded, same contacts resume on same handset
"""

from __future__ import annotations

from collections import defaultdict, Counter

import networkx as nx
import numpy as np
import pandas as pd

from . import config as C


def _finding(pattern, entity_type, entity_ids, score, description,
             evidence, window=("", ""), persons=(), linked_incident=""):
    return {
        "pattern": pattern,
        "entity_type": entity_type,
        "entity_ids": list(entity_ids),
        "person_ids": list(persons),
        "risk_score": round(float(score), 4),
        "window_start": window[0],
        "window_end": window[1],
        "description": description,
        "evidence": evidence,
        "linked_incident_id": linked_incident,
        "requires_human_review": True,
    }


class AnomalyDetector:

    def __init__(self, store, verbose: bool = True):
        self.s = store
        self.verbose = verbose
        self._tx = None
        self._cdr = None

    def _log(self, m):
        if self.verbose:
            print(f"    {m}", flush=True)

    # ------------------------------------------------------------------
    @property
    def tx(self) -> pd.DataFrame:
        if self._tx is None:
            t = self.s.transactions.copy()
            t["ts"] = pd.to_datetime(t["timestamp"], errors="coerce")
            t["amount_inr"] = pd.to_numeric(t["amount_inr"], errors="coerce").fillna(0)
            self._tx = t.dropna(subset=["ts"]).sort_values("ts")
        return self._tx

    @property
    def cdr(self) -> pd.DataFrame:
        if self._cdr is None:
            c = self.s.cdr.copy()
            c["ts"] = pd.to_datetime(c["timestamp"], errors="coerce")
            self._cdr = c.dropna(subset=["ts"])
        return self._cdr

    # ==================================================================
    # 1. Structuring
    # ==================================================================
    def detect_structuring(self) -> list[dict]:
        A = C.Anomaly
        out = []
        cash = self.tx[self.tx["channel"].isin(["CASH_DEPOSIT", "CASH_WITHDRAWAL"])]
        if cash.empty:
            return out

        for thresh in A.STRUCTURING_THRESHOLDS:
            lo = thresh * (1 - A.STRUCTURING_BAND)
            band = cash[(cash["amount_inr"] >= lo) & (cash["amount_inr"] < thresh)]
            for acct, grp in band.groupby("dst_account_id"):
                if len(grp) < A.STRUCTURING_MIN_COUNT:
                    continue
                g = grp.sort_values("ts")
                # densest window of the configured length
                best = None
                for i in range(len(g)):
                    j = np.searchsorted(
                        g["ts"].values,
                        g["ts"].values[i] + np.timedelta64(A.STRUCTURING_WINDOW_DAYS, "D"),
                        side="right")
                    if (j - i) >= A.STRUCTURING_MIN_COUNT and \
                            (best is None or (j - i) > best[1] - best[0]):
                        best = (i, j)
                if not best:
                    continue
                w = g.iloc[best[0]:best[1]]
                total = float(w["amount_inr"].sum())
                depositors = sorted(set(w["src_person_id"]))
                holder = self.s.account_holders.get(acct, [""])[0]
                score = min(1.0, 0.35 + 0.05 * len(w) + 0.15 * (len(depositors) > 3))
                out.append(_finding(
                    "STRUCTURING_SMURFING", "ACCOUNT", [acct], score,
                    f"{len(w)} cash deposits between Rs.{lo:,.0f} and Rs.{thresh:,.0f} "
                    f"(each below the Rs.{thresh:,.0f} reporting threshold) into one "
                    f"account within {A.STRUCTURING_WINDOW_DAYS} days, totalling "
                    f"Rs.{total:,.0f}, from {len(depositors)} distinct depositors.",
                    {"deposit_count": len(w), "total_inr": total,
                     "threshold": thresh, "depositor_count": len(depositors),
                     "txn_ids": list(w["txn_id"])[:25]},
                    (str(w["ts"].min()), str(w["ts"].max())),
                    persons=[holder] + depositors[:10]))
        self._log(f"structuring:            {len(out):>5} findings")
        return out

    # ==================================================================
    # 2. Layering chains
    # ==================================================================
    def detect_layering(self) -> list[dict]:
        A = C.Anomaly
        tx = self.tx
        big = tx[tx["amount_inr"] >= tx["amount_inr"].quantile(0.90)]
        if big.empty:
            return []

        # adjacency: account -> outgoing transfers, time-ordered
        outgoing = defaultdict(list)
        for r in big.itertuples():
            outgoing[r.src_account_id].append(
                (r.ts, r.dst_account_id, float(r.amount_inr), r.txn_id))
        for k in outgoing:
            outgoing[k].sort()

        seen_chains, out = set(), []

        def extend(chain, txns):
            """chain = [acct...]; txns = [(ts, amount, txn_id)]"""
            last_acct = chain[-1]
            ts, amt = txns[-1][0], txns[-1][1]
            grown = False
            for nts, nxt, namt, ntid in outgoing.get(last_acct, []):
                if nxt in chain:
                    continue
                gap = (nts - ts).total_seconds() / 3600.0
                if not (0 <= gap <= A.LAYERING_MAX_GAP_HOURS):
                    continue
                if not (A.LAYERING_MIN_RETENTION <= namt / amt <= 1.02):
                    continue
                if len(chain) < A.LAYERING_MAX_HOPS:
                    grown = True
                    extend(chain + [nxt], txns + [(nts, namt, ntid)])
            if not grown and len(chain) - 1 >= A.LAYERING_MIN_HOPS:
                key = tuple(chain)
                if key in seen_chains:
                    return
                seen_chains.add(key)
                hops = len(chain) - 1
                retention = txns[-1][1] / txns[0][1]
                span = (txns[-1][0] - txns[0][0]).total_seconds() / 3600.0
                persons = []
                for a in chain:
                    persons += self.s.account_holders.get(a, [])
                out.append(_finding(
                    "LAYERING_CHAIN", "ACCOUNT_PATH", chain,
                    min(1.0, 0.4 + 0.08 * hops + 0.2 * (span < 48)),
                    f"{hops}-hop pass-through of Rs.{txns[0][1]:,.0f} completed in "
                    f"{span:.1f} hours, retaining {retention:.0%} of the original "
                    f"value (commission shaved at each hop).",
                    {"hops": hops, "initial_inr": txns[0][1],
                     "final_inr": txns[-1][1], "retention": round(retention, 4),
                     "span_hours": round(span, 2),
                     "txn_ids": [t[2] for t in txns]},
                    (str(txns[0][0]), str(txns[-1][0])),
                    persons=list(dict.fromkeys(persons))))

        for src, edges in list(outgoing.items()):
            for ts, dst, amt, tid in edges:
                extend([src, dst], [(ts, amt, tid)])
        self._log(f"layering chains:        {len(out):>5} findings")
        return out

    # ==================================================================
    # 3. Mule fan-out
    # ==================================================================
    def detect_mule_fanout(self) -> list[dict]:
        A = C.Anomaly
        tx = self.tx
        small = tx[(tx["amount_inr"] <= A.FANOUT_MAX_AMOUNT) &
                   (tx["channel"].isin(["IMPS", "UPI", "NEFT", "WALLET_TRANSFER"]))]
        out = []
        for src, grp in small.groupby("src_account_id"):
            if len(grp) < A.FANOUT_MIN_TARGETS:
                continue
            g = grp.sort_values("ts")
            times = g["ts"].values
            for i in range(len(g)):
                j = np.searchsorted(
                    times, times[i] + np.timedelta64(A.FANOUT_WINDOW_HOURS, "h"),
                    side="right")
                w = g.iloc[i:j]
                targets = set(w["dst_account_id"])
                if len(targets) < A.FANOUT_MIN_TARGETS:
                    continue
                # did the money leave as cash soon after?
                cashed = self._cash_out_count(targets, w["ts"].min())
                total = float(w["amount_inr"].sum())
                holder = self.s.account_holders.get(src, [""])[0]
                out.append(_finding(
                    "MULE_FANOUT", "ACCOUNT", [src],
                    min(1.0, 0.35 + 0.03 * len(targets) + 0.25 * (cashed > 2)),
                    f"Hub account fanned Rs.{total:,.0f} to {len(targets)} distinct "
                    f"accounts in {A.FANOUT_WINDOW_HOURS} hours, each transfer under "
                    f"Rs.{A.FANOUT_MAX_AMOUNT:,}; {cashed} recipients withdrew cash "
                    f"shortly after.",
                    {"target_count": len(targets), "total_inr": total,
                     "cash_out_recipients": cashed,
                     "target_accounts": sorted(targets)[:30],
                     "txn_ids": list(w["txn_id"])[:30]},
                    (str(w["ts"].min()), str(w["ts"].max())),
                    persons=[holder]))
                break   # one finding per hub is enough
        self._log(f"mule fan-out:           {len(out):>5} findings")
        return out

    def _cash_out_count(self, accounts, after, hours=24):
        tx = self.tx
        w = tx[(tx["channel"] == "CASH_WITHDRAWAL") &
               (tx["src_account_id"].isin(accounts)) &
               (tx["ts"] >= after) &
               (tx["ts"] <= after + pd.Timedelta(hours=hours))]
        return int(w["src_account_id"].nunique())

    # ==================================================================
    # 4. Round-tripping
    # ==================================================================
    def detect_round_tripping(self) -> list[dict]:
        A = C.Anomaly
        tx = self.tx
        big = tx[tx["amount_inr"] >= tx["amount_inr"].quantile(0.85)]
        G = nx.DiGraph()
        for r in big.itertuples():
            if G.has_edge(r.src_account_id, r.dst_account_id):
                G[r.src_account_id][r.dst_account_id]["txns"].append(
                    (r.ts, float(r.amount_inr), r.txn_id))
            else:
                G.add_edge(r.src_account_id, r.dst_account_id,
                           txns=[(r.ts, float(r.amount_inr), r.txn_id)])
        out, seen = [], set()
        try:
            cycles = nx.simple_cycles(G, length_bound=A.ROUNDTRIP_MAX_HOPS)
        except TypeError:                      # older networkx
            cycles = (c for c in nx.simple_cycles(G)
                      if len(c) <= A.ROUNDTRIP_MAX_HOPS)
        for cyc in cycles:
            if len(cyc) < 3:
                continue
            key = tuple(sorted(cyc))
            if key in seen:
                continue
            # simple_cycles returns an arbitrary rotation, so the node it starts
            # at is usually NOT where the money started. Try every rotation and
            # keep the first that is consistent in time; checking only one
            # rotation silently discards most genuine circuits.
            legs = None
            for rot in range(len(cyc)):
                order = cyc[rot:] + cyc[:rot]
                trial, ok = [], True
                for a, b in zip(order, order[1:] + order[:1]):
                    cand = sorted(G[a][b]["txns"])
                    if not trial:
                        trial.append(cand[0])
                        continue
                    nxt = [t for t in cand if t[0] >= trial[-1][0]]
                    if not nxt:
                        ok = False
                        break
                    trial.append(nxt[0])
                if ok and len(trial) >= 3:
                    legs = trial
                    cyc = order
                    break
            if not legs:
                continue
            start, end = legs[0][1], legs[-1][1]
            if abs(end - start) / start > A.ROUNDTRIP_TOLERANCE:
                continue
            seen.add(key)
            persons = []
            for a in cyc:
                persons += self.s.account_holders.get(a, [])
            span_days = (legs[-1][0] - legs[0][0]).total_seconds() / 86400
            out.append(_finding(
                "ROUND_TRIPPING", "ACCOUNT_CYCLE", list(cyc),
                min(1.0, 0.5 + 0.1 * len(cyc)),
                f"Rs.{start:,.0f} left one account and returned to it after "
                f"{len(cyc)} hops over {span_days:.1f} days, arriving back at "
                f"{end / start:.0%} of the amount that left.",
                {"hops": len(cyc), "out_inr": start, "back_inr": end,
                 "attrition": round(1 - end / start, 4),
                 "txn_ids": [l[2] for l in legs]},
                (str(legs[0][0]), str(legs[-1][0])),
                persons=list(dict.fromkeys(persons))))
        self._log(f"round-tripping:         {len(out):>5} findings")
        return out

    # ==================================================================
    # 5. Dormant reactivation
    # ==================================================================
    def detect_dormant_reactivation(self) -> list[dict]:
        A = C.Anomaly
        tx = self.tx
        out = []
        moves = pd.concat([
            tx[["ts", "src_account_id", "amount_inr", "txn_id"]]
              .rename(columns={"src_account_id": "acct"}).assign(dir="OUT"),
            tx[["ts", "dst_account_id", "amount_inr", "txn_id"]]
              .rename(columns={"dst_account_id": "acct"}).assign(dir="IN"),
        ]).sort_values("ts")

        for acct, g in moves.groupby("acct"):
            if len(g) < 2:
                continue
            g = g.sort_values("ts")
            gaps = g["ts"].diff().dt.days.fillna(0)
            # The detectable signature is the PASS-THROUGH: a large sum arrives
            # and leaves almost intact within hours. Prior dormancy makes it more
            # suspicious but is not required -- requiring it missed 93% of real
            # cases here, because these accounts also carry ordinary traffic that
            # closes the idle gap.
            candidates = g[(g["dir"] == "IN") &
                           (g["amount_inr"] >= A.DORMANT_MIN_AMOUNT)]
            for i in candidates.index:
                row = g.loc[i]
                gap = int(gaps.loc[i])
                was_dormant = gap >= A.DORMANT_MIN_GAP_DAYS
                after = g[(g["ts"] > row["ts"]) &
                          (g["ts"] <= row["ts"] + pd.Timedelta(
                              hours=A.DORMANT_PASSTHROUGH_HOURS)) &
                          (g["dir"] == "OUT")]
                if after.empty:
                    continue
                passed = float(after["amount_inr"].sum())
                ratio = passed / float(row["amount_inr"])
                if ratio < 0.7:
                    continue
                holder = self.s.account_holders.get(acct, [""])[0]
                lead = (f"Account idle for {gap} days then received"
                        if was_dormant else "Account received")
                out.append(_finding(
                    "DORMANT_REACTIVATION", "ACCOUNT", [acct],
                    min(1.0, 0.35 + 0.2 * (ratio > 0.9) + 0.25 * was_dormant),
                    f"{lead} Rs.{row['amount_inr']:,.0f} and moved {ratio:.0%} of "
                    f"it onward within {A.DORMANT_PASSTHROUGH_HOURS} hours "
                    f"(pass-through account).",
                    {"dormant_days": gap, "was_dormant": was_dormant,
                     "inflow_inr": float(row["amount_inr"]),
                     "outflow_inr": passed, "passthrough_ratio": round(ratio, 4),
                     "txn_ids": [row["txn_id"]] + list(after["txn_id"])[:10]},
                    (str(row["ts"]), str(after["ts"].max())),
                    persons=[holder]))
        self._log(f"dormant reactivation:   {len(out):>5} findings")
        return out

    # ==================================================================
    # 6. Pre-incident call burst
    # ==================================================================
    def detect_call_bursts(self) -> list[dict]:
        A = C.Anomaly
        cdr = self.cdr
        out = []
        inc = self.s.incidents.copy()
        inc["ts"] = pd.to_datetime(inc["incident_datetime"], errors="coerce")
        inc = inc.dropna(subset=["ts"])

        by_person = defaultdict(list)
        for r in cdr[["caller_person_id", "callee_person_id", "ts"]].itertuples():
            by_person[r.caller_person_id].append((r.ts, r.callee_person_id))
            by_person[r.callee_person_id].append((r.ts, r.caller_person_id))

        for r in inc.itertuples():
            actors = set(self.s.accused_of_incident.get(r.incident_id, []))
            if len(actors) < 2:
                continue
            t0 = r.ts
            lo = t0 - pd.Timedelta(hours=A.BURST_WINDOW_HOURS)
            inside = 0
            for a in actors:
                for ts, other in by_person.get(a, []):
                    if other in actors and lo <= ts <= t0:
                        inside += 1
            inside //= 2                     # each call seen from both ends
            if inside < A.BURST_MIN_CALLS:
                continue
            # baseline rate for the same group over the whole period
            total = 0
            for a in actors:
                total += sum(1 for _, o in by_person.get(a, []) if o in actors)
            total //= 2
            span_days = 365 * 8
            expected = total * (A.BURST_WINDOW_HOURS / 24) / span_days
            ratio = inside / expected if expected > 0 else float("inf")
            if ratio < A.BURST_RATIO:
                continue
            out.append(_finding(
                "PRE_INCIDENT_CALL_BURST", "PERSON_SET", sorted(actors),
                min(1.0, 0.4 + 0.02 * inside),
                f"{inside} calls among {len(actors)} co-accused inside the "
                f"{A.BURST_WINDOW_HOURS} hours before "
                f"{r.crime_type} at {r.area}, {r.city} -- "
                f"{ratio:.0f}x the group's own baseline rate.",
                {"calls_in_window": inside, "group_size": len(actors),
                 "baseline_expected": round(expected, 2),
                 "ratio_to_baseline": round(ratio, 1)},
                (str(lo), str(t0)),
                persons=sorted(actors), linked_incident=r.incident_id))
        self._log(f"pre-incident bursts:    {len(out):>5} findings")
        return out

    # ==================================================================
    # 7. Burner SIM rotation
    # ==================================================================
    def detect_burner_rotation(self) -> list[dict]:
        A = C.Anomaly
        cdr = self.cdr
        out = []

        contacts = defaultdict(set)
        active = defaultdict(list)
        for r in cdr[["caller_phone_id", "callee_person_id", "ts"]].itertuples():
            contacts[r.caller_phone_id].add(r.callee_person_id)
            active[r.caller_phone_id].append(r.ts)

        owner = self.s.phone_owner
        msisdn = self.s.msisdn_of
        for imei, phone_ids in self.s.phones_of_imei.items():
            if len(phone_ids) < 2:
                continue
            for i in range(len(phone_ids)):
                for j in range(i + 1, len(phone_ids)):
                    p1, p2 = phone_ids[i], phone_ids[j]
                    c1, c2 = contacts.get(p1, set()), contacts.get(p2, set())
                    if not c1 or not c2:
                        continue
                    jac = len(c1 & c2) / len(c1 | c2)
                    if jac < A.BURNER_MIN_OVERLAP:
                        continue
                    o1, o2 = owner.get(p1, ""), owner.get(p2, "")
                    a1 = active.get(p1, [])
                    a2 = active.get(p2, [])
                    if not a1 or not a2:
                        continue
                    same_person = (o1 == o2)

                    # Carrying two SIMs in one handset is ordinary; nearly every
                    # subject here does it. What is NOT ordinary is one SIM going
                    # dark as another takes over the same contacts. Without this
                    # succession test the detector fires on 1,194 pairs, almost
                    # all of them a person's normal dual-SIM usage.
                    s1, e1 = min(a1), max(a1)
                    s2, e2 = min(a2), max(a2)
                    overlap = (min(e1, e2) - max(s1, s2)).total_seconds()
                    span = (max(e1, e2) - min(s1, s2)).total_seconds()
                    overlap_frac = max(0.0, overlap) / span if span > 0 else 1.0
                    if same_person and overlap_frac > A.BURNER_MAX_OVERLAP_FRACTION:
                        continue      # concurrent dual-SIM, not a rotation
                    out.append(_finding(
                        "BURNER_SIM_ROTATION" if same_person else "SHARED_HANDSET",
                        "DEVICE", [imei],
                        min(1.0, 0.45 + jac),
                        (f"Two SIMs used in the same handset (IMEI {imei}) share "
                         f"{jac:.0%} of their contact set. ") +
                        (f"Both attributed to the same person: consistent with SIM "
                         f"rotation to defeat monitoring."
                         if same_person else
                         f"Registered to DIFFERENT subscribers -- handset sharing or "
                         f"identity substitution."),
                        {"imei": imei, "contact_jaccard": round(jac, 4),
                         "msisdn_a": msisdn.get(p1), "msisdn_b": msisdn.get(p2),
                         "subscriber_a": o1, "subscriber_b": o2,
                         "shared_contacts": len(c1 & c2),
                         "active_overlap_fraction": round(overlap_frac, 4)},
                        (str(min(min(a1), min(a2))), str(max(max(a1), max(a2)))),
                        persons=[x for x in {o1, o2} if x]))
        self._log(f"burner / shared handset:{len(out):>5} findings")
        return out

    # ==================================================================
    def run_all(self) -> list[dict]:
        findings = []
        findings += self.detect_structuring()
        findings += self.detect_layering()
        findings += self.detect_mule_fanout()
        findings += self.detect_round_tripping()
        findings += self.detect_dormant_reactivation()
        findings += self.detect_call_bursts()
        findings += self.detect_burner_rotation()
        findings.sort(key=lambda f: -f["risk_score"])
        for i, f in enumerate(findings, 1):
            f["finding_id"] = f"AN{i:05d}"
        self._log(f"TOTAL:                  {len(findings):>5} findings")
        return findings


# ==========================================================================
def evaluate_anomalies(findings: list[dict], truth_df) -> dict:
    """
    Recall per planted pattern. A planted anomaly counts as found when a finding
    of the same pattern names at least one of the same entities -- the analyst
    only needs to be pointed at the right account or group.
    """
    if truth_df.empty:
        return {}
    by_pattern = defaultdict(list)
    for f in findings:
        ids = set(f["entity_ids"]) | set(f["person_ids"])
        by_pattern[f["pattern"]].append(ids)

    # SHARED_HANDSET is the cross-subscriber case of the same detector
    by_pattern["BURNER_SIM_ROTATION"] += by_pattern.get("SHARED_HANDSET", [])

    res = {}
    for pattern, grp in truth_df.groupby("pattern"):
        planted = len(grp)
        found = 0
        for r in grp.to_dict("records"):
            want = set(str(r.get("entity_ids", "")).split("|")) - {""}
            if any(want & got for got in by_pattern.get(pattern, [])):
                found += 1
        res[pattern] = {
            "planted": planted, "detected": found,
            "recall": round(found / planted, 4) if planted else 0.0,
            "findings_raised": len(by_pattern.get(pattern, [])),
        }
    tot_p = sum(v["planted"] for v in res.values())
    tot_d = sum(v["detected"] for v in res.values())
    res["_overall"] = {"planted": tot_p, "detected": tot_d,
                       "recall": round(tot_d / tot_p, 4) if tot_p else 0.0,
                       "total_findings": len(findings)}
    return res
