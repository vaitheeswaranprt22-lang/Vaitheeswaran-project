# -*- coding: utf-8 -*-
"""
generate_dataset.py
===================
Synthetic criminal-network dataset generator for graph analytics / AI-assisted
investigation prototypes.

WHAT THIS PRODUCES
------------------
  * ~1,000 synthetic "criminal" person records + ~500 peripheral persons
    (victims, complainants, witnesses, officials) across 15 syndicates.
  * Identifier layers: phones (SIM), handsets (IMEI), bank accounts, vehicles,
    social handles, e-mail.
  * Structured event layers: FIRs/incidents, seizures, CDR, financial
    transactions, co-location observations.
  * Unstructured text layers: FIR narratives, surveillance reports, intel notes
    -- each shipped with character-level NER annotations (ground truth).
  * GROUND TRUTH answer keys: community labels, key players, cross-syndicate
    brokers, duplicate pairs, planted anomalies, latent (derivable) links.

WHY GROUND TRUTH MATTERS
------------------------
Real seized data gives you no answer key. This generator plants the structure it
wants you to find, then writes down what it planted -- so you can compute real
precision/recall for community detection, key-player ranking, entity resolution
and anomaly detection instead of eyeballing a pretty graph.

ETHICS
------
100% synthetic. No real person, gang, phone number, account or vehicle is
represented. Names are sampled from culturally-authentic pools; collisions with
real names are coincidental and carry no meaning. Geography and statute sections
are real only so the data behaves realistically for NLP and analytics.
No national-ID-format numbers (Aadhaar/PAN) are generated; a dataset-internal
`nic_ref` is used instead as the strong identifier for entity-resolution work.

USAGE
-----
    python generate_dataset.py                     # defaults
    python generate_dataset.py --criminals 1000 --seed 42
    python generate_dataset.py --cdr 200000 --txn 60000 --out ../data
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import string
from collections import defaultdict, Counter
from datetime import datetime, timedelta

import reference_data as R

# ---------------------------------------------------------------------------
# Global timeline
# ---------------------------------------------------------------------------
T_START = datetime(2018, 1, 1)
T_END = datetime(2026, 6, 30)
TOTAL_DAYS = (T_END - T_START).days


# ===========================================================================
#  Small helpers
# ===========================================================================

def luhn_check_digit(number_str: str) -> str:
    """Return the Luhn check digit for a numeric string (used for IMEI)."""
    total, parity = 0, len(number_str) % 2
    for i, ch in enumerate(number_str):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def inr(amount: int) -> str:
    """Format an integer as an Indian-grouped amount string: 4523000 -> 45,23,000."""
    s = str(int(amount))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def spans_for(text: str, items):
    """
    Locate each (value, label, entity_id) inside `text` and return character
    spans. Non-overlapping, first free occurrence wins. This is the NER
    ground truth that ships with every narrative.
    """
    used, out = [], []
    for value, label, eid in items:
        if not value:
            continue
        value = str(value)
        start = 0
        while True:
            i = text.find(value, start)
            if i == -1:
                break
            j = i + len(value)
            if not any(i < ue and j > us for us, ue in used):
                used.append((i, j))
                out.append({"start": i, "end": j, "text": value,
                            "label": label, "entity_id": eid})
                break
            start = i + 1
    return sorted(out, key=lambda a: a["start"])


# ===========================================================================
#  Generator
# ===========================================================================

class CrimeNetworkGenerator:

    def __init__(self, seed=42, n_criminals=1000, n_peripheral=500,
                 target_cdr=200_000, target_txn=60_000, n_incidents=2200,
                 out_dir="../data"):
        self.rng = random.Random(seed)
        self.seed = seed
        self.n_criminals = n_criminals
        self.n_peripheral = n_peripheral
        self.target_cdr = target_cdr
        self.target_txn = target_txn
        self.n_incidents = n_incidents
        self.out = os.path.abspath(out_dir)

        # node stores
        self.locations = []
        self.police_stations = []
        self.syndicates = []
        self.orgs = []
        self.persons = []
        self.phones = []
        self.devices = []
        self.accounts = []
        self.vehicles = []
        self.digital_ids = []
        self.cases = []
        self.incidents = []
        self.seizures = []

        # edge stores
        self.pp_edges = []
        self.person_org = []
        self.person_phone = []
        self.phone_device = []
        self.person_account = []
        self.person_vehicle = []
        self.person_location = []
        self.person_incident = []
        self.incident_vehicle = []
        self.colocations = []

        # ground truth
        self.gt_key_players = []
        self.gt_bridges = []
        self.gt_duplicates = []
        self.gt_anomalies = []
        self.gt_latent = []

        # unstructured
        self.narratives = []

        # lookups
        self.by_syndicate = defaultdict(list)
        self.person_by_id = {}
        self.phones_of = defaultdict(list)
        self.accounts_of = defaultdict(list)
        self.comm_pairs = Counter()          # (phone_a, phone_b) -> call count
        self.comm_duration = Counter()
        self.txn_pairs = Counter()           # (acct_a, acct_b) -> total amount

        # uniqueness guards
        self._pp_index = set()
        self._used_msisdn = set()
        self._used_plates = set()
        self._used_accno = set()
        self._used_imei = set()

        self._ctr = defaultdict(int)

    # -- id helper ---------------------------------------------------------
    def nid(self, prefix):
        self._ctr[prefix] += 1
        return f"{prefix}{self._ctr[prefix]:06d}"

    # -- random primitives -------------------------------------------------
    def rdate(self, start=None, end=None):
        start = start or T_START
        end = end or T_END
        delta = (end - start).days
        if delta <= 0:
            return start
        return start + timedelta(days=self.rng.randrange(delta),
                                 hours=self.rng.randrange(24),
                                 minutes=self.rng.randrange(60))

    def weighted_choice(self, mapping):
        keys = list(mapping.keys())
        weights = [mapping[k] for k in keys]
        return self.rng.choices(keys, weights=weights, k=1)[0]

    def msisdn(self):
        while True:
            n = self.rng.choice(R.MOBILE_PREFIXES) + "".join(
                self.rng.choice(string.digits) for _ in range(8))
            if n not in self._used_msisdn:
                self._used_msisdn.add(n)
                return n

    def imei(self):
        while True:
            tac = self.rng.choice(["35", "86", "01", "49", "35"])
            body = tac + "".join(self.rng.choice(string.digits) for _ in range(12))
            v = body + luhn_check_digit(body)
            if v not in self._used_imei:
                self._used_imei.add(v)
                return v

    def account_no(self):
        while True:
            n = "".join(self.rng.choice(string.digits)
                        for _ in range(self.rng.choice([11, 12, 14, 16])))
            if n not in self._used_accno:
                self._used_accno.add(n)
                return n

    def ifsc(self, bank):
        code = "".join(w[0] for w in bank.split()[:4]).upper().ljust(4, "X")[:4]
        return code + "0" + "".join(self.rng.choice(string.digits) for _ in range(6))

    def plate(self, state):
        codes = R.RTO_CODES.get(state, ["DL01"])
        while True:
            p = (self.rng.choice(codes) + " " +
                 "".join(self.rng.choice(string.ascii_uppercase) for _ in range(2)) +
                 " " + "".join(self.rng.choice(string.digits) for _ in range(4)))
            if p not in self._used_plates:
                self._used_plates.add(p)
                return p

    # ===================================================================
    #  1. LOCATIONS + POLICE STATIONS
    # ===================================================================
    def build_locations(self):
        for state, entries in R.GEOGRAPHY.items():
            for city, area, lat, lon in entries:
                loc = {
                    "location_id": self.nid("LOC"),
                    "area": area, "city": city, "state": state, "country": "India",
                    "latitude": round(lat + self.rng.uniform(-0.01, 0.01), 5),
                    "longitude": round(lon + self.rng.uniform(-0.01, 0.01), 5),
                    "place_type": self.rng.choice(R.PLACE_TYPES),
                    "is_border_point": int(state in ("West Bengal", "Punjab", "Assam",
                                                     "Manipur", "Jammu and Kashmir")
                                           and self.rng.random() < 0.35),
                    "is_hotspot": 0,
                }
                self.locations.append(loc)
                ps = {
                    "ps_id": self.nid("PS"),
                    "ps_name": f"{area} Police Station",
                    "short_name": area,
                    "city": city, "state": state,
                    "jurisdiction_location_id": loc["location_id"],
                }
                self.police_stations.append(ps)

        for country, city, lat, lon in R.FOREIGN_HUBS:
            self.locations.append({
                "location_id": self.nid("LOC"),
                "area": f"{city} Hub", "city": city, "state": "-", "country": country,
                "latitude": lat, "longitude": lon,
                "place_type": "Transit Point", "is_border_point": 1, "is_hotspot": 1,
            })

        self.dom_locs = [l for l in self.locations if l["country"] == "India"]
        self.for_locs = [l for l in self.locations if l["country"] != "India"]
        self.locs_by_state = defaultdict(list)
        for l in self.dom_locs:
            self.locs_by_state[l["state"]].append(l)
        self.ps_by_state = defaultdict(list)
        for p in self.police_stations:
            self.ps_by_state[p["state"]].append(p)
        # One station per locality: an incident must be registered at the station
        # that actually has jurisdiction, not just any station in the same state.
        self.ps_by_loc = {p["jurisdiction_location_id"]: p for p in self.police_stations}
        self.loc_by_id = {l["location_id"]: l for l in self.locations}

    # ===================================================================
    #  2. SYNDICATES + PERSON ALLOCATION
    # ===================================================================
    def build_syndicates(self):
        raw = []
        for arch in R.SYNDICATE_ARCHETYPES:
            lo, hi = arch["size"]
            raw.append((arch, (lo + hi) / 2.0))
        total = sum(w for _, w in raw)

        # ~88% of criminals belong to a syndicate; the rest are unaffiliated.
        affiliated = int(self.n_criminals * 0.88)
        allotted = 0
        for idx, (arch, w) in enumerate(raw):
            share = int(round(affiliated * w / total))
            if idx == len(raw) - 1:
                share = affiliated - allotted
            allotted += share
            base_state = self.rng.choice(arch["base_states"])
            hq = self.rng.choice(self.locs_by_state[base_state])
            syn = {
                "org_id": self.nid("ORG"),
                "name": f"{arch['label']} [{hq['city']} cluster]",
                "org_type": "SYNDICATE",
                "syndicate_code": arch["code"],
                "archetype_label": arch["label"],
                "parent_syndicate_id": "",
                "hq_location_id": hq["location_id"],
                "hq_city": hq["city"], "hq_state": base_state,
                "operating_states": "|".join(sorted(set(arch["base_states"] + arch["reach"]))),
                "foreign_links": "|".join(arch["foreign"]),
                "primary_crimes": "|".join(arch["crimes"]),
                "member_count": share,
                "active_since": (T_START - timedelta(days=self.rng.randrange(400, 5200))).date().isoformat(),
                "status": self.rng.choices(["ACTIVE", "DISRUPTED", "DORMANT"],
                                           weights=[0.72, 0.2, 0.08])[0],
                "threat_level": self.rng.choice(["HIGH", "HIGH", "MEDIUM", "CRITICAL"]),
                "_arch": arch,
            }
            self.syndicates.append(syn)
            self.orgs.append({k: v for k, v in syn.items() if not k.startswith("_")})
        self.unaffiliated_count = self.n_criminals - affiliated

    # ===================================================================
    #  3. PERSONS
    # ===================================================================
    def _name(self, region, gender="m"):
        pool = R.NAME_POOLS[region]
        first = self.rng.choice(pool[gender if gender in pool else "m"])
        sur = self.rng.choice(pool["sur"])
        return first, sur

    def _alias(self, first):
        style = self.rng.random()
        tok = self.rng.choice(R.ALIAS_TOKENS)
        if style < 0.45:
            return f"{first.split()[0]} {tok}"
        if style < 0.75:
            return f"{tok} {first.split()[0]}"
        return tok

    def _roles_for(self, n, arch_code):
        """Deal out roles for a syndicate, guaranteeing a leadership spine."""
        roles = []
        n_king = 1 if n < 90 else 2
        roles += ["KINGPIN"] * n_king
        n_lt = max(2, int(n * 0.06))
        roles += ["LIEUTENANT"] * n_lt
        remaining = n - len(roles)
        pool = {k: v["share"] for k, v in R.ROLES.items()
                if k not in ("KINGPIN", "LIEUTENANT")}
        # Bias the role mix by syndicate type
        bias = {
            "SYN-CYB": {"TECH_HANDLER": 3.0, "MULE": 2.4, "RECRUITER": 1.6, "SHOOTER": 0.05},
            "SYN-HAW": {"HAWALA_OPERATOR": 3.5, "FINANCIER": 2.2, "COURIER": 1.5, "SHOOTER": 0.05},
            "SYN-HER": {"COURIER": 2.2, "LOGISTICS": 1.8, "FIXER": 1.4},
            "SYN-SHK": {"SHOOTER": 4.0, "FIXER": 1.5, "MULE": 0.4},
            "SYN-KDN": {"SHOOTER": 2.5, "FIELD_OPERATIVE": 1.5, "MULE": 0.4},
            "SYN-MIN": {"CORRUPT_OFFICIAL": 3.0, "FIELD_OPERATIVE": 1.6, "LOGISTICS": 1.5},
            "SYN-PON": {"RECRUITER": 3.0, "FINANCIER": 2.0, "MULE": 1.6, "SHOOTER": 0.05},
            "SYN-TRF": {"RECRUITER": 3.0, "COURIER": 1.8, "FIXER": 1.4},
            "SYN-VEH": {"FENCE": 3.0, "LOGISTICS": 1.8},
            "SYN-FIC": {"COURIER": 2.5, "FENCE": 2.0},
            "SYN-BET": {"FINANCIER": 2.0, "TECH_HANDLER": 1.8, "FIXER": 1.6, "SHOOTER": 0.1},
            "SYN-WLD": {"LOGISTICS": 2.0, "FIXER": 1.8, "COURIER": 1.6},
            "SYN-ARM": {"LOGISTICS": 2.0, "FENCE": 1.8, "SHOOTER": 1.5},
            "SYN-GAN": {"COURIER": 2.4, "LOGISTICS": 1.8},
            "SYN-EXT": {"FIELD_OPERATIVE": 1.6, "SHOOTER": 1.6, "FIXER": 1.4},
        }.get(arch_code, {})
        for k, m in bias.items():
            if k in pool:
                pool[k] *= m
        keys = list(pool.keys())
        wts = [pool[k] for k in keys]
        roles += self.rng.choices(keys, weights=wts, k=max(0, remaining))
        self.rng.shuffle(roles)
        return roles

    def _make_person(self, region, syn=None, role=None, is_criminal=True):
        gender = "f" if self.rng.random() < (0.09 if is_criminal else 0.42) else "m"
        first, sur = self._name(region, gender)
        full = f"{first} {sur}"

        if syn:
            arch = syn["_arch"]
            state = self.rng.choice(arch["base_states"] + arch["reach"])
        else:
            state = self.rng.choice(list(self.locs_by_state.keys()))
        home = self.rng.choice(self.locs_by_state[state])

        rspec = R.ROLES.get(role, {"risk": (10, 35), "influence": 0.05})
        dob = datetime(self.rng.randrange(1960, 2004), self.rng.randrange(1, 13),
                       self.rng.randrange(1, 28))
        age = int((T_END - dob).days / 365.25)

        # Abroad-based leadership: classic for the top of Indian syndicates.
        abroad = ""
        if role in ("KINGPIN", "FINANCIER", "HAWALA_OPERATOR") and syn \
                and syn["_arch"]["foreign"] and self.rng.random() < 0.45:
            abroad = self.rng.choice(syn["_arch"]["foreign"])

        risk = self.rng.randint(*rspec["risk"]) if is_criminal else self.rng.randint(0, 12)
        p = {
            "person_id": self.nid("P"),
            "full_name": full,
            "first_name": first,
            "surname": sur,
            "alias": self._alias(first) if (is_criminal and self.rng.random() < 0.62) else "",
            "gender": "F" if gender == "f" else "M",
            "date_of_birth": dob.date().isoformat(),
            "age": age,
            "name_region": region,
            "native_state": state,
            "native_city": home["city"],
            "native_area": home["area"],
            "home_location_id": home["location_id"],
            "based_abroad_in": abroad,
            "person_type": "CRIMINAL" if is_criminal else "CIVILIAN",
            "role": role or "",
            "syndicate_id": syn["org_id"] if syn else "",
            "syndicate_code": syn["syndicate_code"] if syn else "",
            "risk_score": risk,
            "influence_score": round(rspec["influence"] * self.rng.uniform(0.82, 1.18), 3)
                               if is_criminal else 0.0,
            "custody_status": "",
            "first_offence_year": "",
            "total_cases": 0,
            "is_cross_syndicate_bridge": 0,
            "nic_ref": "NIC-" + "".join(self.rng.choice(string.ascii_uppercase + string.digits)
                                        for _ in range(9)),
            "record_source": self.rng.choice(R.SOURCE_TYPES),
            "source_reliability": self.rng.choices(R.RELIABILITY_GRADES,
                                                   weights=[.2, .3, .25, .15, .07, .03])[0],
            "info_credibility": self.rng.choices(R.CREDIBILITY_GRADES,
                                                 weights=[.18, .3, .27, .15, .07, .03])[0],
            "is_synthetic": 1,
        }
        if is_criminal:
            p["first_offence_year"] = self.rng.randrange(max(1996, dob.year + 16), 2026)
            if abroad:
                p["custody_status"] = self.rng.choices(
                    ["ABSCONDING", "DECLARED_PO", "EXTRADITION_PENDING"],
                    weights=[.5, .3, .2])[0]
            else:
                p["custody_status"] = self.rng.choices(
                    R.CUSTODY_STATUS, weights=[.28, .17, .21, .12, .06, .12, .02, .02])[0]
        return p

    def build_persons(self):
        for syn in self.syndicates:
            arch = syn["_arch"]
            n = syn["member_count"]
            roles = self._roles_for(n, arch["code"])
            for role in roles:
                region = self.rng.choice(arch["name_regions"])
                p = self._make_person(region, syn, role, True)
                self.persons.append(p)
                self.by_syndicate[syn["org_id"]].append(p)

        # Unaffiliated / lone offenders & small crews
        for _ in range(self.unaffiliated_count):
            region = self.weighted_choice(R.REGION_WEIGHTS)
            role = self.rng.choices(
                ["FIELD_OPERATIVE", "FENCE", "MULE", "COURIER", "FIXER", "SHOOTER"],
                weights=[.34, .16, .2, .14, .1, .06])[0]
            p = self._make_person(region, None, role, True)
            p["syndicate_code"] = "UNAFFILIATED"
            self.persons.append(p)

        # Peripheral civilians
        for _ in range(self.n_peripheral):
            region = self.weighted_choice(R.REGION_WEIGHTS)
            p = self._make_person(region, None, None, False)
            p["person_type"] = self.rng.choices(
                ["COMPLAINANT", "VICTIM", "WITNESS", "PUBLIC_SERVANT", "ASSOCIATE_CIVILIAN"],
                weights=[.3, .22, .24, .12, .12])[0]
            self.persons.append(p)

        self.person_by_id = {p["person_id"]: p for p in self.persons}
        self.criminals = [p for p in self.persons if p["person_type"] == "CRIMINAL"]
        self.civilians = [p for p in self.persons if p["person_type"] != "CRIMINAL"]

    # ===================================================================
    #  4. FRONT COMPANIES
    # ===================================================================
    def build_front_companies(self):
        for syn in self.syndicates:
            arch = syn["_arch"]
            members = self.by_syndicate[syn["org_id"]]
            controllers = [m for m in members
                           if m["role"] in ("FINANCIER", "HAWALA_OPERATOR", "LIEUTENANT",
                                            "FIXER", "KINGPIN")]
            n_front = self.rng.randint(3, 8)
            for _ in range(n_front):
                state = self.rng.choice(arch["base_states"] + arch["reach"])
                loc = self.rng.choice(self.locs_by_state[state])
                owner = self.rng.choice(controllers) if controllers else self.rng.choice(members)
                stem = self.rng.choice([owner["surname"], owner["first_name"].split()[0],
                                        loc["area"].split()[0],
                                        self.rng.choice(["Shree", "Maa", "New", "National",
                                                         "Royal", "Sunrise", "Galaxy",
                                                         "Global", "Unity", "Sagar"])])
                name = f"{stem} {self.rng.choice(arch['front_types'])}"
                org = {
                    "org_id": self.nid("ORG"),
                    "name": name,
                    "org_type": self.rng.choices(["FRONT_COMPANY", "SHELL_ENTITY", "PROPRIETORSHIP"],
                                                 weights=[.5, .3, .2])[0],
                    "syndicate_code": syn["syndicate_code"],
                    "archetype_label": "",
                    "parent_syndicate_id": syn["org_id"],
                    "hq_location_id": loc["location_id"],
                    "hq_city": loc["city"], "hq_state": state,
                    "operating_states": state,
                    "foreign_links": "|".join(arch["foreign"]) if self.rng.random() < .3 else "",
                    "primary_crimes": "MONEY_LAUNDERING",
                    "member_count": self.rng.randint(1, 4),
                    "active_since": self.rdate(T_START - timedelta(days=2500), T_END).date().isoformat(),
                    "status": self.rng.choices(["ACTIVE", "STRUCK_OFF", "DORMANT"],
                                               weights=[.6, .18, .22])[0],
                    "threat_level": "MEDIUM",
                }
                self.orgs.append(org)
                self.person_org.append({
                    "person_id": owner["person_id"], "org_id": org["org_id"],
                    "role_in_org": self.rng.choice(["Director", "Proprietor", "Beneficial Owner",
                                                    "Authorised Signatory"]),
                    "from_date": org["active_since"], "to_date": "",
                    "is_benami": int(self.rng.random() < 0.42),
                })
                for m in self.rng.sample(members, min(len(members), self.rng.randint(0, 2))):
                    self.person_org.append({
                        "person_id": m["person_id"], "org_id": org["org_id"],
                        "role_in_org": self.rng.choice(["Director", "Employee", "Nominee Director"]),
                        "from_date": org["active_since"], "to_date": "",
                        "is_benami": int(self.rng.random() < 0.5),
                    })

        # membership edges for the syndicates themselves
        for syn in self.syndicates:
            for m in self.by_syndicate[syn["org_id"]]:
                self.person_org.append({
                    "person_id": m["person_id"], "org_id": syn["org_id"],
                    "role_in_org": m["role"], "from_date": "", "to_date": "", "is_benami": 0,
                })

    # ===================================================================
    #  5. IDENTIFIERS: phones, handsets, accounts, vehicles, handles
    # ===================================================================
    def build_identifiers(self):
        for p in self.persons:
            crim = p["person_type"] == "CRIMINAL"
            role = p["role"]

            # ---- phones ----
            if crim:
                base = {"KINGPIN": 4, "LIEUTENANT": 3, "SHOOTER": 3,
                        "HAWALA_OPERATOR": 3, "TECH_HANDLER": 4}.get(role, 2)
                n_ph = max(1, self.rng.randint(base - 1, base + 2))
            else:
                n_ph = 1
            for k in range(n_ph):
                burner = crim and (k > 0) and self.rng.random() < 0.55
                act = self.rdate()
                deact = ""
                if burner and self.rng.random() < 0.6:
                    deact = (act + timedelta(days=self.rng.randint(15, 400))).date().isoformat()
                ph = {
                    "phone_id": self.nid("PH"),
                    "msisdn": self.msisdn(),
                    "operator": self.rng.choice(R.TELECOM_OPERATORS),
                    "circle": p["native_state"],
                    "subscriber_person_id": p["person_id"],
                    "subscriber_name_on_record": (
                        p["full_name"] if not burner else
                        self.rng.choice([
                            f"{self.rng.choice(R.NAME_POOLS[p['name_region']]['m'])} "
                            f"{self.rng.choice(R.NAME_POOLS[p['name_region']]['sur'])}",
                            "NOT AVAILABLE", "ADDRESS INCOMPLETE"])),
                    "kyc_status": "VERIFIED" if not burner else
                                  self.rng.choice(["FORGED_KYC", "UNVERIFIED", "BULK_ISSUED"]),
                    "activation_date": act.date().isoformat(),
                    "deactivation_date": deact,
                    "is_burner": int(burner),
                    "imsi": "4040" + "".join(self.rng.choice(string.digits) for _ in range(11)),
                }
                self.phones.append(ph)
                self.phones_of[p["person_id"]].append(ph)
                self.person_phone.append({
                    "person_id": p["person_id"], "phone_id": ph["phone_id"],
                    "usage_type": "REGISTERED" if not burner else "USED_NOT_REGISTERED",
                    "from_date": ph["activation_date"], "to_date": deact,
                    "confidence": round(self.rng.uniform(0.72, 0.99), 2),
                })

            # ---- bank accounts ----
            if crim:
                n_ac = {"FINANCIER": 4, "HAWALA_OPERATOR": 4, "KINGPIN": 3,
                        "MULE": 2, "TECH_HANDLER": 2}.get(role, 1)
                n_ac = max(1, self.rng.randint(n_ac - 1, n_ac + 1))
            else:
                n_ac = 1 if self.rng.random() < 0.75 else 0
            for _ in range(n_ac):
                bank = self.rng.choice(R.BANKS)
                opened = self.rdate(T_START - timedelta(days=1800), T_END)
                is_mule = int(crim and role == "MULE" and self.rng.random() < 0.85)
                ac = {
                    "account_id": self.nid("AC"),
                    "account_number": self.account_no(),
                    "ifsc": self.ifsc(bank),
                    "bank": bank,
                    "branch_city": p["native_city"],
                    "branch_state": p["native_state"],
                    "holder_person_id": p["person_id"],
                    "holder_org_id": "",
                    "holder_name": p["full_name"],
                    "account_type": self.rng.choices(
                        ["SAVINGS", "CURRENT", "OVERDRAFT", "WALLET"],
                        weights=[.62, .24, .06, .08])[0],
                    "opened_date": opened.date().isoformat(),
                    "status": self.rng.choices(["ACTIVE", "FROZEN", "DORMANT", "CLOSED"],
                                               weights=[.74, .1, .12, .04])[0],
                    "is_mule_account": is_mule,
                    "kyc_risk_rating": self.rng.choices(["LOW", "MEDIUM", "HIGH"],
                                                        weights=[.5, .33, .17])[0],
                }
                self.accounts.append(ac)
                self.accounts_of[p["person_id"]].append(ac)
                self.person_account.append({
                    "person_id": p["person_id"], "account_id": ac["account_id"],
                    "relation": "HOLDER", "from_date": ac["opened_date"], "to_date": "",
                })

            # ---- vehicles ----
            if crim and self.rng.random() < 0.34:
                make, models = self.rng.choice(R.VEHICLE_MAKES)
                state = p["native_state"]
                v = {
                    "vehicle_id": self.nid("VEH"),
                    "registration_no": self.plate(state),
                    "make": make, "model": self.rng.choice(models),
                    "colour": self.rng.choice(["White", "Silver", "Black", "Grey", "Red",
                                               "Blue", "Maroon"]),
                    "vehicle_class": "TWO_WHEELER" if make in ("Royal Enfield", "Bajaj", "Hero")
                                     else ("COMMERCIAL" if make in ("Ashok Leyland", "Eicher")
                                           else "LMV"),
                    "registered_state": state,
                    "owner_person_id": p["person_id"],
                    "owner_name_on_record": p["full_name"] if self.rng.random() < .7 else "THIRD PARTY",
                    "registration_date": self.rdate(T_START - timedelta(days=2000), T_END).date().isoformat(),
                    "is_fake_plate": int(self.rng.random() < 0.11),
                    "chassis_tampered": int(self.rng.random() < 0.08),
                }
                self.vehicles.append(v)
                self.person_vehicle.append({
                    "person_id": p["person_id"], "vehicle_id": v["vehicle_id"],
                    "relation": "REGISTERED_OWNER", "from_date": v["registration_date"],
                    "to_date": "", "confidence": 0.95,
                })

            # ---- digital identity ----
            if self.rng.random() < (0.55 if crim else 0.3):
                plat = self.rng.choice(["WhatsApp", "Telegram", "Instagram", "Facebook",
                                        "Signal", "X", "Snapchat"])
                handle = (p["first_name"].split()[0].lower() +
                          self.rng.choice(["_", ".", ""]) +
                          self.rng.choice([p["surname"].lower(),
                                           str(self.rng.randrange(11, 9999)),
                                           (p["alias"].split()[0].lower() if p["alias"] else "x")]))
                self.digital_ids.append({
                    "digital_id": self.nid("DIG"),
                    "person_id": p["person_id"],
                    "platform": plat,
                    "handle": "@" + handle,
                    "email": handle + self.rng.choice(["@gmail.com", "@yahoo.in",
                                                       "@outlook.com", "@protonmail.com"]),
                    "first_seen": self.rdate().date().isoformat(),
                    "is_anonymous_profile": int(self.rng.random() < 0.3),
                })

            # ---- handsets (IMEI) ----
            my_phones = self.phones_of[p["person_id"]]
            if my_phones:
                n_dev = 1 if len(my_phones) <= 2 else self.rng.randint(1, 2)
                devs = []
                for _ in range(n_dev):
                    d = {
                        "device_id": self.nid("DEV"),
                        "imei": self.imei(),
                        "make": self.rng.choice(["Samsung", "Xiaomi", "Realme", "Vivo", "Oppo",
                                                 "Apple", "OnePlus", "Nokia", "Lava", "Tecno"]),
                        "model": "M" + str(self.rng.randrange(10, 99)),
                        "is_dual_sim": int(self.rng.random() < 0.7),
                        "first_seen": self.rdate().date().isoformat(),
                    }
                    self.devices.append(d)
                    devs.append(d)
                for ph in my_phones:
                    d = self.rng.choice(devs)
                    self.phone_device.append({
                        "phone_id": ph["phone_id"], "device_id": d["device_id"],
                        "imei": d["imei"], "msisdn": ph["msisdn"],
                        "first_seen": ph["activation_date"],
                        "last_seen": ph["deactivation_date"] or T_END.date().isoformat(),
                    })

        self.phone_by_id = {p["phone_id"]: p for p in self.phones}
        self.account_by_id = {a["account_id"]: a for a in self.accounts}

    # ===================================================================
    #  6. PERSON-PERSON GRAPH  (the spine of the whole dataset)
    # ===================================================================
    def _add_pp(self, a, b, relation, subtype="", strength=None, source=None,
                verified=None, confidence=None):
        if a["person_id"] == b["person_id"]:
            return
        self._pp_index.add((a["person_id"], b["person_id"]))
        self._pp_index.add((b["person_id"], a["person_id"]))
        self.pp_edges.append({
            "edge_id": self.nid("E"),
            "src_person_id": a["person_id"],
            "src_name": a["full_name"],
            "dst_person_id": b["person_id"],
            "dst_name": b["full_name"],
            "relation": relation,
            "subtype": subtype,
            "since": self.rdate().date().isoformat(),
            "strength": strength if strength is not None else round(self.rng.uniform(0.2, 1.0), 2),
            "confidence": confidence if confidence is not None else round(self.rng.uniform(0.45, 0.99), 2),
            "source_type": source or self.rng.choice(R.SOURCE_TYPES),
            "is_verified": verified if verified is not None else int(self.rng.random() < 0.55),
        })

    def build_person_person(self):
        for syn in self.syndicates:
            members = self.by_syndicate[syn["org_id"]]
            kings = [m for m in members if m["role"] == "KINGPIN"]
            lts = [m for m in members if m["role"] == "LIEUTENANT"]
            fins = [m for m in members if m["role"] in ("FINANCIER", "HAWALA_OPERATOR")]
            handlers = [m for m in members if m["role"] == "TECH_HANDLER"]
            rank_and_file = [m for m in members
                             if m["role"] not in ("KINGPIN", "LIEUTENANT")]

            # -- leadership spine ------------------------------------------
            # The kingpin is the ONLY top-level connector between cells: every
            # lieutenant reports to him, but he touches no rank-and-file. That
            # keeps his DEGREE low (lieutenants command far bigger crews) while
            # making his BETWEENNESS high -- the property that makes "degree
            # centrality misses the boss" demonstrable on this data.
            for k in kings:
                for lt in lts:
                    self._add_pp(lt, k, "REPORTS_TO", strength=round(self.rng.uniform(.75, 1.0), 2),
                                 source="INTELLIGENCE_REPORT", verified=1, confidence=0.9)
                for f in self.rng.sample(fins, min(len(fins), 2)) if fins else []:
                    self._add_pp(f, k, "FINANCES",
                                 strength=round(self.rng.uniform(.7, 1.0), 2),
                                 source="BANK_STATEMENT", verified=1, confidence=0.86)
                if handlers and self.rng.random() < 0.6:
                    self._add_pp(k, self.rng.choice(handlers), "HANDLER_OF",
                                 source="INTELLIGENCE_REPORT", verified=0, confidence=0.6)

            # -- cells: each lieutenant owns a crew -------------------------
            if lts:
                self.rng.shuffle(rank_and_file)
                cells = defaultdict(list)
                for i, m in enumerate(rank_and_file):
                    cells[lts[i % len(lts)]["person_id"]].append(m)
                lt_by_id = {l["person_id"]: l for l in lts}
                for lt_id, crew in cells.items():
                    lt = lt_by_id[lt_id]
                    for m in crew:
                        self._add_pp(m, lt, "REPORTS_TO",
                                     strength=round(self.rng.uniform(.5, .9), 2))
                        if self.rng.random() < 0.22:
                            self._add_pp(lt, m, "RECRUITED_BY" if self.rng.random() < .5
                                         else "HANDLER_OF")
                    # dense lateral ties inside the cell
                    for i in range(len(crew)):
                        for j in range(i + 1, len(crew)):
                            if self.rng.random() < 0.16:
                                self._add_pp(crew[i], crew[j], "ASSOCIATE_OF",
                                             strength=round(self.rng.uniform(.3, .8), 2))
                # Sparse ties across cells. Kept deliberately thin: every extra
                # lateral shortcut routes around the leadership and erodes the
                # hierarchy the analytics are supposed to recover.
                for _ in range(int(len(members) * 0.10)):
                    a, b = self.rng.sample(rank_and_file, 2) if len(rank_and_file) > 1 \
                        else (None, None)
                    if a is None:
                        break
                    self._add_pp(a, b, self.rng.choices(
                        ["ASSOCIATE_OF", "CO_ACCUSED_WITH", "SHARES_HIDEOUT_WITH",
                         "CELLMATE_OF", "SUPPLIES_TO"],
                        weights=[.45, .22, .13, .1, .1])[0])
                # lieutenants know each other, but sparsely -- co-ordination is
                # supposed to go up through the kingpin, not sideways
                for i in range(len(lts)):
                    for j in range(i + 1, len(lts)):
                        if self.rng.random() < 0.18:
                            self._add_pp(lts[i], lts[j], "ASSOCIATE_OF", strength=0.7)

            # -- family ties (very common in Indian syndicates) -------------
            for _ in range(max(1, int(len(members) * 0.08))):
                a, b = self.rng.sample(members, 2)
                if a["surname"] == b["surname"] or self.rng.random() < 0.4:
                    self._add_pp(a, b, "FAMILY_OF", subtype=self.rng.choice(R.FAMILY_SUBTYPES),
                                 strength=0.9, verified=1, confidence=0.95,
                                 source="CRIMINAL_HISTORY_DB")

        # -- leadership summits: kingpin-to-kingpin alliances ---------------
        # Puts the bosses on the only paths between whole syndicates, which is
        # what makes them the top-ranked nodes under betweenness.
        kp_by_syn = {s["org_id"]: [m for m in self.by_syndicate[s["org_id"]]
                                   if m["role"] == "KINGPIN"] for s in self.syndicates}
        syn_ids = [s["org_id"] for s in self.syndicates]
        self.rng.shuffle(syn_ids)
        for i in range(len(syn_ids)):
            partner = syn_ids[(i + 1) % len(syn_ids)]
            a_pool, b_pool = kp_by_syn[syn_ids[i]], kp_by_syn[partner]
            if not a_pool or not b_pool:
                continue
            self._add_pp(self.rng.choice(a_pool), self.rng.choice(b_pool),
                         "ASSOCIATE_OF", subtype="Inter-syndicate accommodation",
                         strength=round(self.rng.uniform(.55, .9), 2),
                         source="INTELLIGENCE_REPORT", verified=0,
                         confidence=round(self.rng.uniform(.45, .7), 2))
        for _ in range(8):
            s1, s2 = self.rng.sample(syn_ids, 2)
            if kp_by_syn[s1] and kp_by_syn[s2]:
                self._add_pp(self.rng.choice(kp_by_syn[s1]), self.rng.choice(kp_by_syn[s2]),
                             "ASSOCIATE_OF", subtype="Inter-syndicate accommodation",
                             strength=round(self.rng.uniform(.5, .85), 2),
                             source="INTELLIGENCE_REPORT", verified=0, confidence=0.55)

        # -- rivalries between syndicates ---------------------------------
        for _ in range(24):
            s1, s2 = self.rng.sample(self.syndicates, 2)
            m1 = self.rng.choice(self.by_syndicate[s1["org_id"]])
            m2 = self.rng.choice(self.by_syndicate[s2["org_id"]])
            self._add_pp(m1, m2, "RIVAL_OF", strength=round(self.rng.uniform(.5, 1.0), 2),
                         source="INTELLIGENCE_REPORT")

        # -- unaffiliated offenders form loose crews ----------------------
        una = [p for p in self.criminals if p["syndicate_code"] == "UNAFFILIATED"]
        self.rng.shuffle(una)
        for i in range(0, len(una) - 3, 4):
            crew = una[i:i + 4]
            for a in range(len(crew)):
                for b in range(a + 1, len(crew)):
                    if self.rng.random() < 0.6:
                        self._add_pp(crew[a], crew[b], "CO_ACCUSED_WITH")
            if self.rng.random() < 0.4:
                syn = self.rng.choice(self.syndicates)
                anchor = self.rng.choice([m for m in self.by_syndicate[syn["org_id"]]
                                          if m["role"] in ("FENCE", "FIXER", "LOGISTICS",
                                                           "LIEUTENANT")] or
                                         self.by_syndicate[syn["org_id"]])
                self._add_pp(crew[0], anchor, "SUPPLIES_TO", confidence=0.5, verified=0)

    # ===================================================================
    #  7. CROSS-SYNDICATE BRIDGES  (the "hidden link" payload)
    # ===================================================================
    def build_bridges(self, n_bridges=22):
        candidates = [p for p in self.criminals
                      if p["role"] in ("FINANCIER", "HAWALA_OPERATOR", "FIXER", "FENCE",
                                       "CORRUPT_OFFICIAL", "LOGISTICS", "TECH_HANDLER")
                      and p["syndicate_id"]]
        self.rng.shuffle(candidates)
        chosen = candidates[:n_bridges]
        for b in chosen:
            own = b["syndicate_id"]
            others = [s for s in self.syndicates if s["org_id"] != own]
            targets = self.rng.sample(others, self.rng.randint(1, 3))
            linked = []
            for t in targets:
                pool = [m for m in self.by_syndicate[t["org_id"]]
                        if m["role"] in ("LIEUTENANT", "FINANCIER", "HAWALA_OPERATOR",
                                         "LOGISTICS", "FIXER", "KINGPIN")]
                pool = pool or self.by_syndicate[t["org_id"]]
                for peer in self.rng.sample(pool, min(len(pool), self.rng.randint(1, 3))):
                    rel = self.rng.choice(["ASSOCIATE_OF", "FINANCES", "SUPPLIES_TO"])
                    self._add_pp(b, peer, rel,
                                 strength=round(self.rng.uniform(.45, .85), 2),
                                 source=self.rng.choice(["INTELLIGENCE_REPORT",
                                                         "BANK_STATEMENT", "CDR"]),
                                 verified=int(self.rng.random() < 0.4),
                                 confidence=round(self.rng.uniform(.5, .85), 2))
                linked.append(t["syndicate_code"])
            b["is_cross_syndicate_bridge"] = 1
            b["influence_score"] = round(min(1.0, b["influence_score"] + 0.22), 3)
            self.gt_bridges.append({
                "person_id": b["person_id"], "name": b["full_name"],
                "alias": b["alias"], "role": b["role"],
                "home_syndicate": b["syndicate_code"],
                "bridged_syndicates": "|".join(sorted(set(linked))),
                "bridge_type": "FINANCIAL_CONDUIT" if b["role"] in
                               ("FINANCIER", "HAWALA_OPERATOR") else "OPERATIONAL_CONDUIT",
                "why_it_matters": "High betweenness centrality; removal fragments "
                                  "the inter-syndicate component.",
            })

    # ===================================================================
    #  8. KEY-PLAYER GROUND TRUTH
    # ===================================================================
    def build_key_players(self):
        for syn in self.syndicates:
            members = self.by_syndicate[syn["org_id"]]
            for m in members:
                if m["role"] == "KINGPIN":
                    self.gt_key_players.append({
                        "person_id": m["person_id"], "name": m["full_name"],
                        "alias": m["alias"], "syndicate_code": syn["syndicate_code"],
                        "key_player_type": "KINGPIN",
                        "expected_signal": "LOW degree centrality, HIGH betweenness / "
                                           "eigenvector via lieutenants",
                        "influence_score": m["influence_score"],
                    })
                elif m["role"] == "LIEUTENANT":
                    self.gt_key_players.append({
                        "person_id": m["person_id"], "name": m["full_name"],
                        "alias": m["alias"], "syndicate_code": syn["syndicate_code"],
                        "key_player_type": "LIEUTENANT",
                        "expected_signal": "HIGH degree centrality within community",
                        "influence_score": m["influence_score"],
                    })
        for b in self.gt_bridges:
            self.gt_key_players.append({
                "person_id": b["person_id"], "name": b["name"], "alias": b["alias"],
                "syndicate_code": b["home_syndicate"],
                "key_player_type": "BROKER",
                "expected_signal": "HIGH betweenness across communities; low within-"
                                   "community degree",
                "influence_score": self.person_by_id[b["person_id"]]["influence_score"],
            })

    # ===================================================================
    #  9. CASES + INCIDENTS + SEIZURES
    # ===================================================================
    def build_incidents(self):
        # Cases group incidents; most cases belong to a syndicate.
        n_cases = max(60, self.n_incidents // 14)
        for _ in range(n_cases):
            syn = self.rng.choice(self.syndicates) if self.rng.random() < 0.8 else None
            crime = self.rng.choice(syn["_arch"]["crimes"]) if syn else \
                self.rng.choice(list(R.CRIME_TYPES.keys()))
            opened = self.rdate()
            self.cases.append({
                "case_id": self.nid("CASE"),
                "case_title": f"Operation {self.rng.choice(['Nirbhik','Chakravyuh','Prahar','Sankalp','Trishul','Vajra','Netra','Ankush','Dhruv','Samadhan','Kavach','Pralay','Aakhet','Sudarshan'])}-{self.rng.randrange(10,99)}",
                "primary_crime": crime,
                "lead_agency": self.rng.choice(R.AGENCIES),
                "syndicate_id": syn["org_id"] if syn else "",
                "syndicate_code": syn["syndicate_code"] if syn else "UNAFFILIATED",
                "opened_date": opened.date().isoformat(),
                "status": self.rng.choices(["UNDER_INVESTIGATION", "CHARGESHEETED",
                                            "TRIAL", "CLOSED"], weights=[.42, .27, .21, .1])[0],
                "priority": self.rng.choices(["HIGH", "MEDIUM", "LOW"], weights=[.3, .5, .2])[0],
            })

        for _ in range(self.n_incidents):
            case = self.rng.choice(self.cases)
            syn = next((s for s in self.syndicates if s["org_id"] == case["syndicate_id"]), None)

            if syn:
                crime = self.rng.choice(syn["_arch"]["crimes"])
                state = self.rng.choice(syn["_arch"]["base_states"] + syn["_arch"]["reach"])
                pool = self.by_syndicate[syn["org_id"]]
            else:
                crime = case["primary_crime"]
                state = self.rng.choice(list(self.locs_by_state.keys()))
                pool = [p for p in self.criminals if p["syndicate_code"] == "UNAFFILIATED"]
                pool = pool or self.criminals

            loc = self.rng.choice(self.locs_by_state[state])
            ps = self.ps_by_loc.get(loc["location_id"]) or self.rng.choice(self.ps_by_state[state])
            when = self.rdate(datetime.fromisoformat(case["opened_date"]), T_END)
            meta = R.CRIME_TYPES[crime]

            inc = {
                "incident_id": self.nid("INC"),
                "fir_no": f"{self.rng.randrange(1, 900):03d}/{when.year}",
                "case_id": case["case_id"],
                "crime_type": crime,
                "ipc_section": meta["ipc"],
                "bns_section": meta["bns"],
                "severity": meta["severity"],
                "bailable": int(meta["bailable"]),
                "ps_id": ps["ps_id"], "ps_name": ps["ps_name"],
                "location_id": loc["location_id"],
                "area": loc["area"], "city": loc["city"], "state": state,
                "latitude": loc["latitude"], "longitude": loc["longitude"],
                "incident_datetime": when.isoformat(timespec="minutes"),
                "reported_datetime": (when + timedelta(hours=self.rng.randint(1, 72))).isoformat(timespec="minutes"),
                "investigating_agency": case["lead_agency"],
                "syndicate_id": syn["org_id"] if syn else "",
                "syndicate_code": case["syndicate_code"],
                "status": self.rng.choices(["UNDER_INVESTIGATION", "CHARGESHEETED",
                                            "CONVICTED", "ACQUITTED", "UNTRACED"],
                                           weights=[.4, .28, .13, .07, .12])[0],
                "loss_or_value_inr": 0,
                "n_accused": 0,
                "source_reliability": self.rng.choice(R.RELIABILITY_GRADES[:4]),
            }

            # value involved
            if crime in ("MONEY_LAUNDERING", "CHIT_FUND_PONZI", "CYBER_FRAUD",
                         "CHEATING_FRAUD", "SMUGGLING_CUSTOMS", "BETTING_GAMBLING"):
                inc["loss_or_value_inr"] = self.rng.choice(
                    [self.rng.randrange(50_000, 20_00_000),
                     self.rng.randrange(20_00_000, 5_00_00_000),
                     self.rng.randrange(5_00_00_000, 300_00_00_000)])
            elif crime in ("EXTORTION", "KIDNAP_FOR_RANSOM", "ROBBERY", "DACOITY"):
                inc["loss_or_value_inr"] = self.rng.randrange(1_00_000, 5_00_00_000)
            elif crime in ("NDPS_TRAFFICKING", "FICN_COUNTERFEIT", "WILDLIFE_TRAFFICKING"):
                inc["loss_or_value_inr"] = self.rng.randrange(5_00_000, 80_00_00_000)

            # accused set -- drawn from ONE cell so co-accused cliques are real
            n_acc = self.rng.choices([1, 2, 3, 4, 5, 7], weights=[.2, .28, .22, .15, .1, .05])[0]
            n_acc = min(n_acc, len(pool))
            accused = self.rng.sample(pool, n_acc)
            inc["n_accused"] = n_acc
            self.incidents.append(inc)

            for a in accused:
                arrested = self.rng.random() < 0.6
                self.person_incident.append({
                    "incident_id": inc["incident_id"], "person_id": a["person_id"],
                    "person_name": a["full_name"],
                    "role_in_incident": self.rng.choices(
                        ["ACCUSED", "SUSPECT", "ABSCONDING_ACCUSED"],
                        weights=[.66, .22, .12])[0],
                    "arrested": int(arrested),
                    "chargesheeted": int(arrested and self.rng.random() < 0.72),
                    "arrest_date": (when + timedelta(days=self.rng.randint(0, 200))).date().isoformat()
                                   if arrested else "",
                })
                a["total_cases"] += 1
                self.person_location.append({
                    "person_id": a["person_id"], "location_id": loc["location_id"],
                    "association": "PRESENT_AT_INCIDENT",
                    "observed_on": when.date().isoformat(),
                    "source_type": "FIR", "confidence": round(self.rng.uniform(.6, .98), 2),
                })

            # victims / complainants / witnesses
            for role_ in ("COMPLAINANT", "VICTIM", "WITNESS"):
                if role_ == "WITNESS" and self.rng.random() > 0.5:
                    continue
                if role_ == "VICTIM" and crime in ("ILLEGAL_MINING", "BETTING_GAMBLING",
                                                   "NDPS_POSSESSION"):
                    continue
                civ = self.rng.choice(self.civilians)
                self.person_incident.append({
                    "incident_id": inc["incident_id"], "person_id": civ["person_id"],
                    "person_name": civ["full_name"], "role_in_incident": role_,
                    "arrested": 0, "chargesheeted": 0, "arrest_date": "",
                })

            # vehicle involvement
            if self.rng.random() < 0.3 and self.vehicles:
                owner_ids = {a["person_id"] for a in accused}
                cand = [v for v in self.vehicles if v["owner_person_id"] in owner_ids]
                v = self.rng.choice(cand) if cand else self.rng.choice(self.vehicles)
                self.incident_vehicle.append({
                    "incident_id": inc["incident_id"], "vehicle_id": v["vehicle_id"],
                    "registration_no": v["registration_no"],
                    "involvement": self.rng.choice(["USED_IN_OFFENCE", "SEIZED",
                                                    "SEEN_AT_SCENE", "TRANSPORT"]),
                })

            # seizures
            if crime in R.CONTRABAND and self.rng.random() < 0.75:
                item = self.rng.choice(R.CONTRABAND[crime])
                qty, unit = self._quantity(crime)
                self.seizures.append({
                    "seizure_id": self.nid("SZ"), "incident_id": inc["incident_id"],
                    "item_category": "CONTRABAND", "item": item,
                    "quantity": qty, "unit": unit,
                    "estimated_value_inr": inc["loss_or_value_inr"] or self.rng.randrange(50_000, 2_00_00_000),
                    "seized_from_person_id": accused[0]["person_id"],
                })
            if crime in ("MURDER", "ATTEMPT_TO_MURDER", "ARMS_ACT", "KIDNAP_FOR_RANSOM",
                         "DACOITY") and self.rng.random() < 0.6:
                self.seizures.append({
                    "seizure_id": self.nid("SZ"), "incident_id": inc["incident_id"],
                    "item_category": "WEAPON", "item": self.rng.choice(R.WEAPON_TYPES),
                    "quantity": self.rng.randint(1, 6), "unit": "nos",
                    "estimated_value_inr": self.rng.randrange(5_000, 3_00_000),
                    "seized_from_person_id": accused[0]["person_id"],
                })
            if self.rng.random() < 0.18:
                self.seizures.append({
                    "seizure_id": self.nid("SZ"), "incident_id": inc["incident_id"],
                    "item_category": "CASH", "item": "Indian currency",
                    "quantity": self.rng.randrange(50_000, 2_00_00_000), "unit": "INR",
                    "estimated_value_inr": 0,
                    "seized_from_person_id": accused[0]["person_id"],
                })

        self.incident_by_id = {i["incident_id"]: i for i in self.incidents}
        # mark hotspots
        cnt = Counter(i["location_id"] for i in self.incidents)
        top = {lid for lid, _ in cnt.most_common(int(len(self.dom_locs) * 0.25))}
        for l in self.locations:
            if l["location_id"] in top:
                l["is_hotspot"] = 1

    def _quantity(self, crime):
        if crime in ("NDPS_TRAFFICKING", "NDPS_POSSESSION"):
            if self.rng.random() < 0.5:
                return round(self.rng.uniform(0.05, 12.0), 3), "kg"
            return self.rng.randrange(50, 900), "grams"
        if crime == "FICN_COUNTERFEIT":
            return self.rng.randrange(50_000, 40_00_000), "INR face value"
        if crime == "ARMS_ACT":
            return self.rng.randint(2, 60), "nos"
        if crime == "WILDLIFE_TRAFFICKING":
            return round(self.rng.uniform(1, 900), 2), "kg"
        return self.rng.randint(1, 50), "nos"

    # ===================================================================
    # 10. CDR  (streamed straight to disk -- this is the biggest table)
    # ===================================================================
    def build_cdr(self, path):
        """
        Call pattern is driven by the person-person graph, so communication
        topology and intelligence topology agree -- but not perfectly: burner
        rotation, insulation layers and pure-noise calls make the CDR view a
        *lossy* projection of the truth, which is exactly the analytic problem.
        """
        fields = ["cdr_id", "caller_phone_id", "callee_phone_id", "caller_msisdn",
                  "callee_msisdn", "caller_person_id", "callee_person_id", "timestamp",
                  "duration_sec", "call_type", "cell_id", "location_id", "imei",
                  "roaming_flag"]
        imei_of = {}
        for pd_ in self.phone_device:
            imei_of[pd_["phone_id"]] = pd_["imei"]

        # candidate communicating pairs
        pairs = []
        for e in self.pp_edges:
            if e["relation"] == "RIVAL_OF":
                continue
            a, b = e["src_person_id"], e["dst_person_id"]
            if self.phones_of[a] and self.phones_of[b]:
                w = 1.0 + 2.5 * float(e["strength"])
                if e["relation"] in ("REPORTS_TO", "HANDLER_OF"):
                    w *= 1.6
                pairs.append((a, b, w))
        if not pairs:
            return
        weights = [w for _, _, w in pairs]

        n = 0
        rows_written = 0
        with open(path, "w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=fields)
            wr.writeheader()

            def emit(pa, pb, ts, ctype=None):
                nonlocal rows_written
                pha = self.rng.choice(self.phones_of[pa])
                phb = self.rng.choice(self.phones_of[pb])
                ctype = ctype or self.rng.choices(["CALL", "SMS"], weights=[.82, .18])[0]
                dur = 0 if ctype == "SMS" else max(3, int(self.rng.lognormvariate(3.6, 1.05)))
                pers = self.person_by_id[pa]
                lloc = self.rng.choice(self.locs_by_state.get(pers["native_state"], self.dom_locs))
                wr.writerow({
                    "cdr_id": f"CDR{rows_written+1:08d}",
                    "caller_phone_id": pha["phone_id"], "callee_phone_id": phb["phone_id"],
                    "caller_msisdn": pha["msisdn"], "callee_msisdn": phb["msisdn"],
                    "caller_person_id": pa, "callee_person_id": pb,
                    "timestamp": ts.isoformat(timespec="seconds"),
                    "duration_sec": dur,
                    "call_type": ("SMS" if ctype == "SMS" else
                                  self.rng.choices(["MOC", "MTC"], weights=[.55, .45])[0]),
                    "cell_id": f"{lloc['state'][:2].upper()}-{self.rng.randrange(1000,9999)}-"
                               f"{self.rng.randrange(1,7)}",
                    "location_id": lloc["location_id"],
                    "imei": imei_of.get(pha["phone_id"], ""),
                    "roaming_flag": int(self.rng.random() < 0.07),
                })
                key = tuple(sorted((pha["phone_id"], phb["phone_id"])))
                self.comm_pairs[key] += 1
                self.comm_duration[key] += dur
                rows_written += 1

            # --- baseline traffic along the social graph ---
            budget = int(self.target_cdr * 0.86)
            chosen = self.rng.choices(pairs, weights=weights, k=budget)
            for a, b, _w in chosen:
                # realistic diurnal profile: peak 10-14 and 19-23
                hour = self.rng.choices(range(24), weights=(
                    [1, 1, 1, 1, 1, 2, 4, 7, 10, 13, 16, 17, 16, 15, 13, 12, 12, 14,
                     16, 18, 17, 13, 8, 4]))[0]
                ts = T_START + timedelta(days=self.rng.randrange(TOTAL_DAYS),
                                         hours=hour, minutes=self.rng.randrange(60),
                                         seconds=self.rng.randrange(60))
                if self.rng.random() < 0.5:
                    emit(a, b, ts)
                else:
                    emit(b, a, ts)
                n += 1

            # --- planted pattern: call burst before an incident, then silence ---
            burst_incidents = self.rng.sample(
                [i for i in self.incidents if i["severity"] >= 6],
                min(120, len([i for i in self.incidents if i["severity"] >= 6])))
            for inc in burst_incidents:
                actors = [pi["person_id"] for pi in self.person_incident
                          if pi["incident_id"] == inc["incident_id"]
                          and pi["role_in_incident"] in ("ACCUSED", "SUSPECT",
                                                         "ABSCONDING_ACCUSED")]
                actors = [a for a in actors if self.phones_of[a]]
                if len(actors) < 2:
                    continue
                t0 = datetime.fromisoformat(inc["incident_datetime"])
                nburst = self.rng.randint(12, 40)
                for _ in range(nburst):
                    a, b = self.rng.sample(actors, 2)
                    ts = t0 - timedelta(hours=self.rng.uniform(0.5, 48))
                    emit(a, b, ts, "CALL")
                self.gt_anomalies.append({
                    "anomaly_id": self.nid("ANOM"),
                    "pattern": "PRE_INCIDENT_CALL_BURST",
                    "entity_type": "PERSON_SET",
                    "entity_ids": "|".join(actors),
                    "linked_incident_id": inc["incident_id"],
                    "window_start": (t0 - timedelta(hours=48)).isoformat(timespec="minutes"),
                    "window_end": t0.isoformat(timespec="minutes"),
                    "description": f"{nburst} calls among {len(actors)} accused inside the "
                                   f"48h preceding {inc['crime_type']} at {inc['area']}, "
                                   f"{inc['city']}; traffic drops to zero afterwards.",
                    "detect_with": "Temporal edge-density spike / burst detection on CDR",
                })

            # --- planted pattern: burner rotation ---
            rotators = self.rng.sample(
                [p for p in self.criminals if len(self.phones_of[p["person_id"]]) >= 3], 60) \
                if len([p for p in self.criminals if len(self.phones_of[p["person_id"]]) >= 3]) >= 60 \
                else [p for p in self.criminals if len(self.phones_of[p["person_id"]]) >= 3]
            for p in rotators:
                phs = self.phones_of[p["person_id"]]
                peers = [e["dst_person_id"] for e in self.pp_edges
                         if e["src_person_id"] == p["person_id"]] + \
                        [e["src_person_id"] for e in self.pp_edges
                         if e["dst_person_id"] == p["person_id"]]
                peers = [q for q in set(peers) if self.phones_of[q]]
                if not peers:
                    continue
                cut = self.rdate(T_START + timedelta(days=400), T_END - timedelta(days=200))
                for _ in range(self.rng.randint(10, 30)):
                    q = self.rng.choice(peers)
                    emit(p["person_id"], q, cut - timedelta(days=self.rng.uniform(1, 120)))
                for _ in range(self.rng.randint(10, 30)):
                    q = self.rng.choice(peers)
                    emit(p["person_id"], q, cut + timedelta(days=self.rng.uniform(1, 120)))
                self.gt_anomalies.append({
                    "anomaly_id": self.nid("ANOM"),
                    "pattern": "BURNER_SIM_ROTATION",
                    "entity_type": "PERSON",
                    "entity_ids": p["person_id"],
                    "linked_incident_id": "",
                    "window_start": (cut - timedelta(days=120)).isoformat(timespec="minutes"),
                    "window_end": (cut + timedelta(days=120)).isoformat(timespec="minutes"),
                    "description": f"{p['full_name']} discards one MSISDN and continues the "
                                   f"same contact set on another; handset IMEI is the "
                                   f"stitching key ({len(phs)} SIMs on file).",
                    "detect_with": "IMEI-based SIM stitching + contact-set Jaccard similarity",
                })

            # --- background noise: unrelated random calls ---
            noise = max(0, self.target_cdr - rows_written)
            with_phone = [p["person_id"] for p in self.persons if self.phones_of[p["person_id"]]]
            for _ in range(noise):
                a, b = self.rng.sample(with_phone, 2)
                ts = T_START + timedelta(seconds=self.rng.randrange(TOTAL_DAYS * 86400))
                emit(a, b, ts)

        self.cdr_rows = rows_written

    # ===================================================================
    # 11. TRANSACTIONS  (layering, structuring, mule fan-out, round-tripping)
    # ===================================================================
    def build_transactions(self, path):
        fields = ["txn_id", "src_account_id", "dst_account_id", "src_account_no",
                  "dst_account_no", "src_person_id", "dst_person_id", "amount_inr",
                  "channel", "timestamp", "narration", "is_cash", "branch_city",
                  "flagged_by_bank"]
        rows = 0
        acc_of_role = defaultdict(list)
        for p in self.criminals:
            for a in self.accounts_of[p["person_id"]]:
                acc_of_role[p["role"]].append((p, a))

        narrations = ["NEFT TRF", "IMPS/P2A", "UPI/P2P", "CASH DEP", "RTGS TRF",
                      "TRF TO SELF", "SALARY", "VENDOR PMT", "ADVANCE", "REFUND",
                      "LOAN REPAY", "COMM", "CONSULTANCY", "SCRAP SALE"]

        with open(path, "w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=fields)
            wr.writeheader()

            def emit(pa, aa, pb, ab, amount, ts, channel=None, narr=None, flagged=0):
                nonlocal rows
                channel = channel or self.rng.choices(
                    R.TXN_CHANNELS, weights=[.28, .16, .14, .07, .1, .09, .03, .02,
                                             .05, .02, .02, .02])[0]
                wr.writerow({
                    "txn_id": f"TXN{rows+1:08d}",
                    "src_account_id": aa["account_id"], "dst_account_id": ab["account_id"],
                    "src_account_no": aa["account_number"], "dst_account_no": ab["account_number"],
                    "src_person_id": pa["person_id"], "dst_person_id": pb["person_id"],
                    "amount_inr": int(amount), "channel": channel,
                    "timestamp": ts.isoformat(timespec="seconds"),
                    "narration": narr or self.rng.choice(narrations),
                    "is_cash": int(channel in ("CASH_DEPOSIT", "CASH_WITHDRAWAL",
                                               "ANGADIA", "HAWALA_TOKEN")),
                    "branch_city": aa["branch_city"],
                    "flagged_by_bank": flagged,
                })
                self.txn_pairs[(aa["account_id"], ab["account_id"])] += int(amount)
                rows += 1

            # ---- baseline: money follows the FINANCES / REPORTS_TO edges ----
            fin_edges = [e for e in self.pp_edges
                         if e["relation"] in ("FINANCES", "REPORTS_TO", "SUPPLIES_TO",
                                              "ASSOCIATE_OF")]
            base_budget = int(self.target_txn * 0.55)
            for _ in range(base_budget):
                e = self.rng.choice(fin_edges)
                pa = self.person_by_id[e["src_person_id"]]
                pb = self.person_by_id[e["dst_person_id"]]
                if not self.accounts_of[pa["person_id"]] or not self.accounts_of[pb["person_id"]]:
                    continue
                aa = self.rng.choice(self.accounts_of[pa["person_id"]])
                ab = self.rng.choice(self.accounts_of[pb["person_id"]])
                amt = self.rng.choice([
                    self.rng.randrange(500, 50_000),
                    self.rng.randrange(50_000, 5_00_000),
                    self.rng.randrange(5_00_000, 50_00_000)])
                emit(pa, aa, pb, ab, amt, self.rdate())

            # ---- planted: STRUCTURING (deposits just under the threshold) ----
            for _ in range(70):
                cand = [p for p in self.criminals
                        if p["role"] in ("HAWALA_OPERATOR", "FINANCIER", "MULE", "FENCE")
                        and self.accounts_of[p["person_id"]]]
                if not cand:
                    break
                target = self.rng.choice(cand)
                tacc = self.rng.choice(self.accounts_of[target["person_id"]])
                threshold = self.rng.choice([50_000, 10_00_000])
                n_dep = self.rng.randint(6, 22)
                t0 = self.rdate(T_START, T_END - timedelta(days=40))
                total = 0
                depositors = []
                for k in range(n_dep):
                    src = self.rng.choice([c for c in self.criminals
                                           if self.accounts_of[c["person_id"]]])
                    sacc = self.rng.choice(self.accounts_of[src["person_id"]])
                    amt = threshold - self.rng.randrange(500, 6_000)
                    emit(src, sacc, target, tacc, amt,
                         t0 + timedelta(days=self.rng.uniform(0, 25)),
                         channel="CASH_DEPOSIT", narr="CASH DEP", flagged=0)
                    total += amt
                    depositors.append(src["person_id"])
                self.gt_anomalies.append({
                    "anomaly_id": self.nid("ANOM"), "pattern": "STRUCTURING_SMURFING",
                    "entity_type": "ACCOUNT", "entity_ids": tacc["account_id"],
                    "linked_incident_id": "",
                    "window_start": t0.isoformat(timespec="minutes"),
                    "window_end": (t0 + timedelta(days=25)).isoformat(timespec="minutes"),
                    "description": f"{n_dep} cash deposits each just below the Rs.{inr(threshold)} "
                                   f"reporting threshold, aggregating Rs.{inr(total)}, into the "
                                   f"account of {target['full_name']} across 25 days.",
                    "detect_with": "Threshold-proximity clustering + deposit-count velocity",
                })

            # ---- planted: LAYERING CHAINS ----
            for _ in range(55):
                depth = self.rng.randint(4, 7)
                chain_people = [p for p in self.criminals if self.accounts_of[p["person_id"]]]
                if len(chain_people) < depth:
                    break
                chain = self.rng.sample(chain_people, depth)
                amt = self.rng.randrange(40_00_000, 12_00_00_000)
                t = self.rdate(T_START, T_END - timedelta(days=10))
                ids = []
                for i in range(depth - 1):
                    pa, pb = chain[i], chain[i + 1]
                    aa = self.rng.choice(self.accounts_of[pa["person_id"]])
                    ab = self.rng.choice(self.accounts_of[pb["person_id"]])
                    amt = int(amt * self.rng.uniform(0.88, 0.98))
                    t = t + timedelta(hours=self.rng.uniform(0.5, 30))
                    emit(pa, aa, pb, ab, amt, t,
                         channel=self.rng.choice(["RTGS", "NEFT", "IMPS"]),
                         narr="VENDOR PMT", flagged=int(self.rng.random() < 0.25))
                    ids.append(aa["account_id"])
                ids.append(ab["account_id"])
                self.gt_anomalies.append({
                    "anomaly_id": self.nid("ANOM"), "pattern": "LAYERING_CHAIN",
                    "entity_type": "ACCOUNT_PATH", "entity_ids": "|".join(ids),
                    "linked_incident_id": "",
                    "window_start": "", "window_end": t.isoformat(timespec="minutes"),
                    "description": f"{depth}-hop rapid pass-through with ~5-10% commission "
                                   f"shaved at each hop, completed inside "
                                   f"{depth * 30} hours.",
                    "detect_with": "Directed path search with time-ordering + value-decay test",
                })

            # ---- planted: MULE FAN-OUT (classic cyber-fraud payout) ----
            cyb = [s for s in self.syndicates if s["syndicate_code"] == "SYN-CYB"]
            for _ in range(40):
                syn = self.rng.choice(cyb) if cyb else self.rng.choice(self.syndicates)
                members = self.by_syndicate[syn["org_id"]]
                hubs = [m for m in members if m["role"] in ("TECH_HANDLER", "FINANCIER",
                                                            "LIEUTENANT")
                        and self.accounts_of[m["person_id"]]]
                mules = [m for m in members if m["role"] == "MULE"
                         and self.accounts_of[m["person_id"]]]
                if not hubs or len(mules) < 6:
                    continue
                hub = self.rng.choice(hubs)
                hacc = self.rng.choice(self.accounts_of[hub["person_id"]])
                picked = self.rng.sample(mules, min(len(mules), self.rng.randint(6, 20)))
                t0 = self.rdate(T_START, T_END - timedelta(days=5))
                for m in picked:
                    macc = self.rng.choice(self.accounts_of[m["person_id"]])
                    emit(hub, hacc, m, macc,
                         self.rng.randrange(9_000, 49_000),
                         t0 + timedelta(minutes=self.rng.uniform(0, 240)),
                         channel=self.rng.choice(["IMPS", "UPI"]), narr="UPI/P2P")
                    # mule withdraws almost immediately
                    emit(m, macc, m, macc,
                         self.rng.randrange(8_000, 48_000),
                         t0 + timedelta(minutes=self.rng.uniform(240, 900)),
                         channel="CASH_WITHDRAWAL", narr="ATM WDL")
                self.gt_anomalies.append({
                    "anomaly_id": self.nid("ANOM"), "pattern": "MULE_FANOUT",
                    "entity_type": "ACCOUNT", "entity_ids": hacc["account_id"],
                    "linked_incident_id": "",
                    "window_start": t0.isoformat(timespec="minutes"),
                    "window_end": (t0 + timedelta(hours=15)).isoformat(timespec="minutes"),
                    "description": f"Single hub account fans {len(picked)} sub-Rs.50,000 "
                                   f"transfers to distinct mule accounts within 4 hours; "
                                   f"each mule withdraws in cash within 15 hours.",
                    "detect_with": "Out-degree burst + downstream cash-out latency",
                })

            # ---- planted: ROUND-TRIPPING ----
            for _ in range(25):
                ppl = [p for p in self.criminals if self.accounts_of[p["person_id"]]]
                hop = self.rng.sample(ppl, 4)
                a0 = self.rng.choice(self.accounts_of[hop[0]["person_id"]])
                amt = self.rng.randrange(50_00_000, 8_00_00_000)
                t = self.rdate(T_START, T_END - timedelta(days=60))
                path_ids = [a0["account_id"]]
                prev_p, prev_a = hop[0], a0
                for nxt in hop[1:]:
                    na = self.rng.choice(self.accounts_of[nxt["person_id"]])
                    t += timedelta(days=self.rng.uniform(1, 12))
                    emit(prev_p, prev_a, nxt, na, amt, t, channel="RTGS", narr="ADVANCE")
                    path_ids.append(na["account_id"])
                    prev_p, prev_a = nxt, na
                t += timedelta(days=self.rng.uniform(1, 12))
                emit(prev_p, prev_a, hop[0], a0, int(amt * 0.97), t,
                     channel="RTGS", narr="REFUND", flagged=1)
                self.gt_anomalies.append({
                    "anomaly_id": self.nid("ANOM"), "pattern": "ROUND_TRIPPING",
                    "entity_type": "ACCOUNT_CYCLE", "entity_ids": "|".join(path_ids),
                    "linked_incident_id": "", "window_start": "",
                    "window_end": t.isoformat(timespec="minutes"),
                    "description": "Funds return to the originating account after 4 hops "
                                   "with ~3% attrition, narrated as an advance and refund.",
                    "detect_with": "Directed cycle detection with amount tolerance",
                })

            # ---- planted: DORMANT ACCOUNT REACTIVATION ----
            for _ in range(45):
                cand = [a for a in self.accounts if a["status"] == "DORMANT"]
                if not cand:
                    break
                acc = self.rng.choice(cand)
                holder = self.person_by_id[acc["holder_person_id"]]
                other = self.rng.choice([p for p in self.criminals
                                         if self.accounts_of[p["person_id"]]])
                oacc = self.rng.choice(self.accounts_of[other["person_id"]])
                t0 = self.rdate(T_START + timedelta(days=600), T_END - timedelta(days=5))
                big = self.rng.randrange(20_00_000, 3_00_00_000)
                emit(other, oacc, holder, acc, big, t0, channel="RTGS", narr="ADVANCE",
                     flagged=1)
                emit(holder, acc, other, oacc, int(big * 0.98),
                     t0 + timedelta(hours=self.rng.uniform(1, 30)),
                     channel="RTGS", narr="TRF", flagged=1)
                self.gt_anomalies.append({
                    "anomaly_id": self.nid("ANOM"), "pattern": "DORMANT_REACTIVATION",
                    "entity_type": "ACCOUNT", "entity_ids": acc["account_id"],
                    "linked_incident_id": "",
                    "window_start": t0.isoformat(timespec="minutes"),
                    "window_end": (t0 + timedelta(days=2)).isoformat(timespec="minutes"),
                    "description": f"Dormant account receives Rs.{inr(big)} and passes ~98% "
                                   f"onward within 30 hours.",
                    "detect_with": "Inactivity-gap feature + in/out ratio + hold-time",
                })

            # ---- remaining noise ----
            all_acc_people = [p for p in self.persons if self.accounts_of[p["person_id"]]]
            while rows < self.target_txn:
                pa, pb = self.rng.sample(all_acc_people, 2)
                emit(pa, self.rng.choice(self.accounts_of[pa["person_id"]]),
                     pb, self.rng.choice(self.accounts_of[pb["person_id"]]),
                     self.rng.randrange(200, 2_00_000), self.rdate())

        self.txn_rows = rows

    # ===================================================================
    # 12. LATENT LINKS  (only discoverable by joining data sources)
    # ===================================================================
    def _latent_ok(self, a, b):
        """A latent link is only interesting if no explicit edge already states it."""
        return (a["person_id"] != b["person_id"]
                and (a["person_id"], b["person_id"]) not in self._pp_index)

    def build_latent_links(self):
        # (a) shared handset across syndicates
        for _ in range(35):
            s1, s2 = self.rng.sample(self.syndicates, 2)
            a = self.rng.choice(self.by_syndicate[s1["org_id"]])
            b = self.rng.choice(self.by_syndicate[s2["org_id"]])
            pa = self.phones_of[a["person_id"]]
            pb = self.phones_of[b["person_id"]]
            if not pa or not pb or not self._latent_ok(a, b):
                continue
            shared = self.imei()
            dev = {"device_id": self.nid("DEV"), "imei": shared,
                   "make": self.rng.choice(["Samsung", "Xiaomi", "Vivo", "Oppo", "Realme"]),
                   "model": "M" + str(self.rng.randrange(10, 99)),
                   "is_dual_sim": 1, "first_seen": self.rdate().date().isoformat()}
            self.devices.append(dev)
            for ph, who in ((self.rng.choice(pa), a), (self.rng.choice(pb), b)):
                self.phone_device.append({
                    "phone_id": ph["phone_id"], "device_id": dev["device_id"],
                    "imei": shared, "msisdn": ph["msisdn"],
                    "first_seen": ph["activation_date"],
                    "last_seen": T_END.date().isoformat(),
                })
            self.gt_latent.append({
                "latent_id": self.nid("LAT"),
                "person_a": a["person_id"], "person_a_name": a["full_name"],
                "person_b": b["person_id"], "person_b_name": b["full_name"],
                "syndicate_a": s1["syndicate_code"], "syndicate_b": s2["syndicate_code"],
                "mechanism": "SHARED_HANDSET_IMEI", "evidence_id": shared,
                "note": "Two SIMs subscribed in different names were used in the same "
                        "handset; no direct edge exists in the intel graph.",
                "detect_with": "Join CDR.imei -> phone -> subscriber; look for IMEIs with "
                               ">1 distinct subscriber",
            })

        # (b) shared vehicle across incidents in different states
        for _ in range(30):
            if len(self.vehicles) < 2 or len(self.incidents) < 2:
                break
            v = self.rng.choice(self.vehicles)
            i1, i2 = self.rng.sample(self.incidents, 2)
            if i1["state"] == i2["state"]:
                continue
            for inc in (i1, i2):
                self.incident_vehicle.append({
                    "incident_id": inc["incident_id"], "vehicle_id": v["vehicle_id"],
                    "registration_no": v["registration_no"],
                    "involvement": "SEEN_AT_SCENE",
                })
            a1 = [pi["person_id"] for pi in self.person_incident
                  if pi["incident_id"] == i1["incident_id"] and pi["role_in_incident"] != "WITNESS"]
            a2 = [pi["person_id"] for pi in self.person_incident
                  if pi["incident_id"] == i2["incident_id"] and pi["role_in_incident"] != "WITNESS"]
            if not a1 or not a2:
                continue
            pa, pb = self.person_by_id[a1[0]], self.person_by_id[a2[0]]
            if not self._latent_ok(pa, pb):
                continue
            self.gt_latent.append({
                "latent_id": self.nid("LAT"),
                "person_a": pa["person_id"], "person_a_name": pa["full_name"],
                "person_b": pb["person_id"], "person_b_name": pb["full_name"],
                "syndicate_a": pa["syndicate_code"], "syndicate_b": pb["syndicate_code"],
                "mechanism": "SHARED_VEHICLE",
                "evidence_id": v["registration_no"],
                "note": f"Vehicle {v['registration_no']} appears at incidents in "
                        f"{i1['state']} and {i2['state']}.",
                "detect_with": "Two-hop path person->incident->vehicle->incident->person",
            })

        # (c) co-location: two persons, same place, same day
        for _ in range(120):
            s1, s2 = self.rng.sample(self.syndicates, 2)
            a = self.rng.choice(self.by_syndicate[s1["org_id"]])
            b = self.rng.choice(self.by_syndicate[s2["org_id"]])
            if not self._latent_ok(a, b):
                continue
            loc = self.rng.choice(self.dom_locs)
            day = self.rdate()
            for who in (a, b):
                self.person_location.append({
                    "person_id": who["person_id"], "location_id": loc["location_id"],
                    "association": self.rng.choice(["HOTEL_STAY", "TOWER_DUMP_PRESENCE",
                                                    "SURVEILLANCE_SIGHTING"]),
                    "observed_on": day.date().isoformat(),
                    "source_type": self.rng.choice(["TOWER_DUMP", "SURVEILLANCE_REPORT",
                                                    "INFORMANT_TIP"]),
                    "confidence": round(self.rng.uniform(.5, .9), 2),
                })
            self.colocations.append({
                "colocation_id": self.nid("COL"),
                "person_a": a["person_id"], "person_b": b["person_id"],
                "location_id": loc["location_id"], "area": loc["area"], "city": loc["city"],
                "observed_on": day.date().isoformat(),
                "time_gap_minutes": self.rng.randrange(2, 180),
                "source_type": "TOWER_DUMP",
                "confidence": round(self.rng.uniform(.45, .85), 2),
            })
            self.gt_latent.append({
                "latent_id": self.nid("LAT"),
                "person_a": a["person_id"], "person_a_name": a["full_name"],
                "person_b": b["person_id"], "person_b_name": b["full_name"],
                "syndicate_a": s1["syndicate_code"], "syndicate_b": s2["syndicate_code"],
                "mechanism": "CO_LOCATION", "evidence_id": loc["location_id"],
                "note": f"Both placed at {loc['area']}, {loc['city']} on "
                        f"{day.date().isoformat()} within minutes of each other.",
                "detect_with": "Spatio-temporal join on tower dumps / hotel registers",
            })

        # (d) shared bank account (joint control)
        for _ in range(28):
            s1, s2 = self.rng.sample(self.syndicates, 2)
            a = self.rng.choice([m for m in self.by_syndicate[s1["org_id"]]
                                 if self.accounts_of[m["person_id"]]] or
                                self.by_syndicate[s1["org_id"]])
            b = self.rng.choice(self.by_syndicate[s2["org_id"]])
            if not self.accounts_of[a["person_id"]] or not self._latent_ok(a, b):
                continue
            acc = self.rng.choice(self.accounts_of[a["person_id"]])
            self.person_account.append({
                "person_id": b["person_id"], "account_id": acc["account_id"],
                "relation": "OPERATES_AS_MANDATE_HOLDER",
                "from_date": acc["opened_date"], "to_date": "",
            })
            self.gt_latent.append({
                "latent_id": self.nid("LAT"),
                "person_a": a["person_id"], "person_a_name": a["full_name"],
                "person_b": b["person_id"], "person_b_name": b["full_name"],
                "syndicate_a": s1["syndicate_code"], "syndicate_b": s2["syndicate_code"],
                "mechanism": "SHARED_BANK_ACCOUNT", "evidence_id": acc["account_id"],
                "note": "Account held by one and operated by the other under a mandate.",
                "detect_with": "person_account fan-in: accounts with >1 controlling person",
            })

    # ===================================================================
    # 13. DUPLICATES  (entity-resolution ground truth -- "possible match")
    # ===================================================================
    def build_duplicates(self, n_true=110, n_decoy=90):
        """
        TRUE duplicates  : the same human entered twice under name variants.
        DECOY near-matches: different humans who merely look alike.
        A correct system must NOT auto-merge either; it must propose and wait.
        """
        pool = self.rng.sample(self.criminals, min(len(self.criminals), n_true))
        for p in pool:
            first, sur = p["first_name"], p["surname"]
            nf = self.rng.choice(R.TRANSLITERATION_VARIANTS.get(first, [first]))
            ns = self.rng.choice(R.TRANSLITERATION_VARIANTS.get(sur, [sur]))
            variant_type = []
            if nf != first:
                variant_type.append("GIVEN_NAME_TRANSLITERATION")
            if ns != sur:
                variant_type.append("SURNAME_TRANSLITERATION")
            if not variant_type:
                style = self.rng.random()
                if style < 0.4:
                    nf = first.split()[0][0] + "."
                    variant_type.append("INITIAL_ONLY")
                elif style < 0.7:
                    ns = ""
                    variant_type.append("SURNAME_DROPPED")
                else:
                    nf, ns = sur, first
                    variant_type.append("NAME_ORDER_SWAPPED")

            dob = datetime.fromisoformat(p["date_of_birth"])
            jitter = self.rng.choice([0, 0, 0, 1, -1, 365, -365])
            dupe = dict(p)
            dupe["person_id"] = self.nid("P")
            dupe["first_name"], dupe["surname"] = nf, ns
            dupe["full_name"] = (nf + " " + ns).strip()
            dupe["date_of_birth"] = (dob + timedelta(days=jitter)).date().isoformat()
            dupe["nic_ref"] = "NIC-" + "".join(
                self.rng.choice(string.ascii_uppercase + string.digits) for _ in range(9))
            dupe["record_source"] = self.rng.choice(["FIR", "CHARGESHEET",
                                                     "CRIMINAL_HISTORY_DB", "INFORMANT_TIP"])
            dupe["alias"] = p["alias"] if self.rng.random() < 0.55 else ""
            dupe["total_cases"] = 0
            dupe["is_duplicate_record_of"] = p["person_id"]
            self.persons.append(dupe)
            self.person_by_id[dupe["person_id"]] = dupe

            # A duplicate record is not an orphan: the second source document
            # names some of the SAME associates. Shared neighbours are the
            # strongest graph signal an ER model can exploit, so plant them --
            # otherwise the merge is undecidable from the graph alone.
            nbrs = [e["dst_person_id"] for e in self.pp_edges
                    if e["src_person_id"] == p["person_id"]] + \
                   [e["src_person_id"] for e in self.pp_edges
                    if e["dst_person_id"] == p["person_id"]]
            nbrs = list({n for n in nbrs if n in self.person_by_id})
            shared_n = 0
            if nbrs:
                for n in self.rng.sample(nbrs, min(len(nbrs), self.rng.randint(1, 3))):
                    self._add_pp(dupe, self.person_by_id[n], "CO_ACCUSED_WITH",
                                 source=dupe["record_source"],
                                 verified=0,
                                 confidence=round(self.rng.uniform(.4, .75), 2))
                    shared_n += 1

            # ~45% of the time the second record also carries a phone number
            # already attributed to the original -- the classic hard identifier
            # that lets a system move from "possible match" to "confirmed".
            shared_phone = ""
            if self.phones_of[p["person_id"]] and self.rng.random() < 0.45:
                ph = self.rng.choice(self.phones_of[p["person_id"]])
                self.person_phone.append({
                    "person_id": dupe["person_id"], "phone_id": ph["phone_id"],
                    "usage_type": "USED_NOT_REGISTERED",
                    "from_date": ph["activation_date"], "to_date": "",
                    "confidence": round(self.rng.uniform(.6, .9), 2),
                })
                shared_phone = ph["msisdn"]

            self.gt_duplicates.append({
                "record_a": p["person_id"], "name_a": p["full_name"], "dob_a": p["date_of_birth"],
                "record_b": dupe["person_id"], "name_b": dupe["full_name"],
                "dob_b": dupe["date_of_birth"],
                "is_same_person": 1,
                "variant_type": "|".join(variant_type),
                "shared_signals": "|".join(filter(None, [
                    "SAME_HOME_LOCATION",
                    "SAME_ALIAS" if dupe["alias"] else "",
                    "DOB_EXACT" if jitter == 0 else "DOB_NEAR",
                    f"SHARED_NEIGHBOURS_{shared_n}" if shared_n else "",
                    "SHARED_PHONE" if shared_phone else "",
                ])),
                "shared_phone": shared_phone,
                "correct_action": "PROPOSE_MERGE_REQUIRE_HUMAN_CONFIRMATION",
            })

        # decoys: coincidental look-alikes that must NOT be merged
        for _ in range(n_decoy):
            a, b = self.rng.sample(self.criminals, 2)
            if a["native_state"] == b["native_state"]:
                continue
            twin = dict(b)
            twin["person_id"] = self.nid("P")
            twin["first_name"] = a["first_name"]
            twin["surname"] = a["surname"]
            twin["full_name"] = f"{a['first_name']} {a['surname']}"
            twin["alias"] = ""
            twin["total_cases"] = 0
            twin["is_duplicate_record_of"] = ""
            self.persons.append(twin)
            self.person_by_id[twin["person_id"]] = twin

            # The decoy gets its OWN unrelated associates. Same name, different
            # neighbourhood -- so a name-only matcher fires and a graph-aware
            # matcher correctly declines.
            for other in self.rng.sample(self.criminals, self.rng.randint(1, 3)):
                self._add_pp(twin, other, "ASSOCIATE_OF",
                             source=self.rng.choice(["FIR", "CRIMINAL_HISTORY_DB"]),
                             verified=0, confidence=round(self.rng.uniform(.4, .7), 2))

            self.gt_duplicates.append({
                "record_a": a["person_id"], "name_a": a["full_name"], "dob_a": a["date_of_birth"],
                "record_b": twin["person_id"], "name_b": twin["full_name"],
                "dob_b": twin["date_of_birth"],
                "is_same_person": 0,
                "variant_type": "COINCIDENTAL_NAME_COLLISION",
                "shared_signals": "SAME_FULL_NAME",
                "shared_phone": "",
                "correct_action": "DO_NOT_MERGE_DIFFERENT_DOB_AND_DISTRICT",
            })

        for p in self.persons:
            p.setdefault("is_duplicate_record_of", "")

    # ===================================================================
    # 14. UNSTRUCTURED NARRATIVES + NER GROUND TRUTH
    # ===================================================================
    def _ctx_for(self, inc, accused, civ):
        loc = self.loc_by_id[inc["location_id"]]
        loc2 = self.rng.choice(self.dom_locs)
        loc3 = self.rng.choice(self.dom_locs)
        # The narrative templates are written with masculine pronouns ("he
        # disclosed his identity as ..."), which mirrors how these documents
        # actually read. Put a male subject in the p1 slot when the accused set
        # has one, so the pronouns agree with the named person.
        ordered = sorted(accused, key=lambda x: 0 if x["gender"] == "M" else 1)
        p1 = ordered[0]
        rest = [a for a in ordered[1:]] or [self.rng.choice(self.criminals)]
        p2 = rest[0]
        p3 = rest[1] if len(rest) > 1 else self.rng.choice(self.criminals)
        bank1, bank2 = self.rng.sample(R.BANKS, 2)
        acc1 = self.rng.choice(self.accounts)["account_number"]
        acc2 = self.rng.choice(self.accounts)["account_number"]
        ph1 = self.phones_of[p1["person_id"]]
        ph2 = self.phones_of[p2["person_id"]]
        phone1 = ph1[0]["msisdn"] if ph1 else self.msisdn()
        phone2 = ph2[0]["msisdn"] if ph2 else self.msisdn()
        veh = self.rng.choice(self.vehicles) if self.vehicles else None
        make, models = self.rng.choice(R.VEHICLE_MAKES)
        if inc["crime_type"] in R.CONTRABAND:
            contraband = self.rng.choice(R.CONTRABAND[inc["crime_type"]])
        else:
            contraband = self.rng.choice(
                [c for lst in R.CONTRABAND.values() for c in lst])
        qv, qu = self._quantity(inc["crime_type"])
        veh_desc = f"{make} {self.rng.choice(models)}"
        when = datetime.fromisoformat(inc["incident_datetime"])
        amount = inc["loss_or_value_inr"] or self.rng.randrange(1_00_000, 5_00_00_000)
        org = self.rng.choice([o for o in self.orgs if o["org_type"] != "SYNDICATE"])
        fh = self.rng.choice(R.FOREIGN_HUBS)

        n_val = self.rng.randint(5, 28)
        ctx = {
            "date": when.strftime("%d.%m.%Y"),
            "date2": (when + timedelta(days=self.rng.randint(1, 20))).strftime("%d.%m.%Y"),
            "time": when.strftime("%H%M"),
            "time2": (when + timedelta(hours=self.rng.randint(1, 6))).strftime("%H%M"),
            "ps": inc["ps_name"].replace(" Police Station", ""),
            "agency": inc["investigating_agency"],
            "complainant": civ["full_name"],
            "victim": civ["full_name"],
            "occupation": self.rng.choice(R.OCCUPATIONS),
            "age": self.rng.randint(17, 62),
            "area": loc["area"], "city": loc["city"],
            "area2": loc2["area"], "city2": loc2["city"],
            "area3": loc3["area"],
            "p1": p1["full_name"], "p2": p2["full_name"], "p3": p3["full_name"],
            "alias1": p1["alias"] or self._alias(p1["first_name"]),
            "alias2": p2["alias"] or self._alias(p2["first_name"]),
            "alias3": p3["alias"] or self._alias(p3["first_name"]),
            "phone1": phone1, "phone2": phone2,
            "account1": acc1, "account2": acc2,
            "bank1": bank1, "bank2": bank2,
            "amount": inr(amount),
            "n": n_val, "n2": self.rng.randint(4, 90),
            # branch count must stay below the deposit count it is described against
            "n_branches": self.rng.randint(2, max(2, n_val // 3)),
            "days": self.rng.randint(3, 60), "days_short": self.rng.randint(2, 12),
            "hours": self.rng.choice([24, 48, 72]),
            "mins": self.rng.randint(5, 95),
            "plate": veh["registration_no"] if veh else self.plate(inc["state"]),
            "vehicle": veh_desc,
            "a_vehicle": ("an " if veh_desc[0].upper() in "AEIOU" else "a ") + veh_desc,
            "contraband": contraband,
            "qty": f"{qv} {qu}",
            "cavity": self.rng.choice(R.CAVITIES),
            "seal": "".join(self.rng.choice(string.ascii_uppercase) for _ in range(3)),
            "org1": org["name"],
            "foreign_city": fh[1],
            "place_type": self.rng.choice(R.PLACE_TYPES),
            "fir": f"FIR No. {inc['fir_no']} of {inc['ps_name']}",
            "rel": self.rng.choice(R.RELIABILITY_GRADES[:4]),
            "cred": self.rng.choice(R.CREDIBILITY_GRADES[:4]),
            "conf": self.rng.choice(R.CONFIDENCE_LEVELS),
            # human-readable syndicate names -- the raw code reads badly in prose,
            # and unaffiliated incidents have no syndicate to name at all
            "syn_label": (self.syn_label_by_code.get(inc["syndicate_code"])
                          or self.rng.choice(self.syndicates)["archetype_label"]),
            "syn_label2": self.rng.choice(self.syndicates)["archetype_label"],
        }
        ents = [
            (ctx["p1"], "PERSON", p1["person_id"]),
            (ctx["p2"], "PERSON", p2["person_id"]),
            (ctx["p3"], "PERSON", p3["person_id"]),
            (ctx["complainant"], "PERSON", civ["person_id"]),
            (ctx["alias1"], "ALIAS", p1["person_id"]),
            (ctx["alias2"], "ALIAS", p2["person_id"]),
            (ctx["alias3"], "ALIAS", p3["person_id"]),
            (ctx["phone1"], "PHONE", ""), (ctx["phone2"], "PHONE", ""),
            (ctx["account1"], "ACCOUNT", ""), (ctx["account2"], "ACCOUNT", ""),
            (ctx["bank1"], "ORG", ""), (ctx["bank2"], "ORG", ""),
            (ctx["org1"], "ORG", org["org_id"]),
            (ctx["city"], "GPE", ""), (ctx["city2"], "GPE", ""),
            (ctx["area"], "LOC", loc["location_id"]),
            (ctx["area2"], "LOC", loc2["location_id"]),
            (ctx["area3"], "LOC", loc3["location_id"]),
            (ctx["plate"], "VEHICLE_REG", veh["vehicle_id"] if veh else ""),
            (ctx["vehicle"], "VEHICLE_MODEL", ""),
            ("Rs." + ctx["amount"], "MONEY", ""),
            (ctx["date"], "DATE", ""), (ctx["date2"], "DATE", ""),
            (ctx["contraband"], "CONTRABAND", ""),
            (ctx["qty"], "QUANTITY", ""),
            (ctx["ps"] + " Police Station", "POLICE_STATION", inc["ps_id"]),
            (ctx["agency"], "AGENCY", ""),
            (ctx["foreign_city"], "GPE", ""),
        ]
        return ctx, ents

    # Which opening paragraph fits which offence. A "patrolling party noticed
    # suspicious movement" opening in front of a job-fraud body is the kind of
    # incoherence that makes generated text obvious.
    _RAID_LED = {"NDPS_TRAFFICKING", "NDPS_POSSESSION", "ARMS_ACT", "FICN_COUNTERFEIT",
                 "BETTING_GAMBLING", "ILLEGAL_MINING", "SMUGGLING_CUSTOMS",
                 "WILDLIFE_TRAFFICKING", "LIQUOR_SMUGGLING", "CRIMINAL_CONSPIRACY"}
    _COMPLAINT_LED = {"CHEATING_FRAUD", "FORGERY", "CYBER_FRAUD", "EXTORTION", "MURDER",
                      "ATTEMPT_TO_MURDER", "KIDNAP_FOR_RANSOM", "ROBBERY", "DACOITY",
                      "LAND_GRABBING", "HUMAN_TRAFFICKING", "VEHICLE_THEFT",
                      "CHIT_FUND_PONZI", "RIOTING"}

    def _opening_for(self, crime):
        if crime in self._RAID_LED:
            idx = [1, 2, 4]
        elif crime in self._COMPLAINT_LED:
            idx = [0, 1, 3]
        else:
            idx = list(range(len(R.FIR_OPENINGS)))
        return R.FIR_OPENINGS[self.rng.choice(idx)]

    def build_narratives(self):
        self.syn_label_by_code = {s["syndicate_code"]: s["archetype_label"]
                                  for s in self.syndicates}
        pi_by_inc = defaultdict(list)
        for pi in self.person_incident:
            pi_by_inc[pi["incident_id"]].append(pi)

        for inc in self.incidents:
            rows = pi_by_inc[inc["incident_id"]]
            accused = [self.person_by_id[r["person_id"]] for r in rows
                       if r["role_in_incident"] in ("ACCUSED", "SUSPECT",
                                                    "ABSCONDING_ACCUSED")]
            civs = [self.person_by_id[r["person_id"]] for r in rows
                    if r["role_in_incident"] in ("COMPLAINANT", "VICTIM", "WITNESS")]
            if not accused:
                continue
            civ = civs[0] if civs else self.rng.choice(self.civilians)
            ctx, ents = self._ctx_for(inc, accused, civ)

            opening = self._opening_for(inc["crime_type"]).format(**ctx)
            body_pool = R.FIR_BODY_TEMPLATES.get(inc["crime_type"],
                                                 R.FIR_BODY_TEMPLATES["DEFAULT"])
            body = self.rng.choice(body_pool).format(**ctx)
            closing = (f" Accordingly a case under section {inc['ipc_section']} "
                       f"(BNS {inc['bns_section']}) has been registered vide FIR No. "
                       f"{inc['fir_no']} at {inc['ps_name']} and investigation has been "
                       f"taken up.")
            text = opening + " " + body + closing

            self.narratives.append({
                "doc_id": self.nid("DOC"),
                "doc_type": "FIR_NARRATIVE",
                "incident_id": inc["incident_id"],
                "case_id": inc["case_id"],
                "fir_no": inc["fir_no"],
                "police_station": inc["ps_name"],
                "district": inc["city"], "state": inc["state"],
                "crime_type": inc["crime_type"],
                "recorded_on": inc["reported_datetime"],
                "language": "en",
                "source_type": "FIR",
                "source_reliability": inc["source_reliability"],
                "text": text,
                "entities": spans_for(text, ents),
                "linked_person_ids": [a["person_id"] for a in accused],
            })

        # surveillance reports
        for _ in range(600):
            inc = self.rng.choice(self.incidents)
            rows = pi_by_inc[inc["incident_id"]]
            accused = [self.person_by_id[r["person_id"]] for r in rows
                       if r["role_in_incident"] in ("ACCUSED", "SUSPECT",
                                                    "ABSCONDING_ACCUSED")]
            if not accused:
                continue
            civ = self.rng.choice(self.civilians)
            ctx, ents = self._ctx_for(inc, accused, civ)
            text = self.rng.choice(R.SURVEILLANCE_TEMPLATES).format(**ctx)
            self.narratives.append({
                "doc_id": self.nid("DOC"), "doc_type": "SURVEILLANCE_REPORT",
                "incident_id": "", "case_id": inc["case_id"], "fir_no": "",
                "police_station": inc["ps_name"], "district": inc["city"],
                "state": inc["state"], "crime_type": inc["crime_type"],
                "recorded_on": self.rdate().isoformat(timespec="minutes"),
                "language": "en", "source_type": "SURVEILLANCE_REPORT",
                "source_reliability": self.rng.choice(R.RELIABILITY_GRADES[:4]),
                "text": text, "entities": spans_for(text, ents),
                "linked_person_ids": [a["person_id"] for a in accused[:3]],
            })

        # intelligence notes
        for _ in range(420):
            inc = self.rng.choice(self.incidents)
            rows = pi_by_inc[inc["incident_id"]]
            accused = [self.person_by_id[r["person_id"]] for r in rows
                       if r["role_in_incident"] != "WITNESS"]
            accused = [a for a in accused if a["person_type"] == "CRIMINAL"]
            if not accused:
                continue
            civ = self.rng.choice(self.civilians)
            ctx, ents = self._ctx_for(inc, accused, civ)
            text = self.rng.choice(R.INTEL_NOTE_TEMPLATES).format(**ctx)
            self.narratives.append({
                "doc_id": self.nid("DOC"), "doc_type": "INTELLIGENCE_NOTE",
                "incident_id": "", "case_id": "", "fir_no": "",
                "police_station": "", "district": inc["city"], "state": inc["state"],
                "crime_type": inc["crime_type"],
                "recorded_on": self.rdate().isoformat(timespec="minutes"),
                "language": "en", "source_type": "INTELLIGENCE_REPORT",
                "source_reliability": self.rng.choice(R.RELIABILITY_GRADES),
                "text": text, "entities": spans_for(text, ents),
                "linked_person_ids": [a["person_id"] for a in accused[:3]],
            })

    # ===================================================================
    # 15. UNIFIED GRAPH PROJECTION
    # ===================================================================
    def build_graph_projection(self):
        nodes, edges = [], []

        def N(nid_, ntype, label, **attrs):
            nodes.append({"node_id": nid_, "node_type": ntype, "label": label,
                          "attributes": json.dumps(attrs, ensure_ascii=False)})

        def E(s, d, etype, weight=1.0, **attrs):
            edges.append({"src": s, "dst": d, "edge_type": etype,
                          "weight": round(float(weight), 4),
                          "attributes": json.dumps(attrs, ensure_ascii=False)})

        for p in self.persons:
            N(p["person_id"], "Person", p["full_name"],
              alias=p["alias"], role=p["role"], syndicate=p["syndicate_code"],
              risk=p["risk_score"], influence=p["influence_score"],
              custody=p["custody_status"], city=p["native_city"], state=p["native_state"],
              person_type=p["person_type"], bridge=p["is_cross_syndicate_bridge"])
        for o in self.orgs:
            N(o["org_id"], "Organization", o["name"], org_type=o["org_type"],
              city=o["hq_city"], state=o["hq_state"], status=o["status"])
        for l in self.locations:
            N(l["location_id"], "Location", f"{l['area']}, {l['city']}",
              state=l["state"], country=l["country"], lat=l["latitude"],
              lon=l["longitude"], hotspot=l["is_hotspot"])
        for ph in self.phones:
            N(ph["phone_id"], "Phone", ph["msisdn"], operator=ph["operator"],
              burner=ph["is_burner"], kyc=ph["kyc_status"])
        for d in self.devices:
            N(d["device_id"], "Device", d["imei"], make=d["make"])
        for a in self.accounts:
            N(a["account_id"], "BankAccount", a["account_number"], bank=a["bank"],
              mule=a["is_mule_account"], status=a["status"])
        for v in self.vehicles:
            N(v["vehicle_id"], "Vehicle", v["registration_no"], make=v["make"],
              model=v["model"], fake_plate=v["is_fake_plate"])
        for i in self.incidents:
            N(i["incident_id"], "Incident", f"{i['crime_type']} {i['fir_no']}",
              crime=i["crime_type"], severity=i["severity"], date=i["incident_datetime"],
              city=i["city"], state=i["state"])
        for c in self.cases:
            N(c["case_id"], "Case", c["case_title"], crime=c["primary_crime"],
              agency=c["lead_agency"], status=c["status"])

        for e in self.pp_edges:
            E(e["src_person_id"], e["dst_person_id"], e["relation"],
              weight=e["strength"], subtype=e["subtype"], confidence=e["confidence"],
              verified=e["is_verified"], source=e["source_type"])
        for r in self.person_org:
            E(r["person_id"], r["org_id"], "MEMBER_OF", 1.0, role=r["role_in_org"],
              benami=r["is_benami"])
        for r in self.person_phone:
            E(r["person_id"], r["phone_id"], "USES_PHONE", r["confidence"],
              usage=r["usage_type"])
        for r in self.phone_device:
            E(r["phone_id"], r["device_id"], "SIM_IN_DEVICE", 1.0, imei=r["imei"])
        for r in self.person_account:
            E(r["person_id"], r["account_id"], "CONTROLS_ACCOUNT", 1.0,
              relation=r["relation"])
        for r in self.person_vehicle:
            E(r["person_id"], r["vehicle_id"], "OWNS_VEHICLE", r["confidence"])
        for r in self.person_location:
            E(r["person_id"], r["location_id"], "PRESENT_AT", r["confidence"],
              association=r["association"], on=r["observed_on"])
        for r in self.person_incident:
            E(r["person_id"], r["incident_id"], "INVOLVED_IN", 1.0,
              role=r["role_in_incident"], arrested=r["arrested"])
        for r in self.incident_vehicle:
            E(r["incident_id"], r["vehicle_id"], "VEHICLE_INVOLVED", 1.0,
              involvement=r["involvement"])
        for i in self.incidents:
            E(i["incident_id"], i["location_id"], "OCCURRED_AT", 1.0)
            E(i["incident_id"], i["case_id"], "PART_OF_CASE", 1.0)

        # aggregated communication + money edges (raw rows stay in their own CSVs)
        for (a, b), cnt in self.comm_pairs.items():
            E(a, b, "COMMUNICATES_WITH", math.log1p(cnt), calls=cnt,
              total_duration_sec=self.comm_duration[(a, b)])
        for (a, b), amt in self.txn_pairs.items():
            E(a, b, "TRANSFERS_TO", math.log1p(amt / 1000.0), total_amount_inr=amt)

        self.graph_nodes, self.graph_edges = nodes, edges

    # ===================================================================
    # 16. WRITE EVERYTHING
    # ===================================================================
    def _csv(self, sub, name, rows, fieldnames=None):
        if not rows:
            return 0
        path = os.path.join(self.out, sub, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fn = fieldnames or list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=fn, extrasaction="ignore")
            wr.writeheader()
            for r in rows:
                wr.writerow(r)
        return len(rows)

    def write_all(self):
        os.makedirs(self.out, exist_ok=True)
        counts = {}

        person_fields = [
            "person_id", "full_name", "first_name", "surname", "alias", "gender",
            "date_of_birth", "age", "name_region", "native_state", "native_city",
            "native_area", "home_location_id", "based_abroad_in", "person_type", "role",
            "syndicate_id", "syndicate_code", "risk_score", "influence_score",
            "custody_status", "first_offence_year", "total_cases",
            "is_cross_syndicate_bridge", "is_duplicate_record_of", "nic_ref",
            "record_source", "source_reliability", "info_credibility", "is_synthetic"]

        counts["persons"] = self._csv("nodes", "persons.csv", self.persons, person_fields)
        counts["organizations"] = self._csv("nodes", "organizations.csv", self.orgs)
        counts["locations"] = self._csv("nodes", "locations.csv", self.locations)
        counts["police_stations"] = self._csv("nodes", "police_stations.csv", self.police_stations)
        counts["phones"] = self._csv("nodes", "phones.csv", self.phones)
        counts["devices"] = self._csv("nodes", "devices.csv", self.devices)
        counts["bank_accounts"] = self._csv("nodes", "bank_accounts.csv", self.accounts)
        counts["vehicles"] = self._csv("nodes", "vehicles.csv", self.vehicles)
        counts["digital_identities"] = self._csv("nodes", "digital_identities.csv", self.digital_ids)
        counts["cases"] = self._csv("nodes", "cases.csv", self.cases)
        counts["incidents"] = self._csv("nodes", "incidents.csv", self.incidents)
        counts["seizures"] = self._csv("nodes", "seizures.csv", self.seizures)

        counts["person_person"] = self._csv("edges", "person_person.csv", self.pp_edges)
        counts["person_org"] = self._csv("edges", "person_organization.csv", self.person_org)
        counts["person_phone"] = self._csv("edges", "person_phone.csv", self.person_phone)
        counts["phone_device"] = self._csv("edges", "phone_device.csv", self.phone_device)
        counts["person_account"] = self._csv("edges", "person_account.csv", self.person_account)
        counts["person_vehicle"] = self._csv("edges", "person_vehicle.csv", self.person_vehicle)
        counts["person_location"] = self._csv("edges", "person_location.csv", self.person_location)
        counts["person_incident"] = self._csv("edges", "person_incident.csv", self.person_incident)
        counts["incident_vehicle"] = self._csv("edges", "incident_vehicle.csv", self.incident_vehicle)
        counts["colocations"] = self._csv("edges", "colocation_observations.csv", self.colocations)
        counts["cdr"] = getattr(self, "cdr_rows", 0)
        counts["transactions"] = getattr(self, "txn_rows", 0)

        # ground truth
        gt_members = [{"person_id": p["person_id"], "name": p["full_name"],
                       "syndicate_id": p["syndicate_id"],
                       "syndicate_code": p["syndicate_code"], "role": p["role"]}
                      for p in self.persons if p["person_type"] == "CRIMINAL"]
        counts["gt_syndicate_membership"] = self._csv("ground_truth",
                                                      "syndicate_membership.csv", gt_members)
        counts["gt_key_players"] = self._csv("ground_truth", "key_players.csv",
                                             self.gt_key_players)
        counts["gt_bridges"] = self._csv("ground_truth", "cross_syndicate_bridges.csv",
                                         self.gt_bridges)
        counts["gt_duplicates"] = self._csv("ground_truth", "duplicate_pairs.csv",
                                            self.gt_duplicates)
        counts["gt_anomalies"] = self._csv("ground_truth", "anomalies.csv", self.gt_anomalies)
        counts["gt_latent_links"] = self._csv("ground_truth", "latent_links.csv", self.gt_latent)

        # unstructured
        for dt, fname in (("FIR_NARRATIVE", "fir_narratives.jsonl"),
                          ("SURVEILLANCE_REPORT", "surveillance_reports.jsonl"),
                          ("INTELLIGENCE_NOTE", "intelligence_notes.jsonl")):
            subset = [d for d in self.narratives if d["doc_type"] == dt]
            path = os.path.join(self.out, "unstructured", fname)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                for d in subset:
                    fh.write(json.dumps(d, ensure_ascii=False) + "\n")
            counts[fname] = len(subset)

        # NER training file (doc_id, text, spans only)
        path = os.path.join(self.out, "ground_truth", "ner_annotations.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for d in self.narratives:
                fh.write(json.dumps({
                    "doc_id": d["doc_id"], "doc_type": d["doc_type"], "text": d["text"],
                    "entities": [[e["start"], e["end"], e["label"]] for e in d["entities"]],
                }, ensure_ascii=False) + "\n")
        counts["ner_annotations"] = len(self.narratives)

        # graph projection
        counts["graph_nodes"] = self._csv("graph", "graph_nodes.csv", self.graph_nodes)
        counts["graph_edges"] = self._csv("graph", "graph_edges.csv", self.graph_edges)
        self._write_cypher()

        # manifest
        label_counts = Counter()
        for d in self.narratives:
            for e in d["entities"]:
                label_counts[e["label"]] += 1
        manifest = {
            "dataset_name": "Synthetic Indian Criminal Network Dataset (SICND)",
            "version": "1.0",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "seed": self.seed,
            "synthetic": True,
            "disclaimer": ("Fully synthetic. No real person, organisation, phone number, "
                           "bank account or vehicle is represented. Geography and statute "
                           "sections are real only to make the data behave realistically."),
            "timeline": {"start": T_START.date().isoformat(), "end": T_END.date().isoformat()},
            "counts": counts,
            "syndicates": [{"code": s["syndicate_code"], "label": s["archetype_label"],
                            "members": s["member_count"], "hq": s["hq_city"],
                            "status": s["status"]} for s in self.syndicates],
            "ner_label_distribution": dict(label_counts.most_common()),
        }
        with open(os.path.join(self.out, "dataset_manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
        return manifest

    def _write_cypher(self):
        path = os.path.join(self.out, "graph", "neo4j_load.cypher")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cy = """// ---------------------------------------------------------------
