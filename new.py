import json
import sys
import uuid

# ----------------------------- Settings -----------------------------
parameter_context_name = "MigratedVariables"  # Name of the new Parameter Context
output_file = "flow_with_parameter_context.json"  # Name of the output file

# --------------------------- Helper Functions ------------------------

def traverse_process_group(group):
    """Recursively traverse process groups, collect variables, and attach parameter context name."""
    vars_dict = group.get("variables", {})
    if vars_dict:
        # Collect variables
        for var_name, var_value in vars_dict.items():
            all_parameters.append({
                "name": var_name,
                "description": "",
                "sensitive": False,
                "value": var_value
            })
        # Attach parameterContextName or parameterContextName_auto
        if "parameterContextName" in group:
            group["parameterContextName_auto"] = parameter_context_name
        else:
            group["parameterContextName"] = parameter_context_name

    # Recursively process child groups
    for child_group in group.get("processGroups", []):
        traverse_process_group(child_group)

# ----------------------------- Main Script ----------------------------

# Check and get input file path
if len(sys.argv) != 2:
    print("Usage: python migrate_variables_into_flow.py <nifi_1.17_flow.json>")
    sys.exit(1)

input_path = sys.argv[1]

# Load the original NiFi flow JSON
with open(input_path, 'r') as f:
    flow_data = json.load(f)

# Locate the root process group
if "rootGroup" in flow_data:
    root_group = flow_data["rootGroup"]
else:
    raise KeyError("Could not find 'rootGroup' in the JSON structure.")

all_parameters = []  # List of all collected parameters

# Start traversing the process groups
traverse_process_group(root_group)

# Build the new Parameter Context
parameter_context = {
    "identifier": str(uuid.uuid4()),
    "instanceIdentifier": str(uuid.uuid4()),
    "name": parameter_context_name,
    "parameters": all_parameters,
    "inheritedParameterContexts": [],
    "componentType": "PARAMETER_CONTEXT"
}

# Append the new Parameter Context to existing ones
if "parameterContexts" in flow_data and isinstance(flow_data["parameterContexts"], list):
    flow_data["parameterContexts"].append(parameter_context)
else:
    flow_data["parameterContexts"] = [parameter_context]

# Save the updated flow JSON
with open(output_file, 'w') as f:
    json.dump(flow_data, f, indent=2)
    f.write("\n")

print(f"[✔] Migration complete (without property changes). Output saved to '{output_file}'")
