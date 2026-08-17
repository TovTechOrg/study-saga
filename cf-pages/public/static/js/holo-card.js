// Reusable holographic card component (player/opponent combat cards).
//
// Inspired by the general "pointer-tracked color-dodge card" technique
// popularized by Simon Goellner's Pokemon Cards Holo effect
// (github.com/simeydotme/pokemon-cards-css, GPL-3.0). That repo's code is
// NOT used here -- GPL-3.0 would obligate this closed commercial codebase
// to also be GPL-licensed. This is an original, independently-written
// implementation of the same general idea. See holo-card.css for the
// matching attribution note.
//
// Public API:
//   HoloCard.init(el, { opponent: bool })  -- wires up pointer/tilt tracking
//   HoloCard.pulse(el)                     -- correct-answer reaction
//   HoloCard.flash(el)                     -- wrong-answer reaction
//   HoloCard.setIntensity(el, streakCount) -- raises shine intensity with streaks
//   HoloCard.setLowEffects(bool)           -- perf toggle, persisted in localStorage

(function () {
    const LOW_EFFECTS_KEY = 'study_saga_low_effects';
    const prefersReducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function clamp(v, lo, hi) {
        return Math.max(lo, Math.min(hi, v));
    }

    function applyPointer(el, clientX, clientY) {
        const rect = el.getBoundingClientRect();
        const px = clamp((clientX - rect.left) / rect.width, 0, 1);
        const py = clamp((clientY - rect.top) / rect.height, 0, 1);
        const rx = (0.5 - py) * 14; // deg
        const ry = (px - 0.5) * 18; // deg
        el.style.setProperty('--holo-rx', rx.toFixed(2) + 'deg');
        el.style.setProperty('--holo-ry', ry.toFixed(2) + 'deg');
        el.style.setProperty('--holo-mx', (px * 100).toFixed(1) + '%');
        el.style.setProperty('--holo-my', (py * 100).toFixed(1) + '%');
    }

    function resetPointer(el) {
        el.style.setProperty('--holo-rx', '0deg');
        el.style.setProperty('--holo-ry', '0deg');
        el.style.setProperty('--holo-mx', '50%');
        el.style.setProperty('--holo-my', '50%');
    }

    function init(el, opts) {
        if (!el) return;
        opts = opts || {};
        el.classList.add('holo-card');
        if (opts.opponent) el.classList.add('holo-card--opponent');

        if (!el.querySelector('.holo-card__shine')) {
            const shine = document.createElement('div');
            shine.className = 'holo-card__shine';
            shine.setAttribute('aria-hidden', 'true');
            el.appendChild(shine);
        }
        if (!el.querySelector('.holo-card__glare')) {
            const glare = document.createElement('div');
            glare.className = 'holo-card__glare';
            glare.setAttribute('aria-hidden', 'true');
            el.appendChild(glare);
        }

        if (prefersReducedMotion) return; // static card, no pointer/tilt wiring

        let rafPending = false;
        let lastEvent = null;
        function onMove(e) {
            lastEvent = e;
            if (rafPending) return;
            rafPending = true;
            requestAnimationFrame(() => {
                rafPending = false;
                if (!lastEvent) return;
                const point = lastEvent.touches ? lastEvent.touches[0] : lastEvent;
                applyPointer(el, point.clientX, point.clientY);
            });
        }
        el.addEventListener('pointermove', onMove);
        el.addEventListener('pointerleave', () => resetPointer(el));

        // Progressive enhancement: device tilt on mobile.
        if (window.DeviceOrientationEvent) {
            window.addEventListener('deviceorientation', (e) => {
                if (e.beta == null || e.gamma == null) return;
                const rx = clamp(e.beta - 45, -20, 20) * 0.4;
                const ry = clamp(e.gamma, -20, 20) * 0.6;
                el.style.setProperty('--holo-rx', rx.toFixed(2) + 'deg');
                el.style.setProperty('--holo-ry', ry.toFixed(2) + 'deg');
            });
        }
    }

    function pulse(el) {
        if (!el || prefersReducedMotion) return;
        el.classList.remove('holo-pulse');
        // eslint-disable-next-line no-unused-expressions
        void el.offsetWidth; // restart animation
        el.classList.add('holo-pulse');
        setTimeout(() => el.classList.remove('holo-pulse'), 500);
    }

    function flash(el) {
        if (!el || prefersReducedMotion) return;
        el.classList.remove('holo-flash');
        void el.offsetWidth;
        el.classList.add('holo-flash');
        setTimeout(() => el.classList.remove('holo-flash'), 450);
    }

    function setIntensity(el, streakCount) {
        if (!el) return;
        const intensity = clamp(0.3 + (streakCount || 0) * 0.08, 0.3, 0.9);
        el.style.setProperty('--holo-intensity', intensity.toFixed(2));
    }

    function setLowEffects(on) {
        document.body.classList.toggle('holo-effects-off', !!on);
        try {
            localStorage.setItem(LOW_EFFECTS_KEY, on ? '1' : '0');
        } catch (e) {
            // localStorage unavailable (private browsing etc.) -- non-fatal.
        }
    }

    function initLowEffectsToggle(buttonEl) {
        let stored = '0';
        try {
            stored = localStorage.getItem(LOW_EFFECTS_KEY) || '0';
        } catch (e) {
            // ignore
        }
        setLowEffects(stored === '1');
        if (buttonEl) {
            buttonEl.textContent = stored === '1' ? 'Effects: Off' : 'Effects: On';
            buttonEl.addEventListener('click', () => {
                const isOff = document.body.classList.contains('holo-effects-off');
                setLowEffects(!isOff);
                buttonEl.textContent = !isOff ? 'Effects: Off' : 'Effects: On';
            });
        }
    }

    window.HoloCard = { init, pulse, flash, setIntensity, setLowEffects, initLowEffectsToggle };
})();
