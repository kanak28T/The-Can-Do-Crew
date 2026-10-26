import json
from pathlib import Path
import h3

ROOT = Path.cwd()
GRID = ROOT / "data" / "nagpur_h3_res9.geojson"
OUT = ROOT / "eval" / "scenarios"
HOLDOUT = OUT / "holdout"
GT = OUT / "ground_truth"

for p in (OUT, HOLDOUT, GT):
    p.mkdir(parents=True, exist_ok=True)

data = json.loads(GRID.read_text(encoding="utf-8"))
cells = []
for feature in data["features"]:
    cell = feature.get("properties", {}).get("cell")
    if cell and h3.is_valid_cell(cell) and h3.get_resolution(cell) == 9:
        if cell not in cells:
            cells.append(cell)

if len(cells) < 30:
    raise RuntimeError(f"Expected at least 30 valid H3 cells, found {len(cells)}")

cell_set = set(cells)

def zone(index, size=4):
    base = cells[index % len(cells)]
    nearby = [c for c in h3.grid_disk(base, 1) if c in cell_set]
    if len(nearby) < size:
        nearby = [base] + [c for c in cells if c != base]
    return nearby[:size]

def event(offset, domain, event_type, entity, cell, severity,
          source="official", raw=None):
    return {
        "offset": offset, "domain": domain, "event_type": event_type,
        "entity_id": entity, "h3_cell": cell, "severity": severity,
        "source_type": source, "raw_text": raw
    }