// Neo4j bulk load for the Synthetic Indian Criminal Network Dataset
// Copy the CSVs under data/ into your Neo4j `import/` folder first.
// ---------------------------------------------------------------
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.person_id IS UNIQUE;
CREATE CONSTRAINT org_id    IF NOT EXISTS FOR (o:Organization) REQUIRE o.org_id IS UNIQUE;
CREATE CONSTRAINT loc_id    IF NOT EXISTS FOR (l:Location) REQUIRE l.location_id IS UNIQUE;
CREATE CONSTRAINT phone_id  IF NOT EXISTS FOR (p:Phone) REQUIRE p.phone_id IS UNIQUE;
CREATE CONSTRAINT acct_id   IF NOT EXISTS FOR (a:BankAccount) REQUIRE a.account_id IS UNIQUE;
CREATE CONSTRAINT veh_id    IF NOT EXISTS FOR (v:Vehicle) REQUIRE v.vehicle_id IS UNIQUE;
CREATE CONSTRAINT inc_id    IF NOT EXISTS FOR (i:Incident) REQUIRE i.incident_id IS UNIQUE;
CREATE CONSTRAINT dev_id    IF NOT EXISTS FOR (d:Device) REQUIRE d.device_id IS UNIQUE;

LOAD CSV WITH HEADERS FROM 'file:///persons.csv' AS r
CREATE (:Person {person_id:r.person_id, name:r.full_name, alias:r.alias,
  role:r.role, syndicate:r.syndicate_code, risk:toInteger(r.risk_score),
  influence:toFloat(r.influence_score), custody:r.custody_status,
  city:r.native_city, state:r.native_state, person_type:r.person_type});

