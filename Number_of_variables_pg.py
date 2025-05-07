import json
import sys
import re
from collections import defaultdict

# -------------------- Config --------------------
output_file = "flow_variables_converted.json"
summary_file = "replaced_variables_summary.json"

if len(sys.argv) != 2:
    print("Usage: python scoped_replace.py <nifi_1.17_flow.json>")
    sys.exit(1)

input_path = sys.argv[1]

with open(input_path, 'r') as f:
    flow_data = json.load(f)

# -------------------- Helpers --------------------

replaced_vars = defaultdict(set)

def replace_in_properties(props, var_names, source_pg_name):
    if not isinstance(props, dict):
        return
    for key, val in props.items():
        if isinstance(val, str):
            for var in var_names:
                pattern = r'\$\{\s*' + re.escape(var) + r'\s*\}'
                new_val, count = re.subn(pattern, f'#{{{var}}}', val)
                if count > 0:
                    props[key] = new_val
                    replaced_vars[source_pg_name].add(var)

def replace_vars_in_pg_tree(group, var_names, source_pg_name):
    # Replace in processors
    for processor in group.get("processors", []):
        replace_in_properties(
            processor.get("config", {}).get("properties", {}),
            var_names,
            source_pg_name
        )

    # Replace in controller services
    for service in group.get("controllerServices", []):
        replace_in_properties(
            service.get("properties", {}),
            var_names,
            source_pg_name
        )

    # Recurse into children
    for child in group.get("processGroups", []):
        replace_vars_in_pg_tree(child, var_names, source_pg_name)

def traverse_scoped_replacement(group):
    pg_name = group.get("name", f"Unnamed_{group.get('identifier', '')[:6]}")
    vars_dict = group.get("variables", {})

    if vars_dict:
        var_names = list(vars_dict.keys())
        # Replace in this PG and all its children using its own variables
        replace_vars_in_pg_tree(group, var_names, pg_name)

    # Always keep going into children to check if they define variables
    for child in group.get("processGroups", []):
        traverse_scoped_replacement(child)

# -------------------- Main --------------------

if "rootGroup" not in flow_data:
    raise KeyError("Could not find 'rootGroup' in the JSON structure.")

print("[*] Traversing and replacing variables scoped to PG + children...")
root = flow_data["rootGroup"]
traverse_scoped_replacement(root)

# -------------------- Save --------------------

with open(output_file, 'w') as f:
    json.dump(flow_data, f, indent=2)
print(f"[✔] Updated flow saved to: {output_file}")

summary = {pg: sorted(vars) for pg, vars in replaced_vars.items()}
with open(summary_file, 'w') as f:
    json.dump(summary, f, indent=2)
print(f"[✔] Replacement summary saved to: {summary_file}")
