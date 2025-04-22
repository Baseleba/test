#!/bin/bash

INPUT_FLOW="flow - Formatted.json"
PARAM_CONTEXTS="partameter_context2.json"
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

jq '
    def attach_context(pg):
        if (pg.variables // {} | length > 0) then
            if pg.parameterContext? then
                pg + { parameterContext_auto: { name: pg.name } }
            else
                pg + { parameterContext: { name: pg.name } }
            end
        else
            pg
        end;
        pg + {
            processGroups: (pg.processGroups // [] | map(attach_context))
        };

    .rootGroup |= attach_context(.)
' "$INPUT_FLOW" > "$OUTPUT_FLOW"