LOAD CSV WITH HEADERS FROM 'file:///organizations.csv' AS r
CREATE (:Organization {org_id:r.org_id, name:r.name, org_type:r.org_type,
  city:r.hq_city, state:r.hq_state, status:r.status});

LOAD CSV WITH HEADERS FROM 'file:///locations.csv' AS r
CREATE (:Location {location_id:r.location_id, area:r.area, city:r.city,
  state:r.state, country:r.country, lat:toFloat(r.latitude), lon:toFloat(r.longitude)});

LOAD CSV WITH HEADERS FROM 'file:///phones.csv' AS r
CREATE (:Phone {phone_id:r.phone_id, msisdn:r.msisdn, operator:r.operator,
  burner:toInteger(r.is_burner), kyc:r.kyc_status});

LOAD CSV WITH HEADERS FROM 'file:///devices.csv' AS r
CREATE (:Device {device_id:r.device_id, imei:r.imei, make:r.make});

LOAD CSV WITH HEADERS FROM 'file:///bank_accounts.csv' AS r
CREATE (:BankAccount {account_id:r.account_id, account_number:r.account_number,
  bank:r.bank, mule:toInteger(r.is_mule_account), status:r.status});

LOAD CSV WITH HEADERS FROM 'file:///vehicles.csv' AS r
CREATE (:Vehicle {vehicle_id:r.vehicle_id, registration_no:r.registration_no,
  make:r.make, model:r.model});

