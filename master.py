import json
import sys
import uuid

# ----------------------------- Settings -----------------------------
output_file = "flow_with_multiple_parameter_contexts.json"

# ----------------------------- Main Script ----------------------------

# Check and get input file path
if len(sys.argv) != 2:
    print("Usage: python migrate_variables_per_pg.py <nifi_1.17_flow.json>")
    sys.exit(1)

input_path = sys.argv[1]

# Load the original NiFi flow JSON
with open(input_path, 'r') as f:
    flow_data = json.load(f)

# Locate the root process group
if "rootGroup" not in flow_data:
    raise KeyError("Could not find 'rootGroup' in the JSON structure.")

root_group = flow_data["rootGroup"]
parameter_contexts = []  # list to collect all new parameter contexts

# --------------------------- Helper Function ------------------------

def traverse_and_create_parameter_context(group):
    pg_name = group.get("name", f"Unnamed_{uuid.uuid4().hex[:6]}")
    pg_identifier = group.get("identifier", str(uuid.uuid4()))
    vars_dict = group.get("variables", {})

    if vars_dict:
        parameters = []
        for var_name, var_value in vars_dict.items():
            parameters.append({
                "name": var_name,
                "description": "",
                "sensitive": False,
                "value": var_value
            })

        # Create a new Parameter Context for this PG
        pc_name = f"{pg_name}_Context"
        pc_id = str(uuid.uuid4())
        parameter_context = {
            "identifier": pc_id,
            "instanceIdentifier": str(uuid.uuid4()),
            "name": pc_name,
            "parameters": parameters,
            "inheritedParameterContexts": [],
            "componentType": "PARAMETER_CONTEXT"
        }

        parameter_contexts.append(parameter_context)

        # Handle PGs with existing parameterContextName
        if "parameterContextName" in group:
            group["parameterContextName_auto"] = pc_name
        else:
            group["parameterContextName"] = pc_name

    # Recurse into nested PGs
    for child in group.get("processGroups", []):
        traverse_and_create_parameter_context(child)

# --------------------------- Execute ------------------------

print("[*] Starting traversal of process groups...")

traverse_and_create_parameter_context(root_group)

print(f"[*] Finished traversal. Found {len(parameter_contexts)} parameter contexts.")

# Add parameter contexts to flow file
if "parameterContexts" in flow_data and isinstance(flow_data["parameterContexts"], list):
    print("[*] Appending to existing parameterContexts array.")
    flow_data["parameterContexts"].extend(parameter_contexts)
else:
    print("[*] Creating new parameterContexts array.")
    flow_data["parameterContexts"] = parameter_contexts

# Save result
try:
    with open(output_file, 'w') as f:
        json.dump(flow_data, f, indent=2)
        f.write("\n")
    print(f"[✔] Migration complete. Created {len(parameter_contexts)} Parameter Context(s). Output saved to '{output_file}'")
except Exception as e:
    print(f"[❌] Failed to write output file: {e}")

