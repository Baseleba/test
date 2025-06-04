#!/bin/bash

# Header
echo -e "InstanceName\tPrivateIP\tOS\tImageID\tAMIName"

# Loop through instances
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].[InstanceId, PrivateIpAddress, PlatformDetails, ImageId, Tags[?Key==`Name`]|[0].Value]' \
  --output text | while read -r instance_id private_ip os image_id name; do
  
  ami_name=$(aws ec2 describe-images --image-ids "$image_id" \
    --query 'Images[0].Name' --output text 2>/dev/null)

  echo -e "${name:-N/A}\t${private_ip:-N/A}\t${os:-N/A}\t${image_id:-N/A}\t${ami_name:-N/A}"
done | column -t -s $'\t'




#!/bin/bash

# Header
echo "InstanceName,PrivateIP,OS,ImageID,AMIName"

# Loop through instances
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].[InstanceId, PrivateIpAddress, PlatformDetails, ImageId, Tags[?Key==`Name`]|[0].Value]' \
  --output text | while read -r instance_id private_ip os image_id name; do

  ami_name=$(aws ec2 describe-images --image-ids "$image_id" \
    --query 'Images[0].Name' --output text 2>/dev/null)

  echo "\"${name:-N/A}\",\"${private_ip:-N/A}\",\"${os:-N/A}\",\"${image_id:-N/A}\",\"${ami_name:-N/A}\""
done







#!/bin/bash

echo -e "InstanceName\tPrivateIP\tOS\tImageID\tAMIName"

# Get all instances with relevant metadata
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].[InstanceId, PrivateIpAddress, PlatformDetails, ImageId, Tags[?Key==`Name`]|[0].Value]' \
  --output text | while read -r instance_id private_ip os image_id name; do
  
  # Get the AMI name for this image_id
  ami_name=$(aws ec2 describe-images --image-ids "$image_id" \
    --query 'Images[0].Name' \
    --output text 2>/dev/null)

  # Output the row
  echo -e "${name:-N/A}\t${private_ip:-N/A}\t${os:-N/A}\t${image_id:-N/A}\t${ami_name:-N/A}"

done | column -t -s $'\t'




aws s3api select-object-content \
  --bucket aiq-logging \
  --key "s3-inventories/aiq-qdrive-inventory/data/5bec0881-bef4-4a59-8d57-f1ea3f4fcfc1.csv.gz" \
  --expression "SELECT s._2, s._3, s._7, s._8 FROM S3Object s WHERE s._4 = 'false' AND s._8 = 'GLACIER'" \
  --expression-type SQL \
  --input-serialization '{"CSV": {"FileHeaderInfo": "NONE"}, "CompressionType": "GZIP"}' \
  --output-serialization '{"CSV": {}}' \
  output.csv



DROP TABLE IF EXISTS s3_inventory_aiq_qdrive;

CREATE EXTERNAL TABLE s3_inventory_aiq_qdrive (
  bucket STRING,
  key STRING,
  versionid STRING,
  islatest BOOLEAN,
  isdeletemarker BOOLEAN,
  size BIGINT,
  lastmodifieddate STRING,
  storageclass STRING,
  etag STRING,
  encryptionstatus STRING,
  objectlockretainuntildate STRING,
  objectlockmode STRING,
  objectlocklegalholdstatus STRING,
  intelligenttieringaccesstier STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES (
  'serialization.format' = ',',
  'field.delim' = ','
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