LOAD CSV WITH HEADERS FROM 'file:///incidents.csv' AS r
CREATE (:Incident {incident_id:r.incident_id, fir_no:r.fir_no, crime:r.crime_type,
  severity:toInteger(r.severity), when:r.incident_datetime, city:r.city, state:r.state});

// ---- relationships -------------------------------------------------
LOAD CSV WITH HEADERS FROM 'file:///person_person.csv' AS r
MATCH (a:Person {person_id:r.src_person_id}), (b:Person {person_id:r.dst_person_id})
CALL apoc.create.relationship(a, r.relation,
  {strength:toFloat(r.strength), confidence:toFloat(r.confidence),
   verified:toInteger(r.is_verified), source:r.source_type}, b) YIELD rel
RETURN count(rel);

LOAD CSV WITH HEADERS FROM 'file:///person_phone.csv' AS r
MATCH (p:Person {person_id:r.person_id}), (h:Phone {phone_id:r.phone_id})
CREATE (p)-[:USES_PHONE {usage:r.usage_type}]->(h);

LOAD CSV WITH HEADERS FROM 'file:///phone_device.csv' AS r
MATCH (h:Phone {phone_id:r.phone_id}), (d:Device {device_id:r.device_id})
CREATE (h)-[:SIM_IN_DEVICE]->(d);

