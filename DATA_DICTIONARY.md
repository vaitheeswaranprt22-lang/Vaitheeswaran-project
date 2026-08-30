# Data Dictionary — SICND

Auto-generated from the shipped dataset. Every table is UTF-8 CSV with a header row.
All `*_id` columns are stable primary keys; joins are on exact string match.


## `data/nodes/`

### `bank_accounts.csv` — 2,071 rows

| # | column |
|---|---|
| 1 | `account_id` |
| 2 | `account_number` |
| 3 | `ifsc` |
| 4 | `bank` |
| 5 | `branch_city` |
| 6 | `branch_state` |
| 7 | `holder_person_id` |
| 8 | `holder_org_id` |
| 9 | `holder_name` |
| 10 | `account_type` |
| 11 | `opened_date` |
| 12 | `status` |
| 13 | `is_mule_account` |
| 14 | `kyc_risk_rating` |

### `cases.csv` — 157 rows

| # | column |
|---|---|
| 1 | `case_id` |
| 2 | `case_title` |
| 3 | `primary_crime` |
| 4 | `lead_agency` |
| 5 | `syndicate_id` |
| 6 | `syndicate_code` |
| 7 | `opened_date` |
| 8 | `status` |
| 9 | `priority` |

### `devices.csv` — 1,811 rows

| # | column |
|---|---|
| 1 | `device_id` |
| 2 | `imei` |
| 3 | `make` |
| 4 | `model` |
| 5 | `is_dual_sim` |
| 6 | `first_seen` |

### `digital_identities.csv` — 712 rows

| # | column |
|---|---|
| 1 | `digital_id` |
| 2 | `person_id` |
| 3 | `platform` |
| 4 | `handle` |
| 5 | `email` |
| 6 | `first_seen` |
| 7 | `is_anonymous_profile` |

### `incidents.csv` — 2,200 rows

| # | column |
|---|---|
| 1 | `incident_id` |
| 2 | `fir_no` |
| 3 | `case_id` |
| 4 | `crime_type` |
| 5 | `ipc_section` |
| 6 | `bns_section` |
| 7 | `severity` |
| 8 | `bailable` |
| 9 | `ps_id` |
| 10 | `ps_name` |
| 11 | `location_id` |
| 12 | `area` |
| 13 | `city` |
| 14 | `state` |
| 15 | `latitude` |
| 16 | `longitude` |
| 17 | `incident_datetime` |
| 18 | `reported_datetime` |
| 19 | `investigating_agency` |
| 20 | `syndicate_id` |
| 21 | `syndicate_code` |
| 22 | `status` |
| 23 | `loss_or_value_inr` |
| 24 | `n_accused` |
| 25 | `source_reliability` |

### `locations.csv` — 137 rows

| # | column |
|---|---|
| 1 | `location_id` |
| 2 | `area` |
| 3 | `city` |
| 4 | `state` |
| 5 | `country` |
| 6 | `latitude` |
| 7 | `longitude` |
| 8 | `place_type` |
| 9 | `is_border_point` |
| 10 | `is_hotspot` |

### `organizations.csv` — 108 rows

| # | column |
|---|---|
| 1 | `org_id` |
| 2 | `name` |
| 3 | `org_type` |
| 4 | `syndicate_code` |
| 5 | `archetype_label` |
| 6 | `parent_syndicate_id` |
| 7 | `hq_location_id` |
| 8 | `hq_city` |
| 9 | `hq_state` |
| 10 | `operating_states` |
| 11 | `foreign_links` |
| 12 | `primary_crimes` |
| 13 | `member_count` |
| 14 | `active_since` |
| 15 | `status` |
| 16 | `threat_level` |

### `persons.csv` — 1,696 rows

| # | column |
|---|---|
| 1 | `person_id` |
| 2 | `full_name` |
| 3 | `first_name` |
| 4 | `surname` |
| 5 | `alias` |
| 6 | `gender` |
| 7 | `date_of_birth` |
| 8 | `age` |
| 9 | `name_region` |
| 10 | `native_state` |
| 11 | `native_city` |
| 12 | `native_area` |
| 13 | `home_location_id` |
| 14 | `based_abroad_in` |
| 15 | `person_type` |
| 16 | `role` |
| 17 | `syndicate_id` |
| 18 | `syndicate_code` |
| 19 | `risk_score` |
| 20 | `influence_score` |
| 21 | `custody_status` |
| 22 | `first_offence_year` |
| 23 | `total_cases` |
| 24 | `is_cross_syndicate_bridge` |
| 25 | `is_duplicate_record_of` |
| 26 | `nic_ref` |
| 27 | `record_source` |
| 28 | `source_reliability` |
| 29 | `info_credibility` |
| 30 | `is_synthetic` |

### `phones.csv` — 3,223 rows

