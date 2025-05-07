import json
import sys
import re
from collections import defaultdict

# ----------------------------- Settings -----------------------------
output_file = "flow_variables_converted.json"
summary_file = "replaced_variables_summary.json"

if len(sys.argv) != 2:
    print("Usage: python replace_pg_scoped_variables.py <nifi_1.17_flow.json>")
    sys.exit(1)

input_path = sys.argv[1]

with open(input_path, 'r') as f:
    flow_data = json.load(f)

# --------------------------- Utility ------------------------

def replace_in_properties(props, variables, replaced_vars, pg_name):
    if not isinstance(props, dict):
        return
    for key, val in props.items():
        if isinstance(val, str):
            for var in variables:
                new_val, count = re.subn(fr'\$\{{\s*' + re.escape(var) + r'\s*\}}', f'#{{{var}}}', val)
                if count > 0:
                    props[key] = new_val
                    replaced_vars[pg_name].add(var)

def replace_in_pg_and_children(group, scoped_vars, replaced_vars, parent_pg_name):
    # Replace in processors
    for processor in group.get("processors", []):
        replace_in_properties(
            processor.get("config", {}).get("properties", {}),
            scoped_vars,
            replaced_vars,
            parent_pg_name
        )

    # Replace in controller services
    for service in group.get("controllerServices", []):
        replace_in_properties(
            service.get("properties", {}),
            scoped_vars,
            replaced_vars,
            parent_pg_name
        )

    # Recurse into children
    for child in group.get("processGroups", []):
        replace_in_pg_and_children(child, scoped_vars, replaced_vars, parent_pg_name)

# --------------------------- Core Logic ------------------------

replaced_vars = defaultdict(set)

def traverse_parent_groups(group):
    pg_name = group.get("name", f"Unnamed_{group.get('identifier', '')[:6]}")
    scoped_vars = set(group.get("variables", {}).keys())

    if scoped_vars:
        replace_in_pg_and_children(group, scoped_vars, replaced_vars, pg_name)

    for child in group.get("processGroups", []):
        traverse_parent_groups(child)

# --------------------------- Execute ------------------------

if "rootGroup" not in flow_data:
    raise KeyError("Could not find 'rootGroup' in the JSON structure.")

root_group = flow_data["rootGroup"]
print("[*] Looking for variables defined in PGs and replacing within scope (PG + children)...")
traverse_parent_groups(root_group)

# --------------------------- Save Output Files ------------------------

try:
    with open(output_file, 'w') as f:
        json.dump(flow_data, f, indent=2)
        f.write("\n")
    print(f"[✔] Updated flow saved to '{output_file}'")
except Exception as e:
    print(f"[❌] Failed to write updated flow file: {e}")

# Write summary
summary_dict = {pg: sorted(list(vars_set)) for pg, vars_set in replaced_vars.items() if vars_set}

try:
    with open(summary_file, 'w') as f:
        json.dump(summary_dict, f, indent=2)
    print(f"[✔] Replacement summary saved to '{summary_file}'")
except Exception as e:
    print(f"[❌] Failed to write summary file: {e}")
