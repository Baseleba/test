import json
import sys

def count_pg_with_variables(flow_file_path):
    with open(flow_file_path, 'r', encoding='utf-8') as f:
        flow_data = json.load(f)

    pg_with_variables = []

    def traverse_process_group(group):
        print(f"Checking ProcessGroup: {group.get('name', 'Unnamed')} (ID: {group.get('identifier', 'no-id')})")
        vars_block = group.get("variables")
        print(f"  Raw variables block: {vars_block}")

        if vars_block and isinstance(vars_block, dict) and len(vars_block) > 0:
            pg_with_variables.append((group.get('identifier', 'no-id'), group.get('name', 'Unnamed')))
            print("  --> PG has variables!")

        # Recursively check child process groups
        for child_group in group.get("processGroups", []):
            traverse_process_group(child_group)

    root_group = flow_data.get("rootGroup")
    if not root_group:
        print("No 'rootGroup' found in the flow file.")
        return

    traverse_process_group(root_group)

    print(f"\nTotal number of Process Groups with variables: {len(pg_with_variables)}")
    print("List of Process Groups with variables:")
    for pg_id, pg_name in pg_with_variables:
        print(f"  - Name: {pg_name}, ID: {pg_id}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python pg_counter.py <flow.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    count_pg_with_variables(input_path)
