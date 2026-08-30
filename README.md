# SICND — Synthetic Indian Criminal Network Dataset

A generated, fully-synthetic dataset for building and **measuring** an AI-powered
criminal-network analysis system: entity extraction, link discovery, community
detection, key-player identification, entity resolution and anomaly detection.

> **Everything here is synthetic.** No real person, gang, phone number, bank
> account, vehicle or case is represented. Names are sampled from
> culturally-authentic Indian name pools; any collision with a real name is
> coincidental and carries no meaning. Geography (states, cities, localities),
> police-station naming conventions and statute sections (IPC / BNS 2023 / NDPS /
> PMLA / Arms Act / UAPA) are real **only** so the data behaves realistically for
> NLP and graph analytics. No Aadhaar-, PAN- or passport-format identifiers are
> generated anywhere.

---

## Why synthetic, and why this is better than a real-name list

Attaching fabricated call records, hawala transfers and gang hierarchies to real
named individuals would be defamatory, would be built largely on hallucinated
"convictions", and — critically — **buys nothing technically**. Graph analytics
does not care whether a node is named `Ramesh Kumar` or a real person; it cares
about topology, timestamps and ground truth.

Real seized data has a fatal weakness for a prototype: **it has no answer key.**
You cannot compute precision or recall against it. This dataset plants its
structure deliberately and then writes down exactly what it planted.

| Ground-truth file | Lets you measure |
|---|---|
| `syndicate_membership.csv` | Community detection (ARI / NMI vs planted syndicates) |
| `key_players.csv` | Key-player ranking (are the kingpins/brokers in your top-k?) |
| `cross_syndicate_bridges.csv` | Broker detection / network-fragmentation analysis |
| `duplicate_pairs.csv` | Entity resolution — with **hard negatives** |
| `anomalies.csv` | Anomaly detection, per pattern type |
| `latent_links.csv` | Hidden-link discovery |
| `ner_annotations.jsonl` | NER (character-level spans) |

---

## Quick start

```bash
cd data_generator
python generate_dataset.py
```

```bash
python validate_dataset.py
```

Regenerate at a different scale (everything is seeded and reproducible):

```bash
python generate_dataset.py --seed 7 --criminals 5000 --cdr 1000000 --incidents 12000
```

Load into NetworkX:

```python
import pandas as pd, networkx as nx
e = pd.read_csv("data/graph/graph_edges.csv")
G = nx.from_pandas_edgelist(e, "src", "dst", ["edge_type", "weight"],
                            create_using=nx.DiGraph)
```

Load into Neo4j: `data/graph/neo4j_load.cypher` (copy the CSVs into your
`import/` folder first; the person-person loader uses APOC).

---

## What is in the box

**Scale:** 1,696 persons · 108 organisations · 2,200 incidents · 200,000 CDR
rows · 60,000 transactions · 3,220 annotated documents · 11,741 graph nodes ·
112,303 graph edges. Timeline spans 2018-01-01 → 2026-06-30.

### 15 syndicates
Modelled on *publicly documented typologies* of Indian organised crime — none
represents a specific real gang.

`SYN-EXT` urban extortion & land · `SYN-HER` Golden Crescent heroin corridor ·
`SYN-CYB` vishing / digital-arrest fraud · `SYN-HAW` hawala & trade-based
laundering · `SYN-MIN` sand & mineral mining · `SYN-TRF` cross-border human
trafficking · `SYN-ARM` illicit arms manufacture · `SYN-VEH` vehicle theft &
chop-shop · `SYN-FIC` fake currency circulation · `SYN-GAN` Eastern Ghats ganja
corridor · `SYN-PON` chit-fund / ponzi · `SYN-BET` betting & match-fixing ·
`SYN-KDN` kidnapping-for-ransom · `SYN-SHK` contract shooter network ·
`SYN-WLD` wildlife & red-sanders trafficking

### Layers
- **Entities** — persons (15 roles from `KINGPIN` to `MULE`), organisations
  (syndicates, front companies, shell entities), locations (real geography with
  coordinates), police stations, phones (SIM), handsets (IMEI), bank accounts,
  vehicles, social handles.
- **Events** — cases, incidents/FIRs (with IPC *and* BNS sections), seizures,
  CDR, financial transactions, co-location observations.
- **Text** — FIR narratives, surveillance reports, intelligence notes, each with
  character-level NER spans.

---

## The design decisions that make it useful

### 1. The kingpin is invisible to degree centrality
Every lieutenant reports to the kingpin, but the kingpin touches **no**
rank-and-file. Lieutenants command crews of 15–40; the boss has 6–12 contacts.
Cross-cell lateral ties are kept deliberately thin so co-ordination has to route
through the leadership.

