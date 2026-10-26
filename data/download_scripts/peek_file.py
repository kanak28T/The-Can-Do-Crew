import json, sys, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def peek(path):
    txt = open(path, encoding="utf-8").read()
    d = json.loads(txt)
    print("==", path, f"({len(txt):,} chars)")
    words = [w for w in ("synthetic", "SYNTHETIC", "simulated", "placeholder", "license", "source") if w in txt]
    print("mentions:", words or "none of synthetic/simulated/placeholder/license/source")
    if isinstance(d, dict) and d.get("type") == "FeatureCollection":
        fs = d["features"]
        types = collections.Counter(f["geometry"]["type"] for f in fs if f.get("geometry"))
        keys = sorted({k for f in fs for k in f.get("properties", {})})
        print(f"GeoJSON: {len(fs)} features; geometry {dict(types)}; properties {keys}")
        for f in fs[:2]:
            print("  e.g.", {k: f["properties"][k] for k in list(f["properties"])[:6]})
    elif isinstance(d, dict):
        print("dict, keys:", list(d)[:8], "| total", len(d))
        for k in list(d)[:3]:
            print(" ", repr(k), "->", str(d[k])[:160])
        if "meta" in d:
            print("meta:", str(d["meta"])[:400])
    elif isinstance(d, list):
        print("list of", len(d))
        for x in d[:3]:
            print(" ", str(x)[:160])

for p in sys.argv[1:]:
    peek(p)