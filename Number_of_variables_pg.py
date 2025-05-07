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

# ----------------------------- Helpers -----------------------------

def replace_in_props(props, var_names, replaced_vars, pg_name):
    if not isinstance(props, dict):
        return
    for key, val in props.items():
        if not isinstance(val, str):
            continue
        for var in var_names:
            pattern = r'\$\{\s*' + re.escape(var) + r'\s*\}'
            new_val, count = re.subn(pattern, f'#{{{var}}}', val)
            if count > 0:
                props[key] = new_val
                replaced_vars[pg_name].add(var)

def replace_in_pg_and_children(group, var_names, replaced_vars, parent_pg_name):
    # Replace in processors
    for processor in group.get("processors", []):
        config = processor.get("config", {})
        replace_in_props(config.get("properties", {}), var_names, replaced_vars, parent_pg_name)

    # Replace in controller services
    for service in group.get("controllerServices", []):
        replace_in_props(service.get("properties", {}), var_names, replaced_vars, parent_pg_name)

    # Recurse into children
    for child_pg in group.get("processGroups", []):
        replace_in_pg_and_children(child_pg, var_names, replaced_vars, parent_pg_name)

def process_pg(group, replaced_vars):
    pg_name = group.get("name", f"Unnamed_{group.get('identifier', '')[:6]}")
    local_vars = list(group.get("variables", {}).keys())

    if local_vars:
        replace_in_pg_and_children(group, local_vars, replaced_vars, pg_name)

    for child in group.get("processGroups", []):
        process_pg(child, replaced_vars)

# ----------------------------- Main -----------------------------

if "rootGroup" not in flow_data:
    raise KeyError("Could not find 'rootGroup' in the JSON structure.")

root = flow_data["rootGroup"]
replaced_vars = defaultdict(set)

print("[*] Starting variable replacement per PG and its children...")
process_pg(root, replaced_vars)

# Save modified flow
with open(output_file, 'w') as f:
    json.dump(flow_data, f, indent=2)
    f.write("\n")
print(f"[✔] Modified flow saved to '{output_file}'")

# Save replacement summary
summary_dict = {pg: sorted(list(vars)) for pg, vars in replaced_vars.items() if vars}
with open(summary_file, 'w') as f:
    json.dump(summary_dict, f, indent=2)
print(f"[✔] Summary saved to '{summary_file}'")
