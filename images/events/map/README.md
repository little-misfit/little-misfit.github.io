# Local map geometry

Natural Earth 5.1.2, 1:110 million vector data. These files provide a real
geographic basemap without API keys, tile downloads, or runtime network access.

| File | Browser global | Contents |
| --- | --- | --- |
| `countries.js` | `window.EVENT_MAP_COUNTRIES` | 177 country/administrative features, with `name` and `iso_a3` properties |

The classic script assigns a GeoJSON FeatureCollection. Load it before
`scripts/event.js`; it is also embedded directly in the offline HTML export.
The application passes the object to `L.geoJSON(...)`, styling SVG paths with
the site's day/night tokens. Country polygons include the land shapes.

Natural Earth is generalized world-scale cartography, not a street-level map.
Use this geometry for regional/world navigation and actual latitude/longitude
photo markers. Country boundaries follow the upstream dataset; they do not
represent a statement by the website's author.

## Provenance and transformation

Sources pinned to the upstream `v5.1.2` tag:

- https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_110m_admin_0_countries.geojson
- Repository: https://github.com/nvkelso/natural-earth-vector/tree/v5.1.2
- Terms: https://www.naturalearthdata.com/about/terms-of-use/

Natural Earth map data is public domain. Optional map credit: “Natural Earth”.

Original source SHA-256 checksums:

- Countries: `6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f`

Transformation: preserve all features and coordinate topology; round coordinate
values to four decimal places; remove unused properties and top-level metadata;
retain the country name and `ADM0_A3` code as `name` and `iso_a3`; compact JSON;
wrap in a JavaScript assignment. No geometric simplification was applied.

The map does not use OpenStreetMap tiles. If an online layer is added later,
review the provider's current attribution, caching, and use requirements first.
