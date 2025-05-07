import json
import sys
import re
from collections import defaultdict

# -------------------- Output Settings --------------------
output_file = "flow_variables_converted.json"
summary_file = "replaced_variables_summary.json"

# -------------------- Load Input --------------------
if len(sys.argv) != 2:
    print("Usage: python scoped_replace.py <nifi_1.17_flow.json>")
    sys.exit(1)

input_path = sys.argv[1]

with open(input_path, 'r') as f:
    flow_data = json.load(f)

# -------------------- Replacement Tracking --------------------
replaced_vars = defaultdict(set)

def replace_in_properties(props, available_vars, pg_name):
    if not isinstance(props, dict):
        return
    for key, val in props.items():
        if isinstance(val, str):
            for var in available_vars:
                pattern = r'\$\{\s*' + re.escape(var) + r'\s*\}'
                new_val, count = re.subn(pattern, f'#{{{var}}}', val)
                if count > 0:
                    props[key] = new_val
                    replaced_vars[pg_name].add(var)
                    print(f"[INFO] In PG '{pg_name}': replaced '${{{var}}}' → '#{{{var}}}' in property '{key}'")

# -------------------- Traversal Logic --------------------

def traverse_pg(group, inherited_vars):
    pg_name = group.get("name", f"Unnamed_{group.get('identifier', '')[:6]}")
    local_vars = set(group.get("variables", {}).keys())
    available_vars = inherited_vars.union(local_vars)

    # Replace in processors
    for processor in group.get("processors", []):
        props = processor.get("properties", {})  # ✅ Your actual structure
        replace_in_properties(props, available_vars, pg_name)

    # Replace in controller services (if any)
    for service in group.get("controllerServices", []):
        replace_in_properties(service.get("properties", {}), available_vars, pg_name)

    # Recurse into nested PGs
    for child_pg in group.get("processGroups", []):
        traverse_pg(child_pg, available_vars)

# -------------------- Run --------------------

if "rootGroup" not in flow_data:
    raise KeyError("Missing 'rootGroup' in flow definition.")

print("[*] Starting replacement from rootGroup...")
root = flow_data["rootGroup"]
traverse_pg(root, set())

# -------------------- Save Output --------------------

with open(output_file, 'w') as f:
    json.dump(flow_data, f, indent=2)
print(f"[✔] Flow file saved to: {output_file}")

summary = {pg: sorted(list(vars)) for pg, vars in replaced_vars.items()}
with open(summary_file, 'w') as f:
    json.dump(summary, f, indent=2)
print(f"[✔] Replacement summary saved to: {summary_file}")
