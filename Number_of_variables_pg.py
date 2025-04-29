import json
import sys

def count_pg_with_variables(flow_file_path):
    with open(flow_file_path, 'r', encoding='utf-8') as f:
        flow = json.load(f)

    pg_with_variables = []

    def has_variables(pg):
        vars_block = pg.get('variables')
        if vars_block and isinstance(vars_block, dict):
            variables_list = vars_block.get('variables', [])
            if isinstance(variables_list, list) and len(variables_list) > 0:
                return True
        return False

    def scan_pg(pg):
        # Check if this PG has variables
        if has_variables(pg):
            pg_with_variables.append((pg['id'], pg.get('name', 'Unnamed')))

        # Now recursively check child processGroups
        for child_pg in pg.get('processGroups', []):
            scan_pg(child_pg)

    # Get rootGroup
    root_group = flow.get('rootGroup')
    if not root_group:
        print("No 'rootGroup' found in the flow file.")
        return

    # Scan rootGroup itself
    scan_pg(root_group)

    print(f"Total number of Process Groups with variables: {len(pg_with_variables)}")
    print("List of Process Groups with variables:")
    for pg_id, pg_name in pg_with_variables:
        print(f"  - ID: {pg_id}, Name: {pg_name}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python count_pg_with_variables.py <flow.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    count_pg_with_variables(input_path)