scenarios = [
{
"id":"SCN-A-001","family":"A","name":"Road closure and transit loss",
"description":"Road closure followed by transit suspension creates a local healthcare-access risk.",
"seed":101,"anchor":20,
"events":[
("T+0s","transport","road_closure","road_R14",0,.9,"official",None),
("T+30m","transport","transit_suspension","route_4",0,.85,"official","Bus route 4 suspended"),
("T+45m","transport","transit_suspension","route_4",1,.8,"crowdsourced","No buses on this road")],
"decoys":[("T+15m","power","voltage_drop","feeder_F07",8,.3,"sensor",None)],
"feed":[("T+1h","whole_domain","transport",.2)],
"contradiction":True
},
{
"id":"SCN-B-001","family":"B","name":"Feeder failure and water-pump outage",
"description":"Power feeder failure disables a water pump and leads to a local water-supply disruption.",
"seed":202,"anchor":100,
"events":[
("T+0s","power","feeder_failure","feeder_F12",0,.9,"sensor","Feeder power failure"),
("T+20m","water","pump_failure","pump_P03",1,.85,"sensor","Pump stopped after power loss"),
("T+40m","water","water_supply_loss","zone_W03",2,.9,"official","Water supply interrupted")],
"decoys":[("T+10m","transport","traffic_slowdown","road_R88",8,.25,"crowdsourced",None)],
"feed":[("T+1h","random_streams","water",.3)],
"contradiction":False
},
{
"id":"SCN-C-001","family":"C","name":"Communication dead zone and power stress",
"description":"Communication coverage drops while local power instability affects the same area.",
"seed":303,"anchor":200,
"events":[
("T+0s","communications","network_outage","tower_C04",0,.85,"sensor","Network unavailable"),
("T+15m","power","voltage_drop","feeder_F04",1,.75,"sensor","Voltage below normal"),
("T+35m","communications","service_degradation","tower_C04",2,.8,"crowdsourced","Calls and data failing")],
"decoys":[("T+20m","transport","road_closure","road_R91",8,.2,"official",None)],
"feed":[("T+45m","whole_domain","communications",.4)],
"contradiction":False
},
{
"id":"SCN-D-001","family":"D","name":"Construction isolates a low-income block",
"description":"Construction blocks access routes serving a vulnerable residential block; held-out zero-shot test.",
"seed":404,"anchor":300,
"events":[
("T+0s","transport","road_closure","road_C21",0,.8,"official","Construction closure"),
("T+25m","transport","route_blocked","route_B12",1,.8,"sensor","Access route blocked"),
("T+50m","healthcare","access_disruption","clinic_C02",2,.85,"crowdsourced","Clinic difficult to reach")],
"decoys":[("T+15m","power","voltage_drop","feeder_F19",8,.25,"sensor",None)],
"feed":[("T+1h","contiguous_area","transport",.25)],
"contradiction":False
},
{
"id":"SCN-E-001","family":"E","name":"Pump failure compounded by road closure",
"description":"A pump failure and road closure jointly delay water-service repair; held-out test.",
"seed":505,"anchor":400,
"events":[
("T+0s","water","pump_failure","pump_P11",0,.9,"sensor","Pump failure"),
("T+20m","transport","road_closure","road_R31",1,.85,"official","Repair access road closed"),
("T+45m","water","water_supply_loss","zone_W11",2,.9,"crowdsourced","Water unavailable"),
("T+1h","transport","route_blocked","route_R31",3,.8,"official","Repair route inaccessible")],
"decoys":[("T+10m","communications","service_degradation","tower_C09",8,.2,"sensor",None)],
"feed":[("T+1h","random_streams","water",.3)],
"contradiction":False
},
{
"id":"SCN-F-001","family":"F","name":"Official and crowd reports conflict",
"description":"Official reports and crowdsourced observations disagree; evaluate robustness under varied feed loss.",
"seed":606,"anchor":500,
"events":[
("T+0s","transport","road_closure","road_R44",0,.85,"official","Road reported closed"),
("T+15m","transport","road_open","road_R44",0,.2,"crowdsourced","Road appears open"),
("T+35m","transport","traffic_slowdown","road_R44",1,.6,"crowdsourced","Traffic still blocked")],
"decoys":[("T+20m","power","voltage_drop","feeder_F25",8,.25,"sensor",None)],
"feed":[("T+30m","random_streams","transport",.2),("T+1h","random_streams","transport",.4),("T+90m","random_streams","transport",.6)],
"contradiction":True
},
{
"id":"SCN-G-001","family":"G","name":"False-report spam in a quiet area",
"description":"Repeated low-credibility reports target a quiet area; the system should avoid a false high-risk zone.",
"seed":707,"anchor":600,
"events":[
("T+0s","public_safety","incident_report","report_spam_1",0,.15,"crowdsourced","Urgent incident reported"),
("T+5m","public_safety","incident_report","report_spam_2",1,.15,"crowdsourced","Another urgent incident"),
("T+10m","public_safety","incident_report","report_spam_3",2,.1,"crowdsourced","Repeated unverified report"),
("T+15m","public_safety","incident_report","report_spam_4",3,.1,"crowdsourced","Repeated unverified report")],
"decoys":[("T+30m","transport","traffic_slowdown","road_R76",8,.2,"sensor",None)],
"feed":[("T+30m","random_streams","public_safety",.1)],
"contradiction":False
},
{
"id":"SCN-H-001","family":"H","name":"Healthcare desert and warning dead zone",
"description":"Limited healthcare access overlaps a communications dead zone that prevents warnings reaching residents.",
"seed":808,"anchor":700,
"events":[
("T+0s","healthcare","facility_unavailable","clinic_H02",0,.8,"official","Local clinic unavailable"),
("T+20m","communications","network_outage","tower_H03",1,.85,"sensor","Warning coverage lost"),
("T+40m","healthcare","access_disruption","hospital_H01",2,.8,"crowdsourced","Long travel time to care")],
"decoys":[("T+15m","power","voltage_drop","feeder_F33",8,.2,"sensor",None)],
"feed":[("T+1h","whole_domain","communications",.3)],
"contradiction":False
},
{
"id":"SCN-ADV-001","family":"ADV","name":"Adversarial decoy cluster",
"description":"A dense cluster of noisy reports is deliberately separated from the true high-risk zone.",
"seed":909,"anchor":900,
"events":[
("T+0s","transport","road_closure","road_A01",0,.8,"official","Road closure"),
("T+10m","water","water_supply_loss","zone_A01",1,.8,"official","Water outage"),
("T+15m","public_safety","incident_report","report_A01",8,.2,"crowdsourced","Unverified report"),
("T+17m","public_safety","incident_report","report_A02",8,.2,"crowdsourced","Unverified report"),
("T+19m","public_safety","incident_report","report_A03",8,.2,"crowdsourced","Unverified report"),
("T+21m","public_safety","incident_report","report_A04",8,.2,"crowdsourced","Unverified report")],
"decoys":[("T+25m","power","voltage_drop","feeder_A99",9,.2,"sensor",None)],
"feed":[("T+1h","random_streams","transport",.2)],
"contradiction":False
},
{
"id":"SCN-ADV-002","family":"ADV","name":"Sparse hidden hotspot",
"description":"The true zone has sparse early evidence while unrelated cells receive more noisy events.",
"seed":1010,"anchor":1100,
"events":[
("T+0s","water","pump_failure","pump_ADV2",0,.75,"sensor","Pump fault"),
("T+40m","healthcare","access_disruption","clinic_ADV2",1,.8,"crowdsourced","Access disrupted"),
("T+5m","public_safety","incident_report","noise_1",8,.2,"crowdsourced","Unverified report"),
("T+8m","public_safety","incident_report","noise_2",9,.2,"crowdsourced","Unverified report"),
("T+12m","public_safety","incident_report","noise_3",10,.2,"crowdsourced","Unverified report")],
"decoys":[("T+20m","transport","traffic_slowdown","road_ADV99",11,.2,"sensor",None)],
"feed":[("T+30m","random_streams","water",.2)],
"contradiction":False
}
]

