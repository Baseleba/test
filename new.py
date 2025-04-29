import json
import sys

def count_pg_with_variables(flow_file_path):
    with open(flow_file_path, 'r', encoding='utf-8') as f:
        flow_data = json.load(f)

    pg_with_variables = []

    def traverse_process_group(group):
        vars_dict = group.get("variables", {})
        if vars_dict:
            if isinstance(vars_dict, dict) and len(vars_dict) > 0:
                pg_with_variables.append((group['id'], group.get('name', 'Unnamed')))

        # Recursively scan child processGroups
        for child_group in group.get("processGroups", []):
            traverse_process_group(child_group)

    # Locate the root process group
    root_group = flow_data.get("rootGroup")
    if not root_group:
        print("No 'rootGroup' found in the flow file.")
        return

    # Start traversing
    traverse_process_group(root_group)

    print(f"Total number of Process Groups with variables: {len(pg_with_variables)}")
    print("List of Process Groups with variables:")
    for pg_id, pg_name in pg_with_variables:
        print(f"  - Name: {pg_name}, ID: {pg_id}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python count_pg_with_variables.py <flow.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    count_pg_with_variables(input_path)
