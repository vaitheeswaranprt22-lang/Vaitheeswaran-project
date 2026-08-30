# SICND — AI-Powered Criminal Network Analysis System

Ingests fragmented crime data (FIRs, CDRs, bank statements, surveillance reports,
intelligence notes), extracts entities and relationships from unstructured text,
builds a multi-layer relationship graph, and surfaces **key players, hidden
links, criminal networks and suspicious patterns** — with every claim traceable
to the records that produced it, and every merge or confirmation left to a human.

Includes a generated dataset with **ground-truth answer keys**, so every stage is
measured rather than demonstrated.

> **All data is synthetic.** No real person, gang, phone number, bank account or
> vehicle is represented. Geography and statute sections (IPC / BNS 2023 / NDPS /
> PMLA / Arms Act) are real only so the data behaves realistically. No
> Aadhaar-, PAN- or passport-format identifiers are generated anywhere.

---

## Quick start

```bash
pip install -r requirements.txt
```

```bash
python data_generator/generate_dataset.py
```

```bash
python run_pipeline.py
```

```bash
python -m uvicorn sicnd.api:app --port 8000
```

Then open **http://127.0.0.1:8000**. Full pipeline runs in ~38s.

```bash
python -m pytest tests -q
```

---

## Results

Every number below is measured against the ground truth shipped with the
dataset. Real seized data has no answer key, so none of this could be computed
on it.

| Task | Metric | Result |
|---|---|---|
| **Entity extraction** | typed P / R / F1 | 0.999 / 0.998 **0.999** |
| **Key players** | P@10, P@25, AP (vs all true key players) | 1.00, 1.00, **0.942** |
| **Command hierarchy** | AP vs kingpins / lieutenants | 0.480 / **0.625**, recall@100 = 1.00 |
| **Brokers** | AP vs planted cross-syndicate conduits | 0.261 (base rate 0.018) |
| **Community detection** | ARI / NMI / modularity | **0.838** / 0.862 / 0.820 |
| **Entity resolution** | recall @ review band | **0.991** |
| | identical-name traps wrongly escalated | **0 / 84** |
| | blocking recall (2,060 pairs vs 1.43M) | 0.991 |
| **Anomaly detection** | overall recall, 7 patterns | **0.94** (5 patterns at 1.00) |
| **Hidden links** | overall recall | **1.00** (211/212) |
| **Automatic merges / confirmations** | | **0** — by construction |

---

## What the system does

```
 FIRs · CDR · bank statements · surveillance · intel notes · registries
                              │
   1. INGEST        24 feeds, provenance tracked, 305k rows
                              │
   2. NLP           entity + relation extraction from 3,220 documents
                              │
   3. GRAPH         5 evidence layers → one fused relationship map
                              │
   4. ANALYTICS     centrality · command hierarchy · communities · disruption
                              │
   5. RESOLUTION    duplicate identities → proposals, never merges
                              │
   6. ANOMALIES     7 financial / communication typologies
                              │
   7. LINKS         hidden connections nobody recorded
                              │
   8. CONSOLE       investigator UI + audit log
```

### 1. Ingestion
24 structured feeds and 3 unstructured ones, each tagged with its source system.
Identifier columns are forced to text — a phone number read as `int64` silently
stops joining against the same number stored as text, which broke
CDR→subscriber resolution during development.

### 2. Entity & relation extraction
A **cascade**, not a single pass. High-precision types are extracted and their
spans *masked* before ambiguous ones are attempted, because "Bank of Baroda",
"Najafgarh Police Station" and "Enforcement Directorate" are all capitalised
multi-token sequences a naive person-name detector swallows whole.

```
regex (date, money, phone, vehicle, account, IMEI)
  → structural (police station)
    → closed gazetteers (agency, bank/org, contraband, vehicle)
      → geography (city vs locality, disambiguated by context)
        → alias ("@ …", the convention throughout Indian FIRs)
          → person (what survives, validated against a name lexicon)
```

15 entity types, **typed F1 0.999**. Relations are pulled from phrasing like
*"at the instance of"*, *"under the direction of"*, *"benami of"* — each carrying
the sentence it came from, because an extracted relation is a claim, not a fact.

### 3. Graph construction — what may assert a relationship
Five layers: `intel`, `comm` (CDR lifted phone→person), `money`, `co_event`
(co-accused), `co_place` (co-location).

**Only some may create edges.** Being recorded as an associate, phoning someone
repeatedly, or paying them is a relationship. Standing in the same locality on
the same day is not — tower dumps put hundreds of unconnected people in the same
cell every hour. Letting co-location assert edges added 7,243 links against the
intel layer's 2,763 and dissolved the command hierarchy entirely.

Corroborating evidence therefore *strengthens* an edge other evidence already
supports, and otherwise becomes a lead in the review queue. **10,909
observations are held back** on exactly this basis.

Money edges get a materiality filter: a single ordinary transfer is a
transaction, not a relationship (26k of 28.5k pairs transact exactly once). Two
limbs are required — repeated transfers, **or** one transfer above the 90th
percentile, because dropping the second would delete every layering hop.

### 4. Network analytics — three questions, three rankings

The finding that drove this design:

> Kingpins sit at **median betweenness rank 8** in the intelligence layer, and
> at **rank 123** once calls and money are fused in.

That is not a fusion bug — it is a property of the evidence. Everyone in a cell
phones everyone else, and those lateral calls create shortcuts that route around
the person giving the orders. **Topology alone, on undirected fused evidence,
systematically hides command.**