Measured on the shipped dataset: **100% of kingpins land in the top-10% by
betweenness, versus 76% by degree.** That gap is the teaching point — a naive
"most-connected person" dashboard promotes the lieutenant and misses the boss.

### 2. Hidden links must actually be hidden
211 latent links are planted and **verified not to exist as explicit edges** —
otherwise there is nothing to discover. Four discovery mechanisms:

| Mechanism | How to find it |
|---|---|
| `SHARED_HANDSET_IMEI` | Join `cdr.imei` → phone → subscriber; find IMEIs with >1 subscriber |
| `SHARED_VEHICLE` | 2-hop: person → incident → vehicle → incident → person |
| `CO_LOCATION` | Spatio-temporal join on tower dumps / hotel registers |
| `SHARED_BANK_ACCOUNT` | Fan-in on `person_account`: accounts with >1 controller |

### 3. Entity resolution has hard negatives
110 **true duplicates** (transliteration variants — `Mohammed`/`Mohd.`/`Md.`,
`Choudhary`/`Chowdhury`; dropped surnames; swapped name order), carrying real
merge evidence: shared neighbours in the graph, and in ~45% of cases a phone
number already attributed to the original record.

86 **coincidental collisions**: different people with *identical full names*,
different DOB and district, and unrelated associates. A name-similarity matcher
fires on all 86. **The correct action on every pair is `PROPOSE`, never
auto-merge** — which is exactly the safety rule the problem statement demands.

### 4. Seven anomaly families, individually labelled
`STRUCTURING_SMURFING` (deposits just under ₹50,000 / ₹10,00,000) ·
`LAYERING_CHAIN` (4–7 hops, 5–10% shaved per hop, inside ~30h) ·
`MULE_FANOUT` (hub → 6–20 sub-₹50k transfers, cash-out within 15h) ·
`ROUND_TRIPPING` (funds return to origin, ~3% attrition) ·
`DORMANT_REACTIVATION` · `PRE_INCIDENT_CALL_BURST` (spike in the 48h before an
offence, then silence) · `BURNER_SIM_ROTATION` (SIM discarded, contact set
continues on the same IMEI).

### 5. The CDR is a *lossy* projection of the truth
Communication is driven by the intelligence graph, but burner rotation,
insulation layers and pure-noise calls mean the CDR view does not reproduce it.
Reconciling the two is the analytic problem, not a bug.

---

## Validation

`validate_dataset.py` runs 29 checks — referential integrity, NER span
integrity, topology, community recovery, key-player recovery, latent-link
leakage, anomaly and ER ground truth. All 29 pass on the shipped data:

```
giant component            1,144/1,196 = 95.7%   (20 components)
average degree             4.62  density 0.0039   clustering 0.379
Louvain vs planted         ARI=0.599  NMI=0.777  Q=0.860
kingpins in top-10% betw.  100%   (vs 76% by degree)
brokers in top-10% betw.   86%    of 22 planted
latent links leaked        0/211
NER spans                  29,732 spans, 15 labels, 0 offset errors
```

Note that ARI ≈ 0.6 is *intended*. Louvain finds 30 communities against 15
planted syndicates because it correctly splits the larger ones into their
lieutenant-led cells. A dataset that scored ARI ≈ 0.99 would mean the syndicates
were disconnected islands and community detection was trivial.

`scikit-learn` is optional — without it, community quality falls back to a
purity score.

---

## Layout

```
data_generator/
  reference_data.py     name pools, geography, statutes, syndicate archetypes, templates
  generate_dataset.py   the generator
  validate_dataset.py   29-check quality gate + analytics baseline
data/
  nodes/                persons, organizations, locations, police_stations, phones,
                        devices, bank_accounts, vehicles, digital_identities,
                        cases, incidents, seizures
  edges/                person_person, person_organization, person_phone, phone_device,
                        person_account, person_vehicle, person_location, person_incident,
                        incident_vehicle, colocation_observations, cdr, transactions
  unstructured/         fir_narratives, surveillance_reports, intelligence_notes  (.jsonl)
  ground_truth/         syndicate_membership, key_players, cross_syndicate_bridges,
                        duplicate_pairs, anomalies, latent_links, ner_annotations
  graph/                graph_nodes.csv, graph_edges.csv, neo4j_load.cypher
  dataset_manifest.json counts, seed, syndicate roster, NER label distribution
```

See `DATA_DICTIONARY.md` for column-level documentation.

---

## Responsible use

This dataset exists to develop and benchmark investigative *tooling*. It is not
evidence, it is not derived from real records, and no output of a model trained
on it says anything about any real person. Any system built on it should keep
the rule the data is designed around: **surface a possible link and require
human verification — never auto-confirm.**
