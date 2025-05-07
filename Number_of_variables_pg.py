import json
import sys
import re
from collections import defaultdict

# -------------------- Setup --------------------
output_file = "flow_variables_converted.json"
summary_file = "replaced_variables_summary.json"

if len(sys.argv) != 2:
    print("Usage: python scoped_replace.py <nifi_1.17_flow.json>")
    sys.exit(1)

input_path = sys.argv[1]

with open(input_path, 'r') as f:
    flow_data = json.load(f)

replaced_vars = defaultdict(set)

# -------------------- Replace Helpers --------------------

def replace_in_properties(props, var_names, source_pg_name):
    if not isinstance(props, dict):
        return
    for key, val in props.items():
        if isinstance(val, str):
            for var in var_names:
                pattern = r'\$\{\s*' + re.escape(var) + r'\s*\}'
                if re.search(pattern, val):
                    print(f"[DEBUG] Found '${{{var}}}' in '{key}' of PG '{source_pg_name}'")
                new_val, count = re.subn(pattern, f'#{{{var}}}', val)
                if count > 0:
                    props[key] = new_val
                    replaced_vars[source_pg_name].add(var)
                    print(f"[INFO] Replaced '${{{var}}}' → '#{{{var}}}' in '{key}' of PG '{source_pg_name}'")

def apply_replacement_in_pg_tree(group, var_names, source_pg_name):
    # Processors
    for processor in group.get("processors", []):
        replace_in_properties(processor.get("config", {}).get("properties", {}), var_names, source_pg_name)

    # Controller Services
    for service in group.get("controllerServices", []):
        replace_in_properties(service.get("properties", {}), var_names, source_pg_name)

    # Recurse into children
    for child_pg in group.get("processGroups", []):
        apply_replacement_in_pg_tree(child_pg, var_names, source_pg_name)

# -------------------- Traversal --------------------

def traverse_pg(group, inherited_vars):
    pg_name = group.get("name", f"Unnamed_{group.get('identifier', '')[:6]}")
    local_vars = set(group.get("variables", {}).keys())
    available_vars = inherited_vars.union(local_vars)

    # Replace in processors
    for processor in group.get("processors", []):
        props = processor.get("properties", {})  # ✅ FIXED LINE
        replace_in_properties(props, available_vars, pg_name)

    # Recurse into nested PGs
    for child_pg in group.get("processGroups", []):
        traverse_pg(child_pg, available_vars)

# -------------------- Execute --------------------

if "rootGroup" not in flow_data:
    raise KeyError("No 'rootGroup' found in JSON.")

root = flow_data["rootGroup"]
traverse_all_groups(root)

# -------------------- Save Output --------------------

with open(output_file, 'w') as f:
    json.dump(flow_data, f, indent=2)
print(f"[✔] Updated flow saved to '{output_file}'")

summary = {pg: sorted(list(vars)) for pg, vars in replaced_vars.items()}
with open(summary_file, 'w') as f:
    json.dump(summary, f, indent=2)
print(f"[✔] Replacement summary saved to '{summary_file}'")
