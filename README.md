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
- Event is a separate personal photo journal at `event.html`, linked from the
  homepage navigation. Entries run newest first, with a date, title, short note,
  and photo group. The initial entry and three photos are clearly placeholders.
- Event shares the theme preference with the homepage. Photo links open a native
  dialog with previous/next controls, arrow-key browsing, and Escape to close;
  without JavaScript they open the image directly.
- One compact theme button cycles Day → Night → System, with a matching icon
  and an accessible label describing the current and next modes. Its visible
  circle is 36px with a 44px touch target. Preferences persist when storage is
  available; System follows OS changes, and switching works without storage.
- No continuous animation, third-party scripts, analytics, or runtime font
  requests. Reduced-motion preferences are respected.

Only the navigation uses a translucent, blurred surface. The painting
backgrounds are non-interactive and use fixed overlay colors for legibility;
featured research retains an opaque surface. Publication images keep their
original colors. If a painting cannot load, the theme's solid background remains.

## Edit

- `index.html`: content and page structure.
- `event.html`: life-event entries and photo captions.
- `event.css` and `scripts/event.js`: timeline layout and photo viewer.
- `index_css.css`: responsive layout, font declarations, and theme color tokens.
- `scripts/theme-init.js`: theme selection before the first paint.
- `scripts/site.js`: accessible controls and preference synchronization.
- `images/monet/parasol.webp` and `sunrise.webp`: compressed background paintings.
- `images/monet/linen-grain.svg`: retained texture from the previous abstract design.
- `images/monet/README.md`: painting references and provenance; reproductions
  in full-resolution JPG format stay local and are excluded from Git.
- `fonts/`: locally served fonts and their SIL Open Font License texts.

## Add life events

1. Put photos in `images/events/`, ideally in a folder for each entry.
2. Duplicate an `.event-entry` article in `event.html`, newest first. Give its
   heading a unique ID and update the article's `aria-labelledby` to match.
3. Replace the date placeholder with a year and a `<time datetime="YYYY-MM-DD">`
   element, then replace the title and description with the actual information.
4. For each photo, set the link's `href` to the full image and the nested image's
   `src`, `width`, `height`, and descriptive `alt`. Set `data-caption` to its
   caption and remove the `.photo-placeholder-label` span. Optional visible
   captions can use `<figcaption>` after the photo link.
5. Add or remove `.event-figure` elements as needed. One and two images use simple
   rows; three images use a large lead image and two supporting images.
6. Run `bash run.sh check` and `bash run.sh preview` to review both themes.

The image viewer stays within the selected entry's photo group. The site is
static; content and images are added in the repository.

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
The Event checks also cover cross-page navigation, photo-group browsing,
keyboard focus, quick close/reopen, missing images, and offline photo viewing.

GitHub Pages publishes the repository's `main` branch. Local preview exports and
font comparison downloads stay in the ignored `preview/` directory.
