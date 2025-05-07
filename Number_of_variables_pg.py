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

# ----------------------------- Replacer -----------------------------

replaced_vars = defaultdict(set)

def replace_in_properties(props, variable_names, pg_name):
    if not isinstance(props, dict):
        return

    for key, val in props.items():
        if isinstance(val, str):
            for var in variable_names:
                pattern = r'\$\{\s*' + re.escape(var) + r'\s*\}'
                new_val, count = re.subn(pattern, f'#{{{var}}}', val)
                if count > 0:
                    props[key] = new_val
                    replaced_vars[pg_name].add(var)

def replace_variables_in_pg_and_children(group, variable_names, pg_name):
    # Replace in processors
    for processor in group.get("processors", []):
        config = processor.get("config", {})
        replace_in_properties(config.get("properties", {}), variable_names, pg_name)

    # Replace in controller services
    for service in group.get("controllerServices", []):
        replace_in_properties(service.get("properties", {}), variable_names, pg_name)

    # Recurse into child PGs
    for child in group.get("processGroups", []):
        replace_variables_in_pg_and_children(child, variable_names, pg_name)

# ----------------------------- Traverse -----------------------------

def traverse_and_replace(group):
    pg_name = group.get("name", f"Unnamed_{group.get('identifier', '')[:6]}")
    vars_dict = group.get("variables", {})

    if vars_dict:
        variable_names = list(vars_dict.keys())
        replace_variables_in_pg_and_children(group, variable_names, pg_name)

    for child in group.get("processGroups", []):
        traverse_and_replace(child)

# ----------------------------- Run -----------------------------

if "rootGroup" not in flow_data:
    raise KeyError("Could not find 'rootGroup' in the JSON structure.")

root_group = flow_data["rootGroup"]
print("[*] Replacing variable references in each PG and children...")

traverse_and_replace(root_group)

# Save the modified flow
with open(output_file, 'w') as f:
    json.dump(flow_data, f, indent=2)
print(f"[✔] Flow file saved to '{output_file}'")

# Save replacement summary
summary = {pg: sorted(vars) for pg, vars in replaced_vars.items()}
with open(summary_file, 'w') as f:
    json.dump(summary, f, indent=2)
print(f"[✔] Replacement summary saved to '{summary_file}'")