| # | column |
|---|---|
| 1 | `phone_id` |
| 2 | `msisdn` |
| 3 | `operator` |
| 4 | `circle` |
| 5 | `subscriber_person_id` |
| 6 | `subscriber_name_on_record` |
| 7 | `kyc_status` |
| 8 | `activation_date` |
| 9 | `deactivation_date` |
| 10 | `is_burner` |
| 11 | `imsi` |

### `police_stations.csv` — 125 rows

| # | column |
|---|---|
| 1 | `ps_id` |
| 2 | `ps_name` |
| 3 | `short_name` |
| 4 | `city` |
| 5 | `state` |
| 6 | `jurisdiction_location_id` |

### `seizures.csv` — 1,055 rows

| # | column |
|---|---|
| 1 | `seizure_id` |
| 2 | `incident_id` |
| 3 | `item_category` |
| 4 | `item` |
| 5 | `quantity` |
| 6 | `unit` |
| 7 | `estimated_value_inr` |
| 8 | `seized_from_person_id` |

### `vehicles.csv` — 338 rows

| # | column |
|---|---|
| 1 | `vehicle_id` |
| 2 | `registration_no` |
| 3 | `make` |
| 4 | `model` |
| 5 | `colour` |
| 6 | `vehicle_class` |
| 7 | `registered_state` |
| 8 | `owner_person_id` |
| 9 | `owner_name_on_record` |
| 10 | `registration_date` |
| 11 | `is_fake_plate` |
| 12 | `chassis_tampered` |

## `data/edges/`

### `cdr.csv` — 200,000 rows

| # | column |
|---|---|
| 1 | `cdr_id` |
| 2 | `caller_phone_id` |
| 3 | `callee_phone_id` |
| 4 | `caller_msisdn` |
| 5 | `callee_msisdn` |
| 6 | `caller_person_id` |
| 7 | `callee_person_id` |
| 8 | `timestamp` |
| 9 | `duration_sec` |
| 10 | `call_type` |
| 11 | `cell_id` |
| 12 | `location_id` |
| 13 | `imei` |
| 14 | `roaming_flag` |

### `colocation_observations.csv` — 120 rows

| # | column |
|---|---|
| 1 | `colocation_id` |
| 2 | `person_a` |
| 3 | `person_b` |
| 4 | `location_id` |
| 5 | `area` |
| 6 | `city` |
| 7 | `observed_on` |
| 8 | `time_gap_minutes` |
| 9 | `source_type` |
| 10 | `confidence` |

### `incident_vehicle.csv` — 713 rows

| # | column |
|---|---|
| 1 | `incident_id` |
| 2 | `vehicle_id` |
| 3 | `registration_no` |
| 4 | `involvement` |

### `person_account.csv` — 2,099 rows

| # | column |
|---|---|
| 1 | `person_id` |
| 2 | `account_id` |
| 3 | `relation` |
| 4 | `from_date` |
| 5 | `to_date` |

### `person_incident.csv` — 11,570 rows

| # | column |
|---|---|
| 1 | `incident_id` |
| 2 | `person_id` |
| 3 | `person_name` |
| 4 | `role_in_incident` |
| 5 | `arrested` |
| 6 | `chargesheeted` |
| 7 | `arrest_date` |

### `person_location.csv` — 6,446 rows

| # | column |
|---|---|
| 1 | `person_id` |
| 2 | `location_id` |
| 3 | `association` |
| 4 | `observed_on` |
| 5 | `source_type` |
| 6 | `confidence` |

### `person_organization.csv` — 1,067 rows

| # | column |
|---|---|
| 1 | `person_id` |
| 2 | `org_id` |
| 3 | `role_in_org` |
| 4 | `from_date` |
| 5 | `to_date` |
| 6 | `is_benami` |

### `person_person.csv` — 2,980 rows

| # | column |
|---|---|
| 1 | `edge_id` |
| 2 | `src_person_id` |
| 3 | `src_name` |
| 4 | `dst_person_id` |
| 5 | `dst_name` |
| 6 | `relation` |
| 7 | `subtype` |
| 8 | `since` |
| 9 | `strength` |
| 10 | `confidence` |
| 11 | `source_type` |
| 12 | `is_verified` |

### `person_phone.csv` — 3,269 rows

| # | column |
|---|---|
| 1 | `person_id` |
| 2 | `phone_id` |
| 3 | `usage_type` |
| 4 | `from_date` |
| 5 | `to_date` |
| 6 | `confidence` |

### `person_vehicle.csv` — 338 rows

| # | column |
|---|---|
| 1 | `person_id` |
| 2 | `vehicle_id` |
| 3 | `relation` |
| 4 | `from_date` |
| 5 | `to_date` |
| 6 | `confidence` |

### `phone_device.csv` — 3,293 rows

| # | column |
|---|---|
| 1 | `phone_id` |
| 2 | `device_id` |
| 3 | `imei` |
| 4 | `msisdn` |
| 5 | `first_seen` |
| 6 | `last_seen` |

### `transactions.csv` — 60,000 rows

