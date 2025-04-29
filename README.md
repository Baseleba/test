import json
import sys
import uuid

# Check and get input file path from command-line arguments
if len(sys.argv) != 2:
    print("Usage: python migrate_variables_into_flow.py <nifi_1.17_flow.json>")
    sys.exit(1)

input_path = sys.argv[1]

# Load the NiFi 1.17 flow JSON
with open(input_path, 'r') as f:
    flow_data = json.load(f)

# For NiFi flow.json, the root group is usually under 'rootGroup'
if "rootGroup" in flow_data:
    root_group = flow_data["rootGroup"]
else:
    raise KeyError("Could not find 'rootGroup' in the JSON structure.")

all_parameters = []  # single list to collect all parameters

def traverse_process_group(group):
    """Recursively traverse process groups and collect all variables into one parameter context."""
    vars_dict = group.get("variables", {})
    if vars_dict:
        for var_name, var_value in vars_dict.items():
            all_parameters.append({
                "name": var_name,
                "description": "",
                "sensitive": False,
                "value": var_value
            })
    
    # Recurse into child process groups if any
    for child_group in group.get("processGroups", []):
        traverse_process_group(child_group)

# Start recursion from the root process group
traverse_process_group(root_group)

# Build a single Parameter Context with UUIDs
parameter_context = {
    "identifier": str(uuid.uuid4()),
    "instanceIdentifier": str(uuid.uuid4()),
    "name": "MigratedVariables",  # Change this name if you want
    "parameters": all_parameters
}

# Inject into the flow
flow_data["parameterContexts"] = [parameter_context]

# Save the new flow with parameter contexts
output_file = "flow_with_parameter_context.json"
with open(output_file, 'w') as f:
    json.dump(flow_data, f, indent=2)
    f.write("\n")

print(f"[✔] All variables combined and injected into flow under 'parameterContexts'. Saved to '{output_file}'")
