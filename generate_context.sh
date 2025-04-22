import json

INPUT_FILE = "flow - Formatted.json"
OUTPUT_FILE = "flow_with_contexts.json"

def attach_contexts(pg):
    if "variables" in pg and pg["variables"]:
        if "parameterContextName" in pg:
            pg["parameterContextName_auto"] = pg["name"]
        else:
            pg["parameterContextName"] = pg["name"]

    for child in pg.get("processGroups", []):
        attach_contexts(child)

with open(INPUT_FILE, "r") as f:
    flow = json.load(f)

# Start from rootGroup
if "rootGroup" in flow:
    attach_contexts(flow["rootGroup"])
else:
    raise KeyError("Could not find 'rootGroup' in the JSON structure")

with open(OUTPUT_FILE, "w") as f:
    json.dump(flow, f, indent=2)

print(f"[✔] Contexts added using 'parameterContextName'. Output saved to {OUTPUT_FILE}")
