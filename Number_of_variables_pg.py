import json
import sys

def count_pg_with_variables(flow_file_path):
    with open(flow_file_path, 'r', encoding='utf-8') as f:
        flow = json.load(f)

    # To store how many PGs have variables
    pg_with_variables = []

    # Recursive function to walk through the flow structure
    def scan_pg(pg):
        if 'variables' in pg and pg['variables']:
            pg_with_variables.append(pg['id'])

        if 'processGroups' in pg:
            for child_pg in pg['processGroups']:
                scan_pg(child_pg)

    # Start scanning from the root
    if 'flowContents' in flow['processGroupFlow']:
        scan_pg(flow['processGroupFlow']['flowContents'])
    else:
        print("No 'flowContents' found in the flow file structure.")
        return

    print(f"Total number of Process Groups with variables: {len(pg_with_variables)}")
    print("List of Process Group IDs with variables:")
    for pg_id in pg_with_variables:
        print(f"  - {pg_id}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python count_pg_with_variables.py <flow.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    count_pg_with_variables(input_path)
