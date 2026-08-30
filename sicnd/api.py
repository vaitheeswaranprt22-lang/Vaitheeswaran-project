# -*- coding: utf-8 -*-
"""
HTTP API for the investigator console.

Loads the artefacts produced by the pipeline once at startup and serves them.
Analyst decisions (accept / reject on a proposed merge or link) are appended to
an audit log -- the human verification step is a recorded action, not a UI
nicety, because "who confirmed this link, and when" is the question that gets
asked afterwards.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime

import networkx as nx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config as C
from .ingest import Store
from .analytics import PathExplainer
from .graphbuild import NetworkBuilder
from .textsim import name_similarity, normalize

AUDIT_LOG = os.path.join(C.DERIVED, "analyst_decisions.jsonl")


def _load(name, default):
    path = os.path.join(C.DERIVED, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class State:
    """Everything the API serves, loaded once."""

    def __init__(self):
        print("loading artefacts ...", flush=True)
        self.store = Store(verbose=False).load_all()
        self.nodes = _load("graph_nodes.json", [])
        self.edges = _load("graph_edges.json", [])
        self.key_players = _load("key_players.json", [])
        self.communities = _load("communities.json", [])
        self.anomalies = _load("anomaly_findings.json", [])
        self.links = _load("hidden_links.json", [])
        self.proposals = _load("resolution_proposals.json", [])
        self.disruption = _load("disruption_simulation.json", [])
        self.scorecard = _load("scorecard.json", {})
        self.summary = _load("run_summary.json", {})
        self.node_comm = _load("node_communities.json", {})
        self.extracted_relations = _load("extracted_relations.json", [])

        self.kp_by_id = {r["person_id"]: r for r in self.key_players}
        self.node_by_id = {n["id"]: n for n in self.nodes}

        self.G = nx.Graph()
        for n in self.nodes:
            self.G.add_node(n["id"], **{k: v for k, v in n.items() if k != "id"})
        for e in self.edges:
            self.G.add_edge(e["source"], e["target"], weight=e.get("weight", 0),
                            layers=e.get("layers", []),
                            corroboration=e.get("corroboration", 1),
                            detail=e.get("detail", {}))

        print("  building heterogeneous graph for path explanation ...", flush=True)
        self.H = NetworkBuilder(self.store, verbose=False).build_heterogeneous()
        self.paths = PathExplainer(self.H)
        print(f"ready: {self.G.number_of_nodes():,} nodes, "
              f"{self.G.number_of_edges():,} edges", flush=True)


state: State | None = None
app = FastAPI(title="Criminal Network Analysis System", version="1.0")


@app.on_event("startup")
def _startup():
    global state
    state = State()


# ==========================================================================
@app.get("/api/summary")
def summary():
    s = state.store
    return {
        **state.summary,
        "dataset": {
            "persons": len(s.persons),
            "criminals": len(s.criminals),
            "organizations": len(s.organizations),
            "incidents": len(s.incidents),
            "phones": len(s.phones),
            "accounts": len(s.accounts),
            "vehicles": len(s.vehicles),
            "cdr_records": len(s.cdr),
            "transactions": len(s.transactions),
            "documents": len(s.documents()),
        },
        "findings": {
            "key_players": len(state.key_players),
            "anomalies": len(state.anomalies),
            "hidden_links": len(state.links),
            "resolution_proposals": len(state.proposals),
        },
        "synthetic_data_notice": (
            "All data is synthetic. No real person is represented."),
    }


@app.get("/api/scorecard")
def scorecard():
    return state.scorecard


# ==========================================================================
@app.get("/api/search")
def search(q: str = Query(..., min_length=1), limit: int = 25):
    """Search people, phones, accounts, vehicles and organisations at once."""
    ql = normalize(q)
    s = state.store
    out = []

    for r in s.persons.fillna("").itertuples():
        score = 0.0
        if ql in normalize(r.full_name):
            score = 0.95
        elif ql in normalize(r.alias or ""):
            score = 0.9
        else:
            sim = name_similarity(ql, r.full_name)
            if sim > 0.80:
                score = sim
        if score:
            kp = state.kp_by_id.get(r.person_id, {})
            out.append({"type": "Person", "id": r.person_id,
                        "label": r.full_name, "alias": r.alias,
                        "detail": f"{r.role or r.person_type} | {r.native_city}, "
                                  f"{r.native_state}",
                        "risk": int(r.risk_score or 0),
                        "influence_rank": kp.get("rank"),
                        "score": round(score, 3)})

    if q.isdigit():
        for r in s.phones.itertuples():
            if q in str(r.msisdn):
                owner = s.phone_owner.get(r.phone_id, "")
                out.append({"type": "Phone", "id": r.phone_id, "label": r.msisdn,
                            "detail": f"{r.operator} | subscriber: "
                                      f"{s.person_by_id.get(owner, {}).get('full_name', '?')}",
                            "score": 0.9})
        for r in s.accounts.itertuples():
            if q in str(r.account_number):
                out.append({"type": "BankAccount", "id": r.account_id,
                            "label": r.account_number,
                            "detail": f"{r.bank} | {r.holder_name}", "score": 0.9})

    qu = q.upper().replace(" ", "")
    for r in s.vehicles.itertuples():
        if qu in str(r.registration_no).replace(" ", ""):
            out.append({"type": "Vehicle", "id": r.vehicle_id,
                        "label": r.registration_no,
                        "detail": f"{r.make} {r.model} | {r.owner_name_on_record}",
                        "score": 0.9})
    for r in s.organizations.itertuples():
        if ql in normalize(r.name):
            out.append({"type": "Organization", "id": r.org_id, "label": r.name,
                        "detail": f"{r.org_type} | {r.hq_city}", "score": 0.85})

    out.sort(key=lambda x: -x["score"])
    return {"query": q, "count": len(out), "results": out[:limit]}


# ==========================================================================
@app.get("/api/person/{person_id}")
def person(person_id: str):
    s = state.store
    p = s.person_by_id.get(person_id)
    if not p:
        raise HTTPException(404, "person not found")

    phones = [{"phone_id": ph, "msisdn": s.msisdn_of.get(ph),
               "imei": s.imei_of_phone.get(ph)}
              for ph in s.phones_of.get(person_id, [])]
    accounts = []
    for ac in s.accounts_of.get(person_id, []):
        row = s.accounts[s.accounts.account_id == ac]
        if not row.empty:
            r = row.iloc[0]
            accounts.append({"account_id": ac, "account_number": r.account_number,
                             "bank": r.bank, "status": r.status,
                             "is_mule": int(r.is_mule_account)})
    incidents = []
    for i in s.incidents_of_person.get(person_id, [])[:40]:
        inc = s.incident_by_id.get(i)
        if inc:
            incidents.append({"incident_id": i, "fir_no": inc["fir_no"],
                              "crime_type": inc["crime_type"],
                              "date": inc["incident_datetime"],
                              "city": inc["city"], "state": inc["state"],
                              "severity": inc["severity"]})
    incidents.sort(key=lambda x: x["date"], reverse=True)

    rel = []
    for r in s.person_person.itertuples():
        if r.src_person_id == person_id or r.dst_person_id == person_id:
            other = (r.dst_person_id if r.src_person_id == person_id
                     else r.src_person_id)
            rel.append({"person_id": other,
                        "name": s.person_by_id.get(other, {}).get("full_name", ""),
                        "relation": r.relation,
                        "direction": "outgoing" if r.src_person_id == person_id else "incoming",
                        "strength": float(r.strength),
                        "verified": int(r.is_verified),
                        "source": r.source_type})

    return {
        "profile": p,
        "analytics": state.kp_by_id.get(person_id, {}),
        "community": state.node_comm.get(person_id),
        "phones": phones, "accounts": accounts,
        "incidents": incidents, "relationships": rel,
        "anomalies": [a for a in state.anomalies
                      if person_id in a.get("person_ids", [])][:20],
        "hidden_links": [l for l in state.links
                         if person_id in (l["person_a"], l["person_b"])][:20],
    }


@app.get("/api/ego/{person_id}")
def ego(person_id: str, depth: int = 1, min_corroboration: int = 1,
        limit: int = 120):
    if person_id not in state.G:
        raise HTTPException(404, "node not in graph")
    seen = {person_id}
    frontier = {person_id}
    for _ in range(max(1, min(depth, 3))):
        nxt = set()
        for v in frontier:
            for u in state.G.neighbors(v):
                if state.G[v][u].get("corroboration", 1) >= min_corroboration:
                    nxt.add(u)
        seen |= nxt
        frontier = nxt
        if len(seen) > limit:
            break
    seen = set(list(seen)[:limit])
    sub = state.G.subgraph(seen)
    return _graph_payload(sub, focus=person_id)


def _graph_payload(sub, focus=None):
    nodes = []
    for v, d in sub.nodes(data=True):
        kp = state.kp_by_id.get(v, {})
        nodes.append({
            "id": v, "label": d.get("name", v), "alias": d.get("alias", ""),
            "role": d.get("role", ""), "syndicate": d.get("syndicate", ""),
            "risk": d.get("risk", 0), "person_type": d.get("person_type", ""),
            "community": state.node_comm.get(v, -1),
            "influence": kp.get("influence_score", 0),
            "rank": kp.get("rank"),
            "inferred_role": kp.get("inferred_role", ""),
            "is_focus": v == focus,
        })
    edges = [{"source": a, "target": b, "weight": d.get("weight", 0),
              "layers": d.get("layers", []),
              "corroboration": d.get("corroboration", 1)}
             for a, b, d in sub.edges(data=True)]
    return {"nodes": nodes, "edges": edges}


@app.get("/api/graph")
def graph(min_corroboration: int = 2, syndicate: str = "", community: int = -1,
          limit: int = 400):
    """A readable slice of the network for the initial view."""
    G = state.G
    keep = []
    for v, d in G.nodes(data=True):
        if syndicate and d.get("syndicate") != syndicate:
            continue
        if community >= 0 and state.node_comm.get(v, -1) != community:
            continue
        keep.append(v)
    # prefer the most important nodes when trimming
    keep.sort(key=lambda v: -(state.kp_by_id.get(v, {}).get("influence_score", 0)))
    keep = set(keep[:limit])
    sub = nx.Graph()
    sub.add_nodes_from((v, G.nodes[v]) for v in keep)
    for a, b, d in G.edges(data=True):
        if a in keep and b in keep and d.get("corroboration", 1) >= min_corroboration:
            sub.add_edge(a, b, **d)
    return _graph_payload(sub)


# ==========================================================================
@app.get("/api/keyplayers")
def keyplayers(ranking: str = "influence", limit: int = 50):
    key = {"influence": "influence_score", "command": "command_score",
           "broker": "broker_score", "structural": "structural_score"}
    if ranking not in key:
        raise HTTPException(400, f"ranking must be one of {list(key)}")
    rows = sorted(state.key_players, key=lambda r: -r.get(key[ranking], 0))
    return {"ranking": ranking, "results": rows[:limit]}


@app.get("/api/communities")
def communities():
    return {"count": len(state.communities), "communities": state.communities}


@app.get("/api/disruption")
def disruption():
    return {"simulation": state.disruption}


@app.get("/api/anomalies")
def anomalies(pattern: str = "", min_score: float = 0.0, limit: int = 100):
    rows = [a for a in state.anomalies
            if (not pattern or a["pattern"] == pattern)
            and a["risk_score"] >= min_score]
    return {"count": len(rows),
            "patterns": dict(Counter(a["pattern"] for a in state.anomalies)),
            "results": rows[:limit]}


@app.get("/api/links")
def links(finding_type: str = "", mechanism: str = "", limit: int = 100):
    rows = [l for l in state.links
            if (not finding_type or l["finding_type"] == finding_type)
            and (not mechanism or mechanism in l["mechanism"])]
    return {"count": len(rows),
            "mechanisms": dict(Counter(m for l in state.links
                                       for m in l["mechanism"].split("|"))),
            "results": rows[:limit]}


@app.get("/api/resolution")
def resolution(band: str = "", limit: int = 100):
    rows = [p for p in state.proposals
            if not band or p["confidence_band"] == band]
    return {"count": len(rows),
            "bands": dict(Counter(p["confidence_band"] for p in state.proposals)),
            "note": ("Proposals only. This system performs no automatic merges; "
                     "each pair requires an analyst decision."),
            "results": rows[:limit]}


@app.get("/api/path")
def path(a: str, b: str, mode: str = "shortest", cutoff: int = 4):
    if mode == "all":
        res = state.paths.all_paths(a, b, cutoff=cutoff)
        return {"paths": res, "count": len(res)}
    res = state.paths.shortest(a, b)
    if not res:
        return {"paths": [], "count": 0,
                "message": "No path found within the evidence graph."}
    return {"paths": [res], "count": 1}


@app.get("/api/document/{doc_id}")
def document(doc_id: str):
    for d in state.store.documents():
        if d["doc_id"] == doc_id:
            return d
    raise HTTPException(404, "document not found")


@app.get("/api/documents")
def documents(person_id: str = "", limit: int = 20):
    out = []
    for d in state.store.documents():
        if person_id and person_id not in d.get("linked_person_ids", []):
            continue
        out.append({k: v for k, v in d.items() if k != "entities"})
        if len(out) >= limit:
            break
    return {"count": len(out), "results": out}


# ==========================================================================
class Decision(BaseModel):
    item_type: str          # "resolution" | "link" | "anomaly"
    item_id: str
    decision: str           # "CONFIRMED" | "REJECTED" | "DEFERRED"
    analyst: str = "analyst"
    note: str = ""


@app.post("/api/review")
def review(d: Decision):
    """
    Record a human decision. This is the only way anything in this system
    becomes 'confirmed' -- there is no code path that sets it automatically.
    """
    if d.decision not in ("CONFIRMED", "REJECTED", "DEFERRED"):
        raise HTTPException(400, "decision must be CONFIRMED, REJECTED or DEFERRED")
    rec = {**d.dict(), "recorded_at": datetime.now().isoformat(timespec="seconds")}
    with open(AUDIT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {"status": "recorded", "entry": rec}


@app.get("/api/review")
def review_log(limit: int = 200):
    if not os.path.exists(AUDIT_LOG):
        return {"count": 0, "entries": []}
    with open(AUDIT_LOG, encoding="utf-8") as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    return {"count": len(rows), "entries": rows[-limit:][::-1]}


# ==========================================================================
@app.get("/")
def index():
    return FileResponse(os.path.join(C.UI, "index.html"))


if os.path.isdir(C.UI):
    app.mount("/ui", StaticFiles(directory=C.UI), name="ui")


def main():
    import uvicorn
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    uvicorn.run("sicnd.api:app", host=a.host, port=a.port, reload=False)


if __name__ == "__main__":
    main()
