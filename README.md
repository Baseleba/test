SELECT key, version_id, last_modified_date, storage_class
FROM s3_inventory_aiq_qdrive
WHERE is_latest = false
  AND storage_class = 'GLACIER_FLEXIBLE_RETRIEVAL';



CREATE EXTERNAL TABLE IF NOT EXISTS s3_inventory_aiq_qdrive (
  bucket STRING,
  key STRING,
  version_id STRING,
  is_latest BOOLEAN,
  is_delete_marker BOOLEAN,
  size BIGINT,
  last_modified_date STRING,
  storage_class STRING,
  etag STRING,
  encryption_status STRING,
  object_lock_retain_until_date STRING,
  object_lock_mode STRING,
  object_lock_legal_hold_status STRING,
  intelligent_tiering_access_tier STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
  'separatorChar' = ',',
  'quoteChar' = '\"'
)
STORED AS TEXTFILE
LOCATION 's3://aiq-logging/s3-inventories/aiq-qdrive-inventory/data/'
TBLPROPERTIES ('skip.header.line.count'='1');






import json
import sys
import uuid
import re

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
parameter_context_name = "MigratedVariables"  # Name of the new context we create

def update_properties(properties):
    """Update properties dictionary: replace ${...} with #{...}."""
    if not properties:
        return
    for key, value in properties.items():
        if isinstance(value, str) and "${" in value:
            properties[key] = re.sub(r'\$\{([^}]+)\}', r'#\{\1\}', value)

def traverse_process_group(group):
    """Recursively traverse process groups, collect variables, attach parameter context, update properties."""
    vars_dict = group.get("variables", {})
    if vars_dict:
        # Add variables to global list
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

    # Update all processors' properties
    for processor in group.get("processors", []):
        update_properties(processor.get("config", {}).get("properties", {}))

    # Recurse into child process groups if any
    for child_group in group.get("processGroups", []):
        traverse_process_group(child_group)

# Start recursion from the root process group
traverse_process_group(root_group)

# Build the new single Parameter Context
parameter_context = {
    "identifier": str(uuid.uuid4()),
    "instanceIdentifier": str(uuid.uuid4()),
    "name": parameter_context_name,
    "parameters": all_parameters,
    "inheritedParameterContexts": [],
    "componentType": "PARAMETER_CONTEXT"
}

# Append the new parameter context
if "parameterContexts" in flow_data and isinstance(flow_data["parameterContexts"], list):
    flow_data["parameterContexts"].append(parameter_context)
else:
    flow_data["parameterContexts"] = [parameter_context]

# Save the updated flow
output_file = "flow_with_parameter_context.json"
with open(output_file, 'w') as f:
    json.dump(flow_data, f, indent=2)
    f.write("\n")

print(f"[✔] Migrated variables into Parameters, updated Process Groups, and fixed properties. Saved to '{output_file}'")