| # | column |
|---|---|
| 1 | `txn_id` |
| 2 | `src_account_id` |
| 3 | `dst_account_id` |
| 4 | `src_account_no` |
| 5 | `dst_account_no` |
| 6 | `src_person_id` |
| 7 | `dst_person_id` |
| 8 | `amount_inr` |
| 9 | `channel` |
| 10 | `timestamp` |
| 11 | `narration` |
| 12 | `is_cash` |
| 13 | `branch_city` |
| 14 | `flagged_by_bank` |

## `data/ground_truth/`

### `anomalies.csv` — 387 rows

| # | column |
|---|---|
| 1 | `anomaly_id` |
| 2 | `pattern` |
| 3 | `entity_type` |
| 4 | `entity_ids` |
| 5 | `linked_incident_id` |
| 6 | `window_start` |
| 7 | `window_end` |
| 8 | `description` |
| 9 | `detect_with` |

### `cross_syndicate_bridges.csv` — 22 rows

| # | column |
|---|---|
| 1 | `person_id` |
| 2 | `name` |
| 3 | `alias` |
| 4 | `role` |
| 5 | `home_syndicate` |
| 6 | `bridged_syndicates` |
| 7 | `bridge_type` |
| 8 | `why_it_matters` |

### `duplicate_pairs.csv` — 196 rows

| # | column |
|---|---|
| 1 | `record_a` |
| 2 | `name_a` |
| 3 | `dob_a` |
| 4 | `record_b` |
| 5 | `name_b` |
| 6 | `dob_b` |
| 7 | `is_same_person` |
| 8 | `variant_type` |
| 9 | `shared_signals` |
| 10 | `shared_phone` |
| 11 | `correct_action` |

### `key_players.csv` — 85 rows

| # | column |
|---|---|
| 1 | `person_id` |
| 2 | `name` |
| 3 | `alias` |
| 4 | `syndicate_code` |
| 5 | `key_player_type` |
| 6 | `expected_signal` |
| 7 | `influence_score` |

### `latent_links.csv` — 211 rows

| # | column |
|---|---|
| 1 | `latent_id` |
| 2 | `person_a` |
| 3 | `person_a_name` |
| 4 | `person_b` |
| 5 | `person_b_name` |
| 6 | `syndicate_a` |
| 7 | `syndicate_b` |
| 8 | `mechanism` |
| 9 | `evidence_id` |
| 10 | `note` |
| 11 | `detect_with` |

### `syndicate_membership.csv` — 1,196 rows

| # | column |
|---|---|
| 1 | `person_id` |
| 2 | `name` |
| 3 | `syndicate_id` |
| 4 | `syndicate_code` |
| 5 | `role` |

## `data/graph/`

### `graph_edges.csv` — 112,303 rows

| # | column |
|---|---|
| 1 | `src` |
| 2 | `dst` |
| 3 | `edge_type` |
| 4 | `weight` |
| 5 | `attributes` |

### `graph_nodes.csv` — 11,741 rows

| # | column |
|---|---|
| 1 | `node_id` |
| 2 | `node_type` |
| 3 | `label` |
| 4 | `attributes` |


## `data/unstructured/` (JSON Lines)

### `fir_narratives.jsonl` — 2,200 documents

Keys: `doc_id`, `doc_type`, `incident_id`, `case_id`, `fir_no`, `police_station`, `district`, `state`, `crime_type`, `recorded_on`, `language`, `source_type`, `source_reliability`, `text`, `entities`, `linked_person_ids`

`entities` is a list of `{start, end, text, label, entity_id}`; `text[start:end] == text` is guaranteed.

### `surveillance_reports.jsonl` — 600 documents

Keys: `doc_id`, `doc_type`, `incident_id`, `case_id`, `fir_no`, `police_station`, `district`, `state`, `crime_type`, `recorded_on`, `language`, `source_type`, `source_reliability`, `text`, `entities`, `linked_person_ids`

`entities` is a list of `{start, end, text, label, entity_id}`; `text[start:end] == text` is guaranteed.

### `intelligence_notes.jsonl` — 420 documents

Keys: `doc_id`, `doc_type`, `incident_id`, `case_id`, `fir_no`, `police_station`, `district`, `state`, `crime_type`, `recorded_on`, `language`, `source_type`, `source_reliability`, `text`, `entities`, `linked_person_ids`

`entities` is a list of `{start, end, text, label, entity_id}`; `text[start:end] == text` is guaranteed.

### `ground_truth/ner_annotations.jsonl` — 3,220 documents

Training-ready form: `{doc_id, doc_type, text, entities}` where `entities` is `[[start, end, label], ...]` (spaCy/HF compatible).

**Labels:** PERSON, ALIAS, ORG, GPE, LOC, PHONE, ACCOUNT, VEHICLE_REG, VEHICLE_MODEL, MONEY, DATE, CONTRABAND, QUANTITY, POLICE_STATION, AGENCY.