LOAD CSV WITH HEADERS FROM 'file:///person_account.csv' AS r
MATCH (p:Person {person_id:r.person_id}), (a:BankAccount {account_id:r.account_id})
CREATE (p)-[:CONTROLS_ACCOUNT {relation:r.relation}]->(a);

LOAD CSV WITH HEADERS FROM 'file:///person_incident.csv' AS r
MATCH (p:Person {person_id:r.person_id}), (i:Incident {incident_id:r.incident_id})
CREATE (p)-[:INVOLVED_IN {role:r.role_in_incident,
  arrested:toInteger(r.arrested)}]->(i);

// Aggregate CDR into weighted comm edges (raw CDR stays in cdr.csv)
LOAD CSV WITH HEADERS FROM 'file:///cdr.csv' AS r
MATCH (a:Phone {phone_id:r.caller_phone_id}), (b:Phone {phone_id:r.callee_phone_id})
MERGE (a)-[c:CALLED]->(b)
ON CREATE SET c.calls = 1, c.total_duration = toInteger(r.duration_sec)
ON MATCH  SET c.calls = c.calls + 1,
              c.total_duration = c.total_duration + toInteger(r.duration_sec);

LOAD CSV WITH HEADERS FROM 'file:///transactions.csv' AS r
MATCH (a:BankAccount {account_id:r.src_account_id}),
      (b:BankAccount {account_id:r.dst_account_id})
