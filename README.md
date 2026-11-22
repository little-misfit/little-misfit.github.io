# Xuanpu Zhang — personal website

Static academic homepage for GitHub Pages at https://little-misfit.github.io/.
The publishing branch is `main`. Original Monet paintings form the day and
night backgrounds, with soft reading veils, locally served fonts, and a single
theme button.

## Preview

```bash
bash run.sh preview
```

Open `preview/monet-preview.html` or `preview/event-preview.html` in a browser.
Both generated files include their fonts, styles, scripts, and images. Keep the
two files together when downloading them to another machine so navigation works
offline. External paper and profile links still require the internet.

To compare eight handwriting options for the slogan:

```bash
bash run.sh fonts
```

Open `preview/slogan-options.html`. It shows the same text in both palettes and
includes a font-size slider. The first export downloads the candidate fonts and
their licenses into `preview/slogan-fonts/`; subsequent exports reuse them. The
comparison works offline and does not change the font used on the homepage.

For development:

```bash
bash run.sh serve
```

This serves the site at `http://127.0.0.1:8768`. If using VS Code Remote, forward
port 8768 in the Ports panel. Stop the foreground server with Ctrl+C.

## Design and content

- **Day:** *Woman with a Parasol — Madame Monet and Her Son* fills the background
  with a soft, light reading veil; the edges reveal more of the original paint.
- **Night:** *Impression, Sunrise* fills the background with a deep blue-grey
  reading veil. This is a dark theme using the painting, not a
  claim that it depicts night.
- The paintings are fixed CSS backgrounds without a separate artwork panel.
  The original brushstrokes remain visible without a blur filter. Mobile crops
  and a more uniform veil keep the narrow layout readable. The profile, News,
  Recent works, and Experience layouts are retained.
- Cormorant Garamond for the name and section titles; Manrope for reading text.
- Nothing You Could Do handwriting (option H) for “Perfection is reason made sensual.” beneath
  the name. The portrait matches the original homepage's scale: 210px on desktop,
  168px on tablet, and 132px on mobile; the desktop name is reduced to 50px.
- Original portrait, all nine paper records, teaser images, profile links,
  and News retained. Education details and advisor links are in Experience.
- Order: profile, News, Recent works, Experience.
- Event is a separate photo journal at `event.html`. Its default masonry wall
  scrolls slowly, pauses on hover/focus, and stops when the visitor scrolls or
  touches it. The pause/play button controls this motion; reduced-motion users
  start with it off. The wall can always be scrolled manually.
- One view selector rearranges the same photo elements into the wall, a timeline
  grouped by month (newest first), or a geographic map. Photos move between their
  old and new positions. Reduced-motion mode makes the change immediately.
- The map supports dragging, touch gestures, zoom controls, and an All places
  reset. Nearby locations become photo stacks; selecting a multi-place stack
  zooms in, while selecting one place opens its photos. Unlocated photos remain
  available in their own stack. Leaflet and Natural Earth data are served locally;
  no API keys, external map tiles, or runtime map requests are needed.
- Event shares the homepage theme. Clicking a photo opens its image, title,
  date, place, and notes, with previous/next and keyboard controls. Without
  JavaScript, all photo links remain available and open the images directly.
- The initial 12 colored photo placeholders and their dates/coordinates are
  explicitly a sample collection, not the author's personal history.
- One compact theme button cycles Day → Night → System, with a matching icon
  and an accessible label describing the current and next modes. Its visible
  circle is 36px with a 44px touch target. Preferences persist when storage is
  available; System follows OS changes, and switching works without storage.
- The homepage has no continuous animation. Event's optional wall movement
  respects reduced motion. There are no remotely served scripts, analytics,
  or runtime font requests; the map library is bundled locally.

Navigation, compact Event controls, and photo hover labels use translucent,
blurred surfaces. The painting
backgrounds are non-interactive and use fixed overlay colors for legibility;
featured research retains an opaque surface. Publication images keep their
original colors. If a painting cannot load, the theme's solid background remains.

## Edit

- `index.html`: content and page structure.
- `event.html`: photo collection and per-photo metadata.
- `event.css` and `scripts/event.js`: wall, timeline, map, movement, and photo viewer.
- `vendor/leaflet/` and `images/events/map/`: pinned map library and local geometry,
  with licenses and source information in their READMEs.
- `index_css.css`: responsive layout, font declarations, and theme color tokens.
- `scripts/theme-init.js`: theme selection before the first paint.
- `scripts/site.js`: accessible controls and preference synchronization.
- `images/monet/parasol.webp` and `sunrise.webp`: compressed background paintings.
- `images/monet/linen-grain.svg`: retained texture from the previous abstract design.
- `images/monet/README.md`: painting references and provenance; reproductions
  in full-resolution JPG format stay local and are excluded from Git.
- `fonts/`: locally served fonts and their SIL Open Font License texts.

## Add photos

1. Put images in `images/events/`, ideally in a folder for each experience.
2. Replace or duplicate an `.event-photo` link inside `.photo-canvas` in
   `event.html`. DOM order is the default wall order; the timeline sorts dates.
3. Set `href` to the full image and the nested image's `src`, `width`, `height`,
   and descriptive `alt`. A smaller thumbnail can use a different `src`.
4. Update `data-id` (unique), `data-title`, `data-caption`, `data-date`
   (`YYYY-MM-DD`), `data-place`, and `data-ratio` (image width / height).
   Escape quotes and ampersands in HTML attributes as usual.
5. For map placement, set `data-lat` and `data-lng` to the location you want
   publicly displayed. City-level coordinates are sufficient. Missing dates
   show as Undated; missing/invalid coordinates go in the unlocated stack.
   GPS data is not automatically extracted from image files.
6. Remove `data-sample`, `data-tone`, and the `.photo-placeholder-label` span for
   real photos. Update the link's `aria-label`. Once samples are replaced, change
   the collection note and remove its illustrative-dates/places sentence. The
   visible photo total is calculated automatically when JavaScript runs.
7. Run `bash run.sh check` and `bash run.sh preview` to review both themes.

The viewer follows wall order, chronological order, or the selected map stack,
depending on the active view. The site is static; photos and metadata are edited
in the repository. The offline export includes the map and its interactions.

## Checks

```bash
bash run.sh check
```

Checks local references, navigation anchors, image alternative text, section
order, and preservation of the committed paper records and external links.
The generated `preview/` directory is ignored by Git.

Optional browser regression checks, with Python Playwright installed and the
local server running:

```bash
python3 tests/browser_check.py --url http://127.0.0.1:8768/
python3 tests/check_event_browser.py --url http://127.0.0.1:8768/
```

Use `--browser /path/to/chromium` or `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to reuse an
existing browser. The test saves screenshots and `preview/browser-report.json`;
it covers both themes, 320–1440 px layouts, keyboard controls, local-storage
failures, system preference changes, reduced motion, and the offline export.
The Event checks also cover view transitions, chronological order, map grouping,
photo details, motion preferences, keyboard focus, missing metadata/images, and
offline map/photo viewing.

GitHub Pages publishes the repository's `main` branch. Local preview exports and
font comparison downloads stay in the ignored `preview/` directory.
