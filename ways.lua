local ways = osm2pgsql.define_way_table('ways', {
    { column = 'kind', type = 'text' },
    { column = 'name', type = 'text' },
    { column = 'bridge', type = 'text' },
    { column = 'layer', type = 'int4' },
    { column = 'geom', type = 'linestring' }
})

function osm2pgsql.process_way(object)
    if object.tags.highway then
        ways:add_row({
            kind = object.tags.highway,
            name = object.tags.name,
            bridge = object.tags.bridge,
            layer = object.tags.layer,
            geom = { create = 'line' }
        })
    end
end
