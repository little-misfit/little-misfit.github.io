(() => {
    const dialog = document.querySelector('.photo-viewer');
    if (!dialog || typeof dialog.showModal !== 'function') return;

    const image = dialog.querySelector('.viewer-image');
    const caption = dialog.querySelector('#viewer-caption');
    const count = dialog.querySelector('.viewer-count');
    const status = dialog.querySelector('.viewer-status');
    const previous = dialog.querySelector('[data-photo-step="-1"]');
    const next = dialog.querySelector('[data-photo-step="1"]');
    const closeButton = dialog.querySelector('.viewer-close');
    let photos = [];
    let current = 0;
    let trigger;

    function showPhoto(index) {
        if (index < 0 || index >= photos.length) return;
        current = index;
        const photo = photos[current];
        image.hidden = true;
        status.hidden = false;
        status.textContent = 'Loading photo…';
        caption.textContent = photo.dataset.caption || photo.querySelector('img').alt;
        count.textContent = `${current + 1} / ${photos.length}`;
        const focused = document.activeElement;
        previous.disabled = current === 0;
        next.disabled = current === photos.length - 1;
        if (focused === previous && previous.disabled) {
            (next.disabled ? closeButton : next).focus({ preventScroll: true });
        } else if (focused === next && next.disabled) {
            (previous.disabled ? closeButton : previous).focus({ preventScroll: true });
        }
        image.alt = photo.querySelector('img').alt;
        image.src = photo.href;
    }

    image.addEventListener('load', () => {
        image.hidden = false;
        status.hidden = true;
    });
    image.addEventListener('error', () => {
        image.hidden = true;
        status.hidden = false;
        status.textContent = 'This photo could not be loaded.';
    });
    document.querySelectorAll('.event-photo').forEach(photo => {
        photo.addEventListener('click', event => {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            trigger = photo;
            photos = [...photo.closest('.event-gallery').querySelectorAll('.event-photo')];
            showPhoto(photos.indexOf(photo));
            document.body.classList.add('viewer-open');
            dialog.showModal();
        });
    });
    closeButton.addEventListener('click', () => dialog.close());
    dialog.querySelectorAll('[data-photo-step]').forEach(button => {
        button.addEventListener('click', () => showPhoto(current + Number(button.dataset.photoStep)));
    });
    dialog.addEventListener('keydown', event => {
        if (event.key === 'Tab') {
            const controls = [...dialog.querySelectorAll('button:not(:disabled)')];
            const first = controls[0];
            const last = controls[controls.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
            event.preventDefault();
            showPhoto(current + (event.key === 'ArrowRight' ? 1 : -1));
        }
    });
    dialog.addEventListener('click', event => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
    });
    dialog.addEventListener('close', () => {
        // Native close events are queued; a new viewer may already be open.
        if (dialog.open) return;
        document.body.classList.remove('viewer-open');
        image.removeAttribute('src');
        trigger?.focus({ preventScroll: true });
    });
})();
