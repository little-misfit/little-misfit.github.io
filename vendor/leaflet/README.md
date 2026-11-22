# Leaflet 1.9.4

Pinned, self-hosted Leaflet distribution for the Event map. No CDN request is
needed at runtime. The application uses local Natural Earth geometry rather
than a tile service.

- Release: https://github.com/Leaflet/Leaflet/releases/tag/v1.9.4
- Archive: https://github.com/Leaflet/Leaflet/releases/download/v1.9.4/leaflet.zip
- Archive SHA-256: `aaec1d5c3239a613a53e996087629aca1483cb2f0438b11b8a335c6cede4c16b`
- License: BSD 2-Clause; see `LICENSE`, copied from the same tag.
- License source: https://raw.githubusercontent.com/Leaflet/Leaflet/v1.9.4/LICENSE

`leaflet.js`, `leaflet.css`, and `images/` come from the archive's `dist/`
directory. The JavaScript's final source-map URL comment was removed, because
the development source map is not shipped. Runtime code is otherwise unchanged.
CSS and license line endings are normalized to LF, with trailing whitespace
removed; their content is otherwise unchanged.

Load the stylesheet and then the script before the Event application. The
global `L` exposes the Leaflet API. Keep the CSS image files at their existing
relative paths. Offline HTML exports should resolve CSS URLs relative to this
directory before embedding them.
