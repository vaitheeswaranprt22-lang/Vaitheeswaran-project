# -*- coding: utf-8 -*-
"""Central configuration: paths and tuned thresholds."""

from __future__ import annotations
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
NODES = os.path.join(DATA, "nodes")
EDGES = os.path.join(DATA, "edges")
TEXT = os.path.join(DATA, "unstructured")
TRUTH = os.path.join(DATA, "ground_truth")
GRAPH = os.path.join(DATA, "graph")
DERIVED = os.path.join(DATA, "derived")
UI = os.path.join(ROOT, "ui")

os.makedirs(DERIVED, exist_ok=True)


# --------------------------------------------------------------------------
# Entity resolution
# --------------------------------------------------------------------------
class ER:
    # Score bands. Nothing above AUTO exists on purpose: this system never
    # merges without a human. The top band is CONFIRM (queue for one-click
    # approval), not MERGE.
    CONFIRM = 0.82          # strong: surface at top of the review queue
    REVIEW = 0.62           # plausible: needs an analyst
    WEAK = 0.45             # below this, do not even show

    # Feature weights (sum ~= 1.0 before evidence bonuses)
    W_NAME = 0.34
    W_PHONETIC = 0.14
    W_DOB = 0.16
    W_GEO = 0.10
    W_ALIAS = 0.08
    W_PHONE = 0.10
    W_NEIGHBOURS = 0.08

    # Hard evidence multipliers
    BONUS_SHARED_PHONE = 0.18
    BONUS_SHARED_NEIGHBOURS = 0.14
    PENALTY_DIFF_DISTRICT = 0.12
    PENALTY_DOB_FAR = 0.20


# --------------------------------------------------------------------------
# Anomaly detection
# --------------------------------------------------------------------------
class Anomaly:
    STRUCTURING_THRESHOLDS = (50_000, 10_00_000)
    STRUCTURING_BAND = 0.12          # within 12% below a threshold
    STRUCTURING_MIN_COUNT = 5
    STRUCTURING_WINDOW_DAYS = 30

    LAYERING_MIN_HOPS = 3
    LAYERING_MAX_HOPS = 8
    LAYERING_MAX_GAP_HOURS = 72
    LAYERING_MIN_RETENTION = 0.80    # each hop keeps >= 80% of the previous

    FANOUT_MIN_TARGETS = 5
    FANOUT_WINDOW_HOURS = 6
    FANOUT_MAX_AMOUNT = 50_000

    ROUNDTRIP_MAX_HOPS = 6
    ROUNDTRIP_TOLERANCE = 0.15       # returns within 15% of the original

    DORMANT_MIN_GAP_DAYS = 150
    DORMANT_MIN_AMOUNT = 10_00_000
    DORMANT_PASSTHROUGH_HOURS = 72

    BURST_WINDOW_HOURS = 48
    BURST_MIN_CALLS = 8
    BURST_RATIO = 3.0                # x the pair's baseline rate

    BURNER_MIN_OVERLAP = 0.34        # contact-set Jaccard across two SIMs
    # Two SIMs whose active periods largely coincide are ordinary dual-SIM
    # usage. Rotation means one goes dark as the other takes over, so the
    # active windows must be mostly disjoint.
    BURNER_MAX_OVERLAP_FRACTION = 0.35


# --------------------------------------------------------------------------
# Key-player scoring
# --------------------------------------------------------------------------
class KeyPlayer:
    W_BETWEENNESS = 0.34
    W_EIGENVECTOR = 0.20
    W_PAGERANK = 0.14
    W_DEGREE = 0.08
    W_KCORE = 0.08
    W_BRIDGE = 0.16          # cross-community reach
    # How much the directed command/authority analysis contributes to the
    # final blended ranking, relative to undirected structural centrality.
    W_COMMAND = 0.40
    # Betweenness is the heaviest term in the score, so it is computed exactly
    # whenever the component is small enough to afford it. Pivot sampling adds
    # rank noise precisely at the top, which is the part that matters.
    BETWEENNESS_EXACT_MAX_NODES = 3000
    BETWEENNESS_SAMPLE = 1200


# --------------------------------------------------------------------------
# NLP
# --------------------------------------------------------------------------
class NLP:
    MIN_PERSON_TOKEN_LEN = 3
    MAX_PERSON_TOKENS = 4
    FUZZY_LINK_THRESHOLD = 0.88   # mention -> known person record


SEED = 42
