(() => {
    const journal = document.querySelector('.photo-journal');
    if (!journal) return;
    const stage = journal.querySelector('.photo-stage');
    const canvas = journal.querySelector('.photo-canvas');
    const photos = [...canvas.querySelectorAll('.event-photo')];
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    const picker = journal.querySelector('.view-picker');
    const toggle = picker.querySelector('.view-toggle');
    const menu = picker.querySelector('.view-menu');
    const options = [...menu.querySelectorAll('[data-view]')];
    const motion = journal.querySelector('.motion-toggle');
    const mapElement = journal.querySelector('.map-canvas');
    const mapTools = journal.querySelector('.map-tools');
    const dialog = document.querySelector('.photo-viewer');
    const names = { wall: 'Photo wall', time: 'By time', place: 'By place' };
    let view = 'wall';
    let map;
    let mapGroups = [];
    let changingLayout = false;
    let animations = [];
    let scrollPositions = { wall: 0, time: 0 };
    let playing = !reducedMotion.matches;
    let hovered = false;
    let focused = false;
    let onScreen = true;
    let direction = 1;
    let autoPosition = 0;
    let lastTick = 0;
    let lastWidth = 0;
    let lastHeight = 0;
    let resumeAt = performance.now() + 2200;

    const validDate = photo => /^\d{4}-\d{2}-\d{2}$/.test(photo.dataset.date || '') && !Number.isNaN(Date.parse(photo.dataset.date)) && new Date(photo.dataset.date).toISOString().slice(0, 10) === photo.dataset.date;
    const coordinates = photo => {
        const { lat, lng } = photo.dataset;
        if (!lat?.trim() || !lng?.trim()) return null;
        const point = [Number(lat), Number(lng)];
        return point.every(Number.isFinite) && Math.abs(point[0]) <= 85 && Math.abs(point[1]) <= 180 ? point : null;
    };
    const dated = (photo, format) => validDate(photo) ? new Intl.DateTimeFormat('en-US', { ...format, timeZone: 'UTC' }).format(new Date(photo.dataset.date + 'T12:00:00Z')) : 'Undated';
    const chronological = [...photos].sort((a, b) => (validDate(b) ? b.dataset.date : '').localeCompare(validDate(a) ? a.dataset.date : ''));

    photos.forEach(photo => {
        const hint = document.createElement('span');
        hint.className = 'photo-hover';
        hint.setAttribute('aria-hidden', 'true');
        hint.innerHTML = '<svg viewBox="0 0 16 16"><path d="M6 2H2v4m8-4h4v4M2 10v4h4m4 0h4v-4"/></svg><span>View details</span>';
        photo.append(hint);
        for (const className of ['photo-map-label', 'photo-map-count']) {
            const label = document.createElement('span');
            label.className = className;
            label.setAttribute('aria-hidden', 'true');
            photo.append(label);
        }
        photo.dataset.originalLabel = photo.getAttribute('aria-label') || photo.querySelector('img').alt;
    });

    function setBox(photo, x, y, width, height) {
        Object.assign(photo.style, { left: `${x}px`, top: `${y}px`, width: `${width}px`, height: `${height}px` });
    }

    function resetPhoto(photo) {
        photo.removeAttribute('aria-hidden');
        photo.tabIndex = 0;
        photo.dataset.stack = '';
        photo.style.zIndex = '';
        photo.style.opacity = '';
        photo.setAttribute('aria-label', photo.dataset.originalLabel);
        photo.querySelector('.photo-map-label').hidden = true;
        photo.querySelector('.photo-map-count').hidden = true;
    }

    function gridSettings() {
        const width = stage.clientWidth - 4;
        const columns = width >= 760 ? 3 : 2;
        const gap = width < 600 ? 12 : 20;
        return { columns, gap, cardWidth: (width - gap * (columns - 1)) / columns };
    }

    function layoutWall() {
        const { columns, gap, cardWidth } = gridSettings();
        const heights = Array(columns).fill(2);
        photos.forEach(photo => {
            const column = heights.indexOf(Math.min(...heights));
            const ratio = Number(photo.dataset.ratio) || 1;
            const height = cardWidth / Math.max(.5, Math.min(2, ratio));
            setBox(photo, 2 + column * (cardWidth + gap), heights[column], cardWidth, height);
            heights[column] += height + gap;
        });
        canvas.style.height = `${Math.max(...heights)}px`;
    }

    function layoutTime() {
        const { columns, gap, cardWidth } = gridSettings();
        const groups = new Map();
        chronological.forEach(photo => {
            const key = validDate(photo) ? photo.dataset.date.slice(0, 7) : 'Undated';
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(photo);
        });
        let y = 4;
        for (const group of groups.values()) {
            const heading = document.createElement('h2');
            heading.className = 'time-heading';
            heading.style.top = `${y}px`;
            heading.textContent = dated(group[0], { month: 'long', year: 'numeric' });
            const count = document.createElement('span');
            count.textContent = `${group.length} photos`;
            heading.append(count);
            canvas.append(heading);
            y += 58;
            const height = cardWidth * .8;
            group.forEach((photo, i) => {
                canvas.append(photo);
                setBox(photo, 2 + (i % columns) * (cardWidth + gap), y + Math.floor(i / columns) * (height + gap), cardWidth, height);
            });
            y += Math.ceil(group.length / columns) * (height + gap) + 32;
        }
        canvas.style.height = `${y}px`;
    }

    function fitPlaces() {
        const points = photos.map(coordinates).filter(Boolean);
        if (points.length) map.fitBounds(points, { padding: [stage.clientWidth < 600 ? 70 : 120, 110], maxZoom: 4.5, animate: false });
        else map.setView([25, 15], 2, { animate: false });
    }

    function createMap() {
        if (map) return;
        map = L.map(mapElement, { zoomControl: false, attributionControl: true, scrollWheelZoom: false, minZoom: 2, maxZoom: 8, zoomSnap: .25, zoomAnimation: false, fadeAnimation: false, maxBounds: [[-85, -190], [85, 190]], maxBoundsViscosity: .8 });
        map.setView([32, 114], 4, { animate: false });
        L.control.zoom({ position: 'bottomright' }).addTo(map);
        map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener noreferrer">Leaflet</a>');
        map.attributionControl.addAttribution('<a href="https://www.naturalearthdata.com/" target="_blank" rel="noopener noreferrer">Natural Earth</a>');
        L.geoJSON(window.EVENT_MAP_COUNTRIES, { interactive: false, style: { className: 'map-land', fillOpacity: 1, opacity: 1 } }).addTo(map);
        for (let lat = -60; lat <= 80; lat += 20) L.polyline([[lat, -180], [lat, 180]], { className: 'map-grid', interactive: false }).addTo(map);
        for (let lng = -180; lng <= 180; lng += 20) L.polyline([[-85, lng], [85, lng]], { className: 'map-grid', interactive: false }).addTo(map);
        [['China', 35, 108], ['Mongolia', 46, 103], ['Japan', 37, 138], ['India', 23, 79], ['South Korea', 36, 128], ['Vietnam', 17, 107], ['East China Sea', 27, 125]].forEach(([name, lat, lng]) => {
            const label = document.createElement('span');
            label.textContent = name;
            L.marker([lat, lng], { interactive: false, keyboard: false, icon: L.divIcon({ className: name.includes('Sea') ? 'map-water-label' : 'map-city-label', html: label, iconSize: [100, 20], iconAnchor: [35, 10] }) }).addTo(map);
        });
        map.on('move zoom', () => { if (view === 'place' && !changingLayout) layoutPlaces(); });
    }

    // Cluster in screen space, so nearby places separate naturally as the map zooms in.
    function locationGroups(size) {
        const groups = [];
        for (const photo of chronological) {
            const location = coordinates(photo);
            if (!location) continue;
            const point = map.latLngToContainerPoint(location);
            groups.push({ photos: [photo], x: point.x, y: point.y });
        }
        let merged = true;
        while (merged) {
            merged = false;
            outer: for (let i = 0; i < groups.length; i++) {
                for (let j = i + 1; j < groups.length; j++) {
                    const a = groups[i], b = groups[j];
                    if (Math.hypot(a.x - b.x, a.y - b.y) < size + 42) {
                        const total = a.photos.length + b.photos.length;
                        a.x = (a.x * a.photos.length + b.x * b.photos.length) / total;
                        a.y = (a.y * a.photos.length + b.y * b.photos.length) / total;
                        a.photos.push(...b.photos);
                        groups.splice(j, 1);
                        merged = true;
                        break outer;
                    }
                }
            }
        }
        return groups;
    }

    function layoutPlaces() {
        if (!map) return;
        const size = stage.clientWidth < 600 ? 62 : 78;
        canvas.style.height = `${stage.clientHeight}px`;
        canvas.querySelectorAll('.map-unlocated').forEach(node => node.remove());
        photos.forEach(resetPhoto);
        mapGroups = locationGroups(size);
        mapGroups.forEach(group => {
            const places = [...new Set(group.photos.map(p => p.dataset.place || 'Unnamed place'))];
            group.places = places;
            group.photos.sort((a, b) => chronological.indexOf(a) - chronological.indexOf(b));
            group.photos.forEach((photo, i) => {
                const offset = Math.min(i, 2) * 4;
                setBox(photo, group.x - size / 2 + offset, group.y - size - 12 - offset, size, size);
                photo.style.zIndex = String(30 - i);
                photo.style.opacity = i > 2 ? '0' : '1';
                photo.dataset.stack = i ? 'back' : 'front';
                photo.tabIndex = i ? -1 : 0;
                if (i) photo.setAttribute('aria-hidden', 'true');
                else {
                    const label = photo.querySelector('.photo-map-label');
                    label.textContent = places.length === 1 ? places[0] : `${places.length} places`;
                    label.hidden = false;
                    const count = photo.querySelector('.photo-map-count');
                    count.textContent = group.photos.length;
                    count.hidden = group.photos.length === 1;
                    photo.setAttribute('aria-label', `${group.photos.length} photos in ${places.join(' and ')}. ${places.length > 1 ? 'Zoom in' : 'View details'}.`);
                }
            });
        });
        const unlocated = photos.filter(photo => !coordinates(photo));
        if (unlocated.length) {
            const label = document.createElement('p');
            label.className = 'map-unlocated';
            label.textContent = `${unlocated.length} photos without a location`;
            canvas.append(label);
            // One accessible stack keeps undated / ungeotagged photos available on the map.
            unlocated.forEach((photo, i) => {
                setBox(photo, 18 + Math.min(i, 2) * 4, stage.clientHeight - 92 - Math.min(i, 2) * 4, 62, 62);
                photo.style.zIndex = String(40 - i);
                photo.style.opacity = i > 2 ? '0' : '1';
                photo.dataset.stack = i ? 'back' : 'front';
                photo.tabIndex = i ? -1 : 0;
                if (i) photo.setAttribute('aria-hidden', 'true');
                else photo.setAttribute('aria-label', `${unlocated.length} photos without a location. View details.`);
            });
            mapGroups.push({ photos: unlocated, places: [] });
        }
        journal.querySelector('.map-summary').textContent = `${new Set(photos.filter(coordinates).map(p => p.dataset.place || `${p.dataset.lat},${p.dataset.lng}`)).size} places`;
    }

    function layout(animate = false) {
        const before = new Map(photos.map(p => [p, p.getBoundingClientRect()]));
        animations.forEach(animation => animation.cancel());
        animations = [];
        changingLayout = true;
        canvas.querySelectorAll('.time-heading, .map-unlocated').forEach(node => node.remove());
        photos.forEach(resetPhoto);
        journal.dataset.view = view;
        mapElement.hidden = view !== 'place';
        mapTools.hidden = view !== 'place';
        if (view === 'place') {
            stage.scrollTop = 0;
            const firstMapView = !map;
            createMap();
            map.invalidateSize({ pan: false });
            if (firstMapView) fitPlaces();
            layoutPlaces();
        } else {
            if (view === 'wall') {
                photos.forEach(photo => canvas.append(photo));
                layoutWall();
            } else layoutTime();
            stage.scrollTop = scrollPositions[view];
        }
        changingLayout = false;
        if (animate && !reducedMotion.matches) {
            photos.forEach((photo, i) => {
                const old = before.get(photo), next = photo.getBoundingClientRect();
                if (!old.width || !next.width) return;
                animations.push(photo.animate([
                    { transform: `translate(${old.left - next.left}px, ${old.top - next.top}px) scale(${old.width / next.width}, ${old.height / next.height})` },
                    { transform: 'none' }
                ], { duration: 720, delay: Math.min(i * 12, 100), easing: 'cubic-bezier(.22,.75,.2,1)' }));
            });
        }
        autoPosition = stage.scrollTop;
        resumeAt = performance.now() + 1500;
        // Mode changes may alter scrollbar width; only actual resizes should
        // trigger a second layout and interrupt an in-progress rearrangement.
        lastWidth = stage.clientWidth;
        lastHeight = stage.clientHeight;
    }

    function updateMotion() {
        motion.hidden = view !== 'wall';
        motion.setAttribute('aria-pressed', String(playing));
        motion.setAttribute('aria-label', playing ? 'Pause photo wall' : 'Play photo wall');
        motion.title = playing ? 'Pause photo wall' : 'Play photo wall';
    }

    function closeMenu(restore = false) {
        menu.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
        if (restore) toggle.focus({ preventScroll: true });
    }

    function changeView(next) {
        if (next === view) return;
        if (view !== 'place') scrollPositions[view] = stage.scrollTop;
        view = next;
        options.forEach(option => option.setAttribute('aria-checked', String(option.dataset.view === view)));
        toggle.querySelector('.view-label').textContent = names[view];
        stage.setAttribute('aria-label', view === 'place' ? 'Photo locations. Drag the map or use its zoom controls.' : `Scrollable ${view === 'time' ? 'photos by time' : 'photo wall'}`);
        journal.querySelector('.view-status').textContent = `${names[view]}. ${photos.length} photos.`;
        journal.querySelector('.view-hint').textContent = view === 'place' ? 'Explore a place to see its photos.' : view === 'time' ? 'Newest memories first.' : 'Click a photo to explore.';
        updateMotion();
        layout(true);
    }

    toggle.addEventListener('click', () => {
        const open = menu.hidden;
        menu.hidden = !open;
        toggle.setAttribute('aria-expanded', String(open));
        if (open) options.find(option => option.dataset.view === view).focus();
    });
    options.forEach(option => option.addEventListener('click', () => { closeMenu(true); changeView(option.dataset.view); }));
    picker.addEventListener('keydown', event => {
        if (event.key === 'Escape') { closeMenu(true); event.preventDefault(); }
        if (menu.hidden) return;
        const index = options.indexOf(document.activeElement);
        if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
            event.preventDefault();
            const next = event.key === 'Home' ? 0 : event.key === 'End' ? options.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length;
            options[next].focus();
        }
    });
    document.addEventListener('pointerdown', event => { if (!picker.contains(event.target)) closeMenu(); });
    picker.addEventListener('focusout', event => { if (!picker.contains(event.relatedTarget)) closeMenu(); });
    motion.addEventListener('click', () => { playing = !playing; autoPosition = stage.scrollTop; resumeAt = performance.now() + 500; updateMotion(); });
    const pauseForInteraction = () => { if (playing) { playing = false; updateMotion(); } };
    stage.addEventListener('wheel', pauseForInteraction, { passive: true });
    stage.addEventListener('touchstart', pauseForInteraction, { passive: true });
    stage.addEventListener('keydown', event => { if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '].includes(event.key)) pauseForInteraction(); });
    stage.addEventListener('pointerenter', event => { if (event.pointerType === 'mouse') hovered = true; });
    stage.addEventListener('pointerleave', () => { hovered = false; autoPosition = stage.scrollTop; });
    stage.addEventListener('focusin', () => { focused = true; });
    stage.addEventListener('focusout', event => { focused = stage.contains(event.relatedTarget); autoPosition = stage.scrollTop; });
    reducedMotion.addEventListener('change', () => {
        if (reducedMotion.matches) { playing = false; animations.forEach(a => a.cancel()); updateMotion(); }
    });
    new IntersectionObserver(entries => { onScreen = entries[0].isIntersecting; }).observe(stage);
    function tick(now) {
        const elapsed = Math.min(64, now - (lastTick || now));
        lastTick = now;
        if (playing && view === 'wall' && !hovered && !focused && !dialog.open && menu.hidden && !document.hidden && onScreen && now > resumeAt) {
            const max = stage.scrollHeight - stage.clientHeight;
            if (max > 0) {
                autoPosition = Math.max(0, Math.min(max, autoPosition + direction * elapsed * .012));
                stage.scrollTop = autoPosition;
                if (autoPosition >= max || autoPosition <= 0) { direction *= -1; resumeAt = now + 1400; }
            }
        }
        requestAnimationFrame(tick);
    }
    journal.querySelector('.map-reset').addEventListener('click', () => { fitPlaces(); layoutPlaces(); });
    if (!window.L || !window.EVENT_MAP_COUNTRIES) {
        const mapOption = options.find(option => option.dataset.view === 'place');
        mapOption.disabled = true;
        mapOption.querySelector('span').textContent = 'Map unavailable';
    }
    journal.classList.add('is-enhanced');
    picker.hidden = false;
    journal.querySelector('.collection-count').textContent = `${photos.length} photos`;
    updateMotion();
    layout();
    new ResizeObserver(() => {
        if (stage.clientWidth === lastWidth && stage.clientHeight === lastHeight) return;
        lastWidth = stage.clientWidth; lastHeight = stage.clientHeight;
        if (view !== 'place') scrollPositions[view] = stage.scrollTop;
        layout();
        if (view === 'place') { fitPlaces(); layoutPlaces(); }
    }).observe(stage);
    requestAnimationFrame(tick);

    if (!dialog || typeof dialog.showModal !== 'function') return;
    const image = dialog.querySelector('.viewer-image');
    const caption = dialog.querySelector('#viewer-caption');
    const count = dialog.querySelector('.viewer-count');
    const status = dialog.querySelector('.viewer-status');
    const previous = dialog.querySelector('[data-photo-step="-1"]');
    const next = dialog.querySelector('[data-photo-step="1"]');
    const closeButton = dialog.querySelector('.viewer-close');
    let viewing = [];
    let current = 0;
    let trigger;

    function showPhoto(index) {
        if (index < 0 || index >= viewing.length) return;
        current = index;
        const photo = viewing[current];
        image.hidden = true;
        status.hidden = false;
        status.textContent = 'Loading photo…';
        dialog.querySelector('#viewer-title').textContent = photo.dataset.title || 'Untitled moment';
        caption.textContent = photo.dataset.caption || photo.querySelector('img').alt;
        dialog.querySelector('.viewer-date').textContent = dated(photo, { month: 'long', day: 'numeric', year: 'numeric' });
        dialog.querySelector('.viewer-place').textContent = photo.dataset.place || 'Location not added';
        dialog.querySelector('.viewer-sample').hidden = photo.dataset.sample !== 'true';
        dialog.querySelector('.viewer-stage').dataset.tone = photo.dataset.tone || '';
        dialog.querySelector('.viewer-stage').style.background = getComputedStyle(photo).background;
        dialog.querySelector('.viewer-stage').style.backgroundBlendMode = getComputedStyle(photo).backgroundBlendMode;
        count.textContent = `${current + 1} / ${viewing.length}`;
        const focusedControl = document.activeElement;
        previous.disabled = current === 0;
        next.disabled = current === viewing.length - 1;
        if (focusedControl === previous && previous.disabled) (next.disabled ? closeButton : next).focus({ preventScroll: true });
        else if (focusedControl === next && next.disabled) (previous.disabled ? closeButton : previous).focus({ preventScroll: true });
        image.alt = photo.querySelector('img').alt;
        image.src = photo.href;
    }
    image.addEventListener('load', () => { image.hidden = false; status.hidden = true; });
    image.addEventListener('error', () => { image.hidden = true; status.hidden = false; status.textContent = 'This photo could not be loaded.'; });
    photos.forEach(photo => photo.addEventListener('click', event => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        if (view === 'place') {
            const group = mapGroups.find(group => group.photos.includes(photo));
            if (group?.places.length > 1 && map.getZoom() < 8) {
                map.flyToBounds(group.photos.map(coordinates), { padding: [90, 110], maxZoom: 8, duration: reducedMotion.matches ? 0 : .65, animate: !reducedMotion.matches });
                return;
            }
            viewing = group?.photos || [photo];
        } else viewing = view === 'time' ? chronological : photos;
        trigger = photo;
        showPhoto(viewing.indexOf(photo));
        document.body.classList.add('viewer-open');
        dialog.showModal();
    }));
    closeButton.addEventListener('click', () => dialog.close());
    dialog.querySelectorAll('[data-photo-step]').forEach(button => button.addEventListener('click', () => showPhoto(current + Number(button.dataset.photoStep))));
    dialog.addEventListener('keydown', event => {
        if (event.key === 'Tab') {
            const controls = [...dialog.querySelectorAll('button:not(:disabled)')];
            const first = controls[0], last = controls[controls.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); showPhoto(current + (event.key === 'ArrowRight' ? 1 : -1)); }
    });
    dialog.addEventListener('click', event => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
    });
    dialog.addEventListener('close', () => {
        if (dialog.open) return;
        document.body.classList.remove('viewer-open');
        image.removeAttribute('src');
        trigger?.focus({ preventScroll: true });
    });
})();
