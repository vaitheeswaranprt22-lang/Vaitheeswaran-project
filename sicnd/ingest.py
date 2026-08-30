# -*- coding: utf-8 -*-
"""
Multi-source ingestion.

Mirrors the real problem: the data arrives as separate, differently-shaped feeds
(FIR tables, CDR dumps, bank statements, surveillance text) with no common key
beyond identifiers that have to be matched. This layer loads each feed, records
provenance, and builds the indices the rest of the system joins on.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from functools import cached_property

import pandas as pd

from . import config as C

# Feeds declared the way an integration layer would declare them: logical name,
# path, source system, and the entity the rows are about.
FEEDS = {
    # --- nodes -----------------------------------------------------------
    "persons":       (C.NODES, "persons.csv", "CRIMINAL_HISTORY_DB", "Person"),
    "organizations": (C.NODES, "organizations.csv", "CORPORATE_REGISTRY", "Organization"),
    "locations":     (C.NODES, "locations.csv", "GIS_MASTER", "Location"),
    "police_stations": (C.NODES, "police_stations.csv", "CCTNS", "PoliceStation"),
    "phones":        (C.NODES, "phones.csv", "TELECOM_SUBSCRIBER", "Phone"),
    "devices":       (C.NODES, "devices.csv", "TELECOM_EIR", "Device"),
    "accounts":      (C.NODES, "bank_accounts.csv", "BANK_KYC", "BankAccount"),
    "vehicles":      (C.NODES, "vehicles.csv", "VAHAN", "Vehicle"),
    "digital_ids":   (C.NODES, "digital_identities.csv", "SOCIAL_MEDIA_INTEL", "DigitalIdentity"),
    "cases":         (C.NODES, "cases.csv", "CCTNS", "Case"),
    "incidents":     (C.NODES, "incidents.csv", "FIR", "Incident"),
    "seizures":      (C.NODES, "seizures.csv", "SEIZURE_MEMO", "Seizure"),
    # --- edges -----------------------------------------------------------
    "person_person": (C.EDGES, "person_person.csv", "INTELLIGENCE_REPORT", "Relation"),
    "person_org":    (C.EDGES, "person_organization.csv", "CORPORATE_REGISTRY", "Relation"),
    "person_phone":  (C.EDGES, "person_phone.csv", "TELECOM_SUBSCRIBER", "Relation"),
    "phone_device":  (C.EDGES, "phone_device.csv", "TELECOM_EIR", "Relation"),
    "person_account": (C.EDGES, "person_account.csv", "BANK_KYC", "Relation"),
    "person_vehicle": (C.EDGES, "person_vehicle.csv", "VAHAN", "Relation"),
    "person_location": (C.EDGES, "person_location.csv", "SURVEILLANCE_REPORT", "Relation"),
    "person_incident": (C.EDGES, "person_incident.csv", "FIR", "Relation"),
    "incident_vehicle": (C.EDGES, "incident_vehicle.csv", "FIR", "Relation"),
    "colocations":   (C.EDGES, "colocation_observations.csv", "TOWER_DUMP", "Observation"),
    "cdr":           (C.EDGES, "cdr.csv", "CDR", "Communication"),
    "transactions":  (C.EDGES, "transactions.csv", "BANK_STATEMENT", "Transaction"),
}

TEXT_FEEDS = {
    "fir_narratives": "fir_narratives.jsonl",
    "surveillance_reports": "surveillance_reports.jsonl",
    "intelligence_notes": "intelligence_notes.jsonl",
}

TRUTH_FEEDS = {
    "gt_membership": "syndicate_membership.csv",
    "gt_key_players": "key_players.csv",
    "gt_bridges": "cross_syndicate_bridges.csv",
    "gt_duplicates": "duplicate_pairs.csv",
    "gt_anomalies": "anomalies.csv",
    "gt_latent": "latent_links.csv",
}

# Identifier columns must never be coerced to numeric -- leading zeros and exact
# length are meaningful, and a phone number read as int64 silently stops joining
# against the same number read as text elsewhere. Matched as substrings because
# the same identifier appears prefixed (caller_msisdn, src_account_no, ...).
_STR_TOKENS = ("msisdn", "imei", "imsi", "account_no", "account_number", "ifsc",
               "registration_no", "fir_no", "cell_id", "nic_ref", "handle",
               "email", "plate")


def _string_dtypes(path: str) -> dict:
    """Read only the header to decide which columns must load as text."""
    with open(path, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").rstrip("\r").split(",")
    return {c: str for c in header
            if any(tok in c.lower() for tok in _STR_TOKENS)}


class Store:
    """Lazy, cached access to every feed plus the join indices built over them."""

    def __init__(self, data_dir: str | None = None, verbose: bool = True):
        self.data_dir = data_dir or C.DATA
        self.verbose = verbose
        self._cache: dict[str, pd.DataFrame] = {}
        self.provenance: dict[str, dict] = {}

    # ------------------------------------------------------------------
    def _log(self, msg):
        if self.verbose:
            print(f"    {msg}", flush=True)

    def table(self, name: str) -> pd.DataFrame:
        if name in self._cache:
            return self._cache[name]
        if name not in FEEDS:
            raise KeyError(f"unknown feed: {name}")
        base, fname, source, entity = FEEDS[name]
        base = base.replace(C.DATA, self.data_dir)
        path = os.path.join(base, fname)
        if not os.path.exists(path):
            df = pd.DataFrame()
        else:
            df = pd.read_csv(path, dtype=_string_dtypes(path),
                             keep_default_na=False, na_values=[""],
                             low_memory=False)
        self._cache[name] = df
        self.provenance[name] = {"source_system": source, "entity": entity,
                                 "path": path, "rows": len(df)}
        return df

    def __getattr__(self, item):
        if item in FEEDS:
            return self.table(item)
        raise AttributeError(item)

    # ------------------------------------------------------------------
    def documents(self, kind: str | None = None) -> list[dict]:
        """All unstructured documents, optionally one feed."""
        keys = [kind] if kind else list(TEXT_FEEDS)
        out = []
        for k in keys:
            path = os.path.join(self.data_dir, "unstructured", TEXT_FEEDS[k])
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        out.append(json.loads(line))
        return out

    def truth(self, name: str) -> pd.DataFrame:
        path = os.path.join(self.data_dir, "ground_truth", TRUTH_FEEDS[name])
        if not os.path.exists(path):
            return pd.DataFrame()
        return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])

    # ------------------------------------------------------------------
    # Indices
    # ------------------------------------------------------------------
    @cached_property
    def person_by_id(self) -> dict[str, dict]:
        return {r["person_id"]: r for r in
                self.persons.fillna("").to_dict("records")}

    @cached_property
    def criminals(self) -> pd.DataFrame:
        return self.persons[self.persons["person_type"] == "CRIMINAL"]

    @cached_property
    def phone_owner(self) -> dict[str, str]:
        """phone_id -> the person who REGISTERED it (first listed wins)."""
        out = {}
        for r in self.person_phone.itertuples():
            out.setdefault(r.phone_id, r.person_id)
        return out

    @cached_property
    def phones_of(self) -> dict[str, list[str]]:
        out = defaultdict(list)
        for r in self.person_phone.itertuples():
            out[r.person_id].append(r.phone_id)
        return dict(out)

    @cached_property
    def msisdn_of(self) -> dict[str, str]:
        return dict(zip(self.phones["phone_id"], self.phones["msisdn"]))

    @cached_property
    def phone_by_msisdn(self) -> dict[str, str]:
        return dict(zip(self.phones["msisdn"], self.phones["phone_id"]))

    @cached_property
    def accounts_of(self) -> dict[str, list[str]]:
        out = defaultdict(list)
        for r in self.person_account.itertuples():
            out[r.person_id].append(r.account_id)
        return dict(out)

    @cached_property
    def account_holders(self) -> dict[str, list[str]]:
        out = defaultdict(list)
        for r in self.person_account.itertuples():
            out[r.account_id].append(r.person_id)
        return dict(out)

    @cached_property
    def imei_of_phone(self) -> dict[str, str]:
        return dict(zip(self.phone_device["phone_id"], self.phone_device["imei"]))

    @cached_property
    def phones_of_imei(self) -> dict[str, list[str]]:
        out = defaultdict(list)
        for r in self.phone_device.itertuples():
            out[r.imei].append(r.phone_id)
        return dict(out)

    @cached_property
    def accused_of_incident(self) -> dict[str, list[str]]:
        out = defaultdict(list)
        acc = {"ACCUSED", "SUSPECT", "ABSCONDING_ACCUSED"}
        for r in self.person_incident.itertuples():
            if r.role_in_incident in acc:
                out[r.incident_id].append(r.person_id)
        return dict(out)

    @cached_property
    def incidents_of_person(self) -> dict[str, list[str]]:
        out = defaultdict(list)
        for r in self.person_incident.itertuples():
            out[r.person_id].append(r.incident_id)
        return dict(out)

    @cached_property
    def location_by_id(self) -> dict[str, dict]:
        return {r["location_id"]: r for r in
                self.locations.fillna("").to_dict("records")}

    @cached_property
    def incident_by_id(self) -> dict[str, dict]:
        return {r["incident_id"]: r for r in
                self.incidents.fillna("").to_dict("records")}

    @cached_property
    def org_by_id(self) -> dict[str, dict]:
        return {r["org_id"]: r for r in self.organizations.fillna("").to_dict("records")}

    @cached_property
    def neighbours(self) -> dict[str, set]:
        """Undirected person-person adjacency from the declared intel graph."""
        out = defaultdict(set)
        for r in self.person_person.itertuples():
            out[r.src_person_id].add(r.dst_person_id)
            out[r.dst_person_id].add(r.src_person_id)
        return dict(out)

    # ------------------------------------------------------------------
    def load_all(self) -> "Store":
        """Force-load every feed and report a provenance summary."""
        total = 0
        for name in FEEDS:
            df = self.table(name)
            total += len(df)
        self._log(f"loaded {len(FEEDS)} structured feeds, {total:,} rows")
        docs = self.documents()
        self._log(f"loaded {len(docs):,} unstructured documents")
        return self

    def summary(self) -> pd.DataFrame:
        rows = []
        for name, meta in self.provenance.items():
            rows.append({"feed": name, "source_system": meta["source_system"],
                         "entity": meta["entity"], "rows": meta["rows"]})
        return pd.DataFrame(rows).sort_values("rows", ascending=False)


_default: Store | None = None


def get_store(verbose: bool = True) -> Store:
    """Process-wide singleton so the API does not reload 260k rows per request."""
    global _default
    if _default is None:
        _default = Store(verbose=verbose).load_all()
    return _default