MERGE (a)-[t:TRANSFERRED_TO]->(b)
ON CREATE SET t.total = toInteger(r.amount_inr), t.count = 1
ON MATCH  SET t.total = t.total + toInteger(r.amount_inr), t.count = t.count + 1;

// ---- sample analyst queries ---------------------------------------
// 1) Who bridges two syndicates?
// MATCH (a:Person)-[]-(b:Person)
// WHERE a.syndicate <> b.syndicate AND a.syndicate <> '' AND b.syndicate <> ''
// RETURN a.name, a.syndicate, b.name, b.syndicate LIMIT 50;
//
// 2) One handset, two subscribers -> identity substitution
// MATCH (p1:Person)-[:USES_PHONE]->(:Phone)-[:SIM_IN_DEVICE]->(d:Device)
//       <-[:SIM_IN_DEVICE]-(:Phone)<-[:USES_PHONE]-(p2:Person)
// WHERE p1.person_id < p2.person_id
// RETURN d.imei, p1.name, p1.syndicate, p2.name, p2.syndicate;
//
// 3) Shortest path between two suspects across all evidence types
// MATCH p = shortestPath((a:Person {name:'...'})-[*..6]-(b:Person {name:'...'}))
// RETURN p;
"""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(cy)

    # ===================================================================
    #  RUN
    # ===================================================================
    def run(self):
        steps = [
            ("locations", self.build_locations),
            ("syndicates", self.build_syndicates),
            ("persons", self.build_persons),
            ("front companies", self.build_front_companies),
            ("identifiers", self.build_identifiers),
            ("person-person graph", self.build_person_person),
            ("cross-syndicate bridges", self.build_bridges),
            ("key players", self.build_key_players),
            ("incidents", self.build_incidents),
        ]
        for name, fn in steps:
            print(f"  -> {name} ...", flush=True)
            fn()

        os.makedirs(os.path.join(self.out, "edges"), exist_ok=True)
        print("  -> CDR ...", flush=True)
        self.build_cdr(os.path.join(self.out, "edges", "cdr.csv"))
        print("  -> transactions ...", flush=True)
        self.build_transactions(os.path.join(self.out, "edges", "transactions.csv"))
        print("  -> latent links ...", flush=True)
        self.build_latent_links()
        print("  -> duplicate records ...", flush=True)
        self.build_duplicates()
        print("  -> narratives + NER spans ...", flush=True)
        self.build_narratives()
        print("  -> graph projection ...", flush=True)
        self.build_graph_projection()
        print("  -> writing files ...", flush=True)
        return self.write_all()


# ===========================================================================
def main():
    ap = argparse.ArgumentParser(description="Synthetic Indian criminal-network dataset")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--criminals", type=int, default=1000)
    ap.add_argument("--peripheral", type=int, default=500)
    ap.add_argument("--incidents", type=int, default=2200)
    ap.add_argument("--cdr", type=int, default=200_000)
    ap.add_argument("--txn", type=int, default=60_000)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    a = ap.parse_args()

    print("=" * 72)
    print(" Synthetic Indian Criminal Network Dataset (SICND) -- generator")
    print(" 100% synthetic. No real individual is represented.")
    print("=" * 72)
    g = CrimeNetworkGenerator(seed=a.seed, n_criminals=a.criminals,
                              n_peripheral=a.peripheral, target_cdr=a.cdr,
                              target_txn=a.txn, n_incidents=a.incidents, out_dir=a.out)
    m = g.run()
    print("-" * 72)
    for k, v in m["counts"].items():
        print(f"  {k:<28} {v:>10,}")
    print("-" * 72)
    print(f"  Output: {g.out}")


if __name__ == "__main__":
    main()