Command is recoverable because relation *types* carry direction: "reports to",
"handler of", "recruited by" are not symmetric. Collapsing them into undirected
edges throws away the only signal separating a boss from a busy subordinate. So:

| Ranking | Question | Method |
|---|---|---|
| **Command** | who gives orders | authority flow + transitive span over directed chain-of-command relations |
| **Broker** | who connects the groups | cross-community reach, measured on the intel layer |
| **Influence** | overall importance | blended |

Forcing these into one list makes each worse — blending drove broker AP from
0.40 to 0.12, because conduits have no subordinates to score on.

The command analysis distinguishes two shapes automatically:

| | direct reports | span | label |
|---|---|---|---|
| kingpin | 5.9 | **62.7** | APEX / INSULATED CONTROLLER |
| lieutenant | **17.9** | 17.8 | CELL COMMANDER |
| financier, mule | ~0 | 0 | — |

Only genuine chain-of-command relations propagate transitively. "Supplies to" is
leverage, not command — admitting it gave a cell lieutenant 658 subordinates in
an 889-node graph.

**Disruption simulation** answers the question a commander actually asks: not
"who is important" but "if I can arrest ten people, which ten hurt this network
most" — scored against a most-connected baseline.

### 5. Entity resolution — the system never merges
Produces proposals with an evidence breakdown and a confidence band, and stops.
The hard part is not finding similar names; it is **refusing to act on them**.

The corpus deliberately contains **86 pairs of different people with identical
full names**. A name-similarity matcher fires on all 86. At the review band this
system escalates **zero** of them, while recovering 99.1% of true duplicates.

Indian transliteration is handled directly rather than with Soundex, which is
built for English orthography: `Mohammed / Mohammad / Muhammad / Mohd / Md`,
`Choudhary / Chowdhury / Chaudhari`, `Nair / Nayar`, `Gowda / Gouda` all collapse
to one key. Blocking cuts 1.43M comparisons to 2,060 with recall 0.991.

### 6. Suspicious patterns
Seven detectors, each carrying the records that triggered it:

| Pattern | Recall |
|---|---|
| Structuring / smurfing (deposits below reporting threshold) | 1.00 |
| Mule fan-out (hub → many small transfers → cash-out) | 1.00 |
| Round-tripping (funds return to origin) | 1.00 |
| Dormant reactivation / pass-through | 1.00 |
| Pre-incident call burst (spike before an offence, then silence) | 1.00 |
| Layering chains (multi-hop, value decay, time-ordered) | 0.87 |
| Burner SIM rotation | 0.62 |

### 7. Hidden links
Pairs with **no recorded relationship** that the evidence nonetheless ties
together, split into two kinds that are not the same thing:

- **Evidential** — a concrete artefact: one handset carrying both their SIMs, one
  account both operate, one vehicle at both their scenes, co-location.
- **Inferred** — no shared artefact, only structural likelihood (Adamic-Adar).
  Labelled as a hypothesis.

Nothing is written into the graph. An unverified link becomes, three hops later,
someone's justification for a warrant.

### 8. Console
Relationship map (pan / zoom / expand), connection finder, key players,
detected networks, suspicious patterns, hidden links, identity review, decision
log, scorecard. Self-contained — no CDN, works offline.

---

## The safety rule, enforced in code

The problem statement's core requirement — *never automatically connect two
people because their details look similar* — is not a UI convention here:

- Entity resolution emits `auto_merged: False` on every proposal; no code path
  sets it true. Guarded by tests.
- Hidden links ship `status: UNVERIFIED`, `requires_human_verification: True`.
- Anomaly findings carry `requires_human_review: True`.
- Co-location and text-extracted relations cannot assert a relationship alone.
- The only route to "confirmed" is `POST /api/review`, which appends to an audit
  log recording who decided what and when.

Run summary reports `auto_merges_performed: 0`, `auto_confirmed_links: 0`, and
`text_relations_pending_review: 989`.

---

## Layout

```
data_generator/   reference_data.py · generate_dataset.py · validate_dataset.py
data/             nodes · edges · unstructured · ground_truth · graph · derived
sicnd/
  config.py       paths and tuned thresholds
  ingest.py       24 feeds, provenance, join indices
  textsim.py      Indian-name phonetics, Jaro-Winkler, token-set similarity
  nlp.py          gazetteers, cascade extractor, relation extraction, NER eval
  graphbuild.py   5 evidence layers, fusion, heterogeneous graph
  analytics.py    centrality, command hierarchy, communities, paths, disruption
  resolution.py   blocking, scoring, banding — proposals only
  anomaly.py      7 detectors
  linkpred.py     hidden-link discovery
  pipeline.py     orchestration + scorecard
  api.py          FastAPI + audit log
ui/index.html     investigator console
tests/            44 regression tests
```

## API

`/api/summary` · `/api/search` · `/api/person/{id}` · `/api/ego/{id}` ·
`/api/graph` · `/api/keyplayers?ranking=influence|command|broker` ·
`/api/communities` · `/api/disruption` · `/api/anomalies` · `/api/links` ·
`/api/resolution` · `/api/path?a=&b=` · `/api/scorecard` · `/api/review`
(GET log, POST decision)

## Dataset

See **[DATASET.md](DATASET.md)** for the generator, the 15 syndicate archetypes,
the planted structure and the 29 dataset-validation checks.

## Responsible use

This system develops and benchmarks investigative *tooling*. It is not evidence,
it is not derived from real records, and no output says anything about any real
person. Any deployment must keep the rule the design is built around: **surface a
possible link and require human verification — never auto-confirm.**
