import json

INPUT_FILE = "flow - Formatted.json"
OUTPUT_FILE = "flow_with_contexts.json"

def attach_contexts(pg):
    if "variables" in pg and pg["variables"]:
        if "parameterContext" in pg:
            pg["parameterContext_auto"] = { "name": pg["name"] }
        else:
            pg["parameterContext"] = { "name": pg["name"] }

    for child in pg.get("processGroups", []):
        attach_contexts(child)

with open(INPUT_FILE, "r") as f:
    flow = json.load(f)

# Recursively process .rootGroup
if "rootGroup" in flow:
    attach_contexts(flow["rootGroup"])
else:
    raise KeyError("Could not find 'rootGroup' in the JSON structure")

with open(OUTPUT_FILE, "w") as f:
    json.dump(flow, f, indent=2)

print(f"[✔] Contexts added. Output written to {OUTPUT_FILE}")