# Add I/O-independent family test variants for A, B, C.
for family, base_idx, name, events in [
("A",1200,"Road and transit in-family test",[
("T+0s","transport","road_closure","road_R22",0,.85,"official","Road closed"),
("T+25m","transport","transit_suspension","route_7",1,.8,"official","Route suspended")]),
("B",1300,"Power and water in-family test",[
("T+0s","power","feeder_failure","feeder_F18",0,.85,"sensor","Feeder fault"),
("T+25m","water","pump_failure","pump_P08",1,.8,"sensor","Pump stopped")]),
("C",1400,"Communication and power in-family test",[
("T+0s","communications","network_outage","tower_C12",0,.8,"sensor","Network outage"),
("T+25m","power","voltage_drop","feeder_F20",1,.7,"sensor","Voltage drop")])]:
    scenarios.append({
        "id":f"SCN-{family}-00{2 if family=='A' else 2}",
        "family":family,"name":name,
        "description":"In-family evaluation replay with a fixed seed.",
        "seed":base_idx,"anchor":base_idx,
        "events":events,"decoys":[("T+15m","transport","traffic_slowdown","road_TEST",8,.2,"sensor",None)],
        "feed":[],"contradiction":False
    })

# Keep exactly one A/B/C scenario each in this initial pack; append test variants
# using unique IDs.
seen = {}
for s in scenarios:
    fam = s["family"]
    seen[fam] = seen.get(fam, 0) + 1
    if seen[fam] > 1 and fam in ("A","B","C"):
        s["id"] = f"SCN-{fam}-002"

written = []
for s in scenarios:
    cells_zone = zone(s["anchor"], 4)
    def idx(i):
        return cells_zone[i % len(cells_zone)]
    causal = [event(o,d,t,e,idx(ci),sev,src,raw)
              for o,d,t,e,ci,sev,src,raw in s["events"]]
    decoys = [event(o,d,t,e,cells[(s["anchor"]+ci) % len(cells)],sev,src,raw)
              for o,d,t,e,ci,sev,src,raw in s["decoys"]]
    scenario = {
        "scenario_id": s["id"], "family": s["family"], "name": s["name"],
        "description": s["description"], "seed": s["seed"],
        "time_compression_factor": 60,
        "events": causal, "decoys": decoys,
        "feed_loss": [
            {"offset":o,"pattern":p,"domain":d,"fraction":f}
            for o,p,d,f in s["feed"]
        ],
        "contradictions": []
    }
    if s["contradiction"]:
        scenario["contradictions"] = [{
            "offset":"T+2h",
            "conflicting_event": event("T+2h","transport","road_open",
                "road_R14",idx(0),.1,"official",None)
        }]
    holdout = s["family"] in ("D","E","ADV")
    path = (HOLDOUT if holdout else OUT) / f"{s['id'].replace('SCN-','').replace('-001','').replace('-002','').lower()}_{s['name'].lower().replace(' ','_').replace('+','and').replace('/','_')[:38]}.yaml"
    # Use stable, unambiguous filenames.
    file_names = {
        "SCN-A-001":"A_road_transit.yaml","SCN-A-002":"A_in_family_test.yaml",
        "SCN-B-001":"B_power_water.yaml","SCN-B-002":"B_in_family_test.yaml",
        "SCN-C-001":"C_comms_power.yaml","SCN-C-002":"C_in_family_test.yaml",
        "SCN-D-001":"D_construction_isolation.yaml",
        "SCN-E-001":"E_pump_road_cascade.yaml",
        "SCN-F-001":"F_official_crowd_conflict.yaml",
        "SCN-G-001":"G_false_report_spam.yaml",
        "SCN-H-001":"H_healthcare_warning_gap.yaml",
        "SCN-ADV-001":"adversarial_1_false_cluster.yaml",
        "SCN-ADV-002":"adversarial_2_hidden_hotspot.yaml"
    }
    path = (HOLDOUT if holdout else OUT) / file_names[s["id"]]
    path.write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8")

    truth = {
        "scenario_id": s["id"],
        "ground_truth": {
            "polygon_h3_cells": cells_zone,
            "zone_label": "High",
            "evaluation_window": {"start_offset":"T+1h","end_offset":"T+4h"},
            "notes": "Synthetic evaluation zone selected from valid Nagpur grid cells; not real-world ground truth."
        },
        "scoring": {
            "primary_metric":"iou",
            "secondary_metrics":["precision","recall","zone_hit_rate","detection_latency_seconds"],
            "iou_threshold":0.5
        }
    }
    (GT / f"{s['id']}.yaml").write_text(json.dumps(truth, indent=2) + "\n", encoding="utf-8")
    written.append((s["id"], str(path.relative_to(ROOT))))

print(f"Valid grid cells: {len(cells)}")
print(f"Scenario files created: {len(written)}")
for sid, path in written:
    print(f"{sid}: {path}")
print(f"Ground-truth files created: {len(written)} in {GT.relative_to(ROOT)}")
print("Note: JSON syntax is valid YAML. Ground truth is stored separately.")
