// ---------------------------------------------------------------
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
