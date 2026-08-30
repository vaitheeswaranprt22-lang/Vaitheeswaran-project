# SICND Dataset — synthetic Indian criminal-network data with ground truth

The data layer underneath [the analysis system](README.md): a generated corpus
for building and **measuring** criminal-network analytics.

> **Everything here is synthetic.** No real person, gang, phone number, bank
> account, vehicle or case is represented. Names are sampled from
> culturally-authentic Indian name pools; any collision with a real name is
> coincidental and carries no meaning. Geography (states, cities, localities),
> police-station naming and statute sections (IPC / BNS 2023 / NDPS / PMLA /
> Arms Act / UAPA) are real **only** so the data behaves realistically for NLP
> and graph analytics. No Aadhaar-, PAN- or passport-format identifiers are
> generated anywhere; a dataset-internal `nic_ref` is the strong identifier.

---

## Why synthetic, and why it beats a real-name list

Attaching fabricated call records, hawala transfers and gang hierarchies to real
named individuals would be defamatory, would rest largely on hallucinated
"convictions", and buys nothing technically — graph analytics does not care
whether a node is named `Ramesh Kumar` or a real person; it cares about topology,
timestamps and ground truth.

Real seized data has one fatal weakness for a prototype: **no answer key.** You
cannot compute precision or recall against it. This dataset plants its structure
deliberately, then writes down exactly what it planted.

| Ground-truth file | Measures |
|---|---|
| `syndicate_membership.csv` | community detection (ARI / NMI) |
| `key_players.csv` | key-player ranking |
| `cross_syndicate_bridges.csv` | broker detection |
| `duplicate_pairs.csv` | entity resolution — **with hard negatives** |
| `anomalies.csv` | anomaly detection, per pattern |
| `latent_links.csv` | hidden-link discovery |
| `ner_annotations.jsonl` | NER (character-level spans) |

---

## Generate

```bash
python data_generator/generate_dataset.py
```

```bash
python data_generator/validate_dataset.py
```

Scale up (seeded and reproducible):

```bash
python data_generator/generate_dataset.py --seed 7 --criminals 5000 --cdr 1000000 --incidents 12000
```

---

## Contents

**56 MB · 36 files.** 1,694 persons · 108 organisations · 2,200 incidents ·
200,000 CDR rows · 60,000 transactions · 3,220 annotated documents. Timeline
2018-01-01 → 2026-06-30.

**15 syndicates**, modelled on publicly documented *typologies* of Indian
organised crime — none represents a specific real gang:

`SYN-EXT` urban extortion & land · `SYN-HER` Golden Crescent heroin corridor ·
`SYN-CYB` vishing / digital-arrest fraud · `SYN-HAW` hawala & trade-based
laundering · `SYN-MIN` sand & mineral mining · `SYN-TRF` cross-border human
trafficking · `SYN-ARM` illicit arms manufacture · `SYN-VEH` vehicle theft &
chop-shop · `SYN-FIC` fake currency circulation · `SYN-GAN` Eastern Ghats ganja
corridor · `SYN-PON` chit-fund / ponzi · `SYN-BET` betting & match-fixing ·
`SYN-KDN` kidnapping-for-ransom · `SYN-SHK` contract shooter network ·
`SYN-WLD` wildlife & red-sanders trafficking

**Layers** — entities (persons in 15 roles, organisations, locations with
coordinates, police stations, SIMs, handsets, accounts, vehicles, social
handles); events (cases, FIRs with IPC *and* BNS sections, seizures, CDR,
transactions, co-location); text (FIR narratives, surveillance reports,
intelligence notes, each with character-level NER spans).

See **[DATA_DICTIONARY.md](DATA_DICTIONARY.md)** for column-level docs.

---

## The design decisions that make it useful

### 1. The kingpin is not the most-connected person
Every lieutenant reports to the kingpin, but the kingpin touches **no**
rank-and-file. Lieutenants command crews of 15–40; the boss has 6–12 contacts.
Cross-cell lateral ties are kept thin so co-ordination must route through the
leadership.

Measured: **100% of kingpins land in the top 10% by betweenness, versus 76% by
degree.** A naive "most-connected person" dashboard promotes the lieutenant and
misses the boss.

### 2. Hidden links must actually be hidden
211 latent links are planted and **verified not to exist as explicit edges**.
Four discovery mechanisms: shared handset IMEI, shared vehicle across incidents
in different states, co-location, shared bank account.

### 3. Entity resolution has hard negatives
110 **true duplicates** (transliteration variants, dropped surnames, swapped name
order) carrying real merge evidence — shared neighbours, and in ~45% of cases a
phone number already attributed to the original.

86 **coincidental collisions**: different people with *identical full names*,
different DOB and district, unrelated associates. A name matcher fires on all 86.
**The correct action on every pair is PROPOSE, never auto-merge.**

### 4. Seven labelled anomaly families
Structuring (below ₹50,000 / ₹10,00,000 thresholds) · layering chains (4–7 hops,
value decay, ~30h) · mule fan-out · round-tripping · dormant reactivation ·
pre-incident call burst · burner SIM rotation.

### 5. The CDR is a lossy projection of the truth
Communication is driven by the intelligence graph, but burner rotation,
insulation layers and noise mean the CDR view does not reproduce it. Reconciling
the two is the analytic problem, not a bug.

### 6. Internal consistency is enforced
Calls only occur on SIMs within their registered service life (**0 of 200,000
violations**); incidents are registered at the station with jurisdiction (**0 of
2,200 mismatches**); openings match offence type; pronouns agree with the named
subject.

---

## Validation

`validate_dataset.py` runs **29 checks** — referential integrity, NER span
integrity, topology, community recovery, key-player recovery, latent-link
leakage, anomaly and ER ground truth. All 29 pass:

```
giant component            1,144/1,196 = 95.7%   (20 components)
average degree             4.62  density 0.0039   clustering 0.379
Louvain vs planted         ARI=0.599  NMI=0.777  Q=0.860
kingpins in top-10% betw.  100%   (vs 76% by degree)
brokers in top-10% betw.   86%    of 22 planted
latent links leaked        0/211
NER spans                  29,732 spans, 15 labels, 0 offset errors
```

ARI ≈ 0.6 here is *intended*: Louvain finds ~30 communities against 15 planted
syndicates because it correctly splits large ones into lieutenant-led cells. A
dataset scoring ARI ≈ 0.99 would mean the syndicates were disconnected islands
and community detection was trivial.

---

## Responsible use

This dataset exists to develop and benchmark investigative tooling. It is not
evidence, not derived from real records, and no model trained on it says anything
about any real person.
