#!/bin/bash

INPUT_FLOW="flow - Formatted.json"
PARAM_CONTEXTS="parameter_context2.json"
OUTPUT_FLOW="flow_with_contexts.json"

echo "[*] STEP 1: Generate parameter contexts..."

jq '
    def find_pg(pg):
        if (pg.variables // {} | length > 0) then
            [{
                name: pg.name,
                parameters: (
                    pg.variables | to_entries | map({
                        parameter: {
                            name: .key,
                            value: .value,
                            description: "",
                            sensitive: false
                        }
                    })
                )
            }] +
            (pg.processGroups // [] | map(find_pg(.)) | add)
        else
            (pg.processGroups // [] | map(find_pg(.)) | add)
        end;

    find_pg(.rootGroup)
' "$INPUT_FLOW" > "$PARAM_CONTEXTS"

echo "[*] STEP 2: Attach parameter contexts..."

jq -f attach_contexts.jq "$INPUT_FLOW" > "$OUTPUT_FLOW"

echo "[✔] Done!"
echo " - $PARAM_CONTEXTS"
echo " - $OUTPUT_FLOW"
