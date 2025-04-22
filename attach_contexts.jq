def attach_context(pg):
   (
        if (pg.variables // {} | length > 0) then
            if pg.parameterContext? then
                pg + { parameterContext_auto: { name: pg.name } }
            else
                pg + { parameterContext: { name: pg.name } }
            end
        else
            pg
        end
    )
    + {
        processGroups: (
            (pg.processGroups // []) | map(attach_context)
        )
    };

.rootGroup |= attach_context(.)