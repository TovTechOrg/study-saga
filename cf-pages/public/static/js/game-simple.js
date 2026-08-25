// Placeholder: the real showFeedbackModal is defined further below.
// This stub prevents errors if called before the real one is ready.
function showFeedbackModal(feedback, onClose) {
    // Will be overridden by the real definition below.
    const msg = typeof feedback === 'string' ? feedback : (feedback.message || '');
    alert(msg);
    if (onClose) onClose();
}

// Comic-caption-style battle log entries (Epic #11 / issues #18, #19): one
// shared helper so every turn outcome -- attack, ability, recharge, and
// in-combat errors -- renders the same narrated way instead of some paths
// using plain text divs and others falling through to a bare alert(). Tone
// is inferred from the message text itself (backend already writes
// narrated strings like "X grows emboldened..."), not from separate flags,
// so this stays a pure presentation layer -- no combat-numbers change.
function addBattleLogEntry(message, { isCorrect } = {}) {
    const log = document.getElementById('battle-log-content');
    if (!log || !message) return;

    let tone = 'system';
    let burst = null;
    if (/^correct!/i.test(message)) {
        tone = 'correct';
    } else if (/^incorrect\./i.test(message)) {
        tone = 'incorrect';
    } else if (typeof isCorrect === 'boolean') {
        tone = isCorrect ? 'correct' : 'incorrect';
    }
    if (/emboldened/i.test(message)) {
        tone = 'crit';
        burst = 'Heavy Hit';
    } else if (/hesitates/i.test(message)) {
        tone = 'falter';
        burst = 'Falters';
    }

    const entry = document.createElement('div');
    entry.className = `battle-log-entry tone-${tone}`;
    if (burst) {
        const burstEl = document.createElement('span');
        burstEl.className = `battle-log-burst ${tone}`;
        burstEl.textContent = burst;
        entry.appendChild(burstEl);
    }
    entry.appendChild(document.createTextNode(message));
    log.prepend(entry);
}

// Consolidated game logic from inline script in index.html
// All functions and event handlers are now in this file

// Test that script is loading
console.log('DOM READY (external)');
document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('deploy-btn');
    const grid = document.getElementById('syllabi-grid');
    if (btn) {
        console.log('Found Deploy System button');
        btn.addEventListener('click', () => {
            // Removed alert for Deploy System button
            console.log('Deploy System button click event fired');
            startGame();
        });
    } else {
        console.log('Button NOT found');
    }

    // Delegate clicks in case cards/buttons are rebuilt
    if (grid) {
        grid.addEventListener('click', function (e) {
            const button = e.target.closest('button[data-syllabus-id]');
            if (button) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Delegated click for syllabus (button):', button.dataset.syllabusId);
                onSyllabusClick({ currentTarget: button });
                return;
            }
            const card = e.target.closest('.syllabus-card');
            if (card && card.dataset.syllabusId) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Delegated click for syllabus (card):', card.dataset.syllabusId);
                // Clicking the card body itself (not a specific difficulty
                // button) has no difficulty to read -- default to medium.
                selectSyllabus(card.dataset.syllabusId, 'medium');
            }
        });
    }

    // Robust event delegation for combat action buttons
    const combatHud = document.querySelector('.combat-hud-outer');
    if (combatHud) {
        combatHud.addEventListener('click', function (e) {
            const btn = e.target.closest('.neural-action-btn');
            if (!btn || !combatHud.contains(btn) || btn.disabled) return;
            if (btn.id === 'attack-btn') {
                console.log('Attack button clicked!');
                performAction('attack');
            } else if (btn.id === 'defend-btn') {
                performAction('recharge');
            } else if (btn.id === 'skill-btn') {
                performAction('ability');
            }
        });
    }

    // Quiz modal's Close control was previously dead markup with no handler.
    const closeQuizBtn = document.getElementById('close-quiz-btn');
    if (closeQuizBtn) closeQuizBtn.addEventListener('click', closeQuizModal);

    // Persistent nav (issue #7): Home always abandons progress, so confirm first.
    const navHomeBtn = document.getElementById('game-nav-home-btn');
    if (navHomeBtn) {
        navHomeBtn.addEventListener('click', function () {
            if (confirm('Return to the main menu? This will abandon your current progress.')) {
                resetGame();
            }
        });
    }

    const signInBtn = document.getElementById('sign-in-btn');
    if (signInBtn) {
        signInBtn.addEventListener('click', function () {
            if (window.currentUser) {
                window.studySagaSignOut();
            } else if (window.studySagaSignIn) {
                clearAuthError();
                window.studySagaSignIn().catch((e) => {
                    console.error('Sign-in failed:', e);
                    showAuthError(e);
                });
            }
        });
    }

    window.addEventListener('studysaga-auth-changed', function (e) {
        handleAuthChanged(e.detail.user);
    });
    window.addEventListener('studysaga-auth-error', function (e) {
        console.error('Sign-in failed:', e.detail.error);
        showAuthError(e.detail.error);
    });
});

// ---------------------------------------------------------------------------
// Inline sign-in error display (issue #8) -- replaces alert() with a message
// next to the sign-in button, styled to match the terminal theme. Firebase
// error `.code` values are mapped to plain-language copy; anything
// unrecognized falls back to a generic message rather than leaking the raw
// Firebase error string to players.
// ---------------------------------------------------------------------------
const AUTH_ERROR_MESSAGES = {
    'auth/unauthorized-domain': "Sign-in isn't available on this site yet. (This domain hasn't been approved for sign-in -- let us know.)",
    'auth/popup-blocked': 'Your browser blocked the sign-in popup. Please allow popups for this site, or try again.',
    'auth/popup-closed-by-user': 'Sign-in was cancelled.',
    'auth/cancelled-popup-request': 'Sign-in was cancelled.',
    'auth/network-request-failed': 'Network error -- check your connection and try again.',
};

function showAuthError(error) {
    const el = document.getElementById('auth-status-error');
    if (!el) return;
    el.textContent = AUTH_ERROR_MESSAGES[error && error.code] || 'Sign-in failed. Please try again.';
    el.style.display = 'block';
}

function clearAuthError() {
    const el = document.getElementById('auth-status-error');
    if (!el) return;
    el.style.display = 'none';
    el.textContent = '';
}

// ---------------------------------------------------------------------------
// Firebase auth (optional sign-in for cross-device progress saves).
// index.html's module script exposes studySagaSignIn/SignOut on window and
// dispatches 'studysaga-auth-changed' on state changes -- game-simple.js is
// a plain classic script, so it listens for that rather than importing the
// SDK directly.
// ---------------------------------------------------------------------------
async function getIdToken() {
    if (!window.currentUser) return null;
    try {
        return await window.currentUser.getIdToken();
    } catch (e) {
        console.error('Failed to get ID token:', e);
        return null;
    }
}

async function handleAuthChanged(user) {
    window.currentUser = user;
    const signInBtn = document.getElementById('sign-in-btn');
    const caption = document.getElementById('auth-status-caption');
    if (user) {
        clearAuthError();
        if (signInBtn) signInBtn.textContent = 'Sign out';
        if (caption) caption.textContent = `Signed in as ${user.displayName || user.email}`;

        // Check for a game already in progress on another device.
        const idToken = await getIdToken();
        try {
            const res = await fetch('/api/auth-resume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id_token: idToken }),
            });
            const data = await res.json();
            if (data.status === 'resumed' && confirm('You have a game in progress. Resume it?')) {
                window.gameId = data.game_id;
                window.combatState = data.combat_state;
                document.getElementById('main-menu').style.display = 'none';
                const combatScreen = document.getElementById('combat-screen');
                combatScreen.style.display = 'block';
                combatScreen.style.visibility = 'visible';
                showGameNav((data.combat_state.syllabus_id || '').charAt(0).toUpperCase() + (data.combat_state.syllabus_id || '').slice(1));
                updateCombatHUD(data.combat_state);
                updateHintsBar(data.hints);
            }
        } catch (e) {
            console.error('auth-resume check failed:', e);
        }
    } else {
        if (signInBtn) signInBtn.textContent = 'Sign in with Google';
        if (caption) caption.textContent = 'Sign in to save your progress across devices';
    }
}

// ---------------------------------------------------------------------------
// Persistent navigation bar (issue #7)
// ---------------------------------------------------------------------------
function showGameNav(realmText) {
    const nav = document.getElementById('game-nav');
    if (!nav) return;
    nav.style.display = 'flex';
    const realmEl = document.getElementById('game-nav-realm');
    if (realmEl) realmEl.textContent = realmText || '';
}

function hideGameNav() {
    const nav = document.getElementById('game-nav');
    if (nav) nav.style.display = 'none';
}

// ---------------------------------------------------------------------------
// Focus trap for modals (issue #5) -- nothing like this existed before;
// used by both the quiz modal and the feedback modal.
// ---------------------------------------------------------------------------
function trapFocus(modalEl, onEscape) {
    const focusable = Array.from(
        modalEl.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
    ).filter(el => !el.disabled && el.offsetParent !== null);

    function handleKeydown(e) {
        if (e.key === 'Escape' && onEscape) {
            e.preventDefault();
            onEscape();
            return;
        }
        if (e.key !== 'Tab' || focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    }

    modalEl.addEventListener('keydown', handleKeydown);
    // Calling .focus() right after classList.add('active') is silently
    // ignored -- confirmed via instrumentation that getComputedStyle(modal)
    // still reports visibility:hidden even a full animation frame later,
    // since the modal's opacity/visibility change is behind a CSS
    // transition that hasn't resolved yet. Wait for the transition to
    // actually finish (with a timeout fallback in case transitionend never
    // fires) rather than guessing at a frame count.
    if (focusable.length) {
        let focused = false;
        function focusFirst() {
            if (focused) return;
            focused = true;
            focusable[0].focus();
        }
        modalEl.addEventListener('transitionend', focusFirst, { once: true });
        setTimeout(focusFirst, 450);
    }
    return () => modalEl.removeEventListener('keydown', handleKeydown);
}

function deactivateModal(modal) {
    modal.classList.remove('active');
    if (modal._releaseFocusTrap) {
        modal._releaseFocusTrap();
        modal._releaseFocusTrap = null;
    }
    if (modal._previouslyFocused && typeof modal._previouslyFocused.focus === 'function') {
        modal._previouslyFocused.focus();
    }
}

function closeQuizModal() {
    const modal = document.getElementById('quiz-modal');
    if (modal) deactivateModal(modal);
}

// ---------------------------------------------------------------------------
// Math notation normalizer + KaTeX render (issue #5). The question corpus
// mixes plain-ASCII conventions (caret exponents, underscore subscripts,
// slash fractions) -- this only converts clearly-recognizable patterns into
// KaTeX's $...$ delimiters, left conservative on purpose since the corpus
// wasn't authored with a renderer in mind and a wrong parse is worse than
// leaving ambiguous text alone.
// ---------------------------------------------------------------------------
function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function normalizeMathText(text) {
    if (!text) return text;
    let result = escapeHtml(text);
    result = result.replace(/\b(\d{1,3})\/(\d{1,3})\b/g, (m, a, b) => `$\\frac{${a}}{${b}}$`);
    result = result.replace(/([A-Za-z0-9])\^(-?\d+|[A-Za-z])/g, (m, base, exp) => `$${base}^{${exp}}$`);
    result = result.replace(/([A-Za-z])_([A-Za-z0-9]+)/g, (m, base, sub) => `$${base}_{${sub}}$`);
    return result;
}

function renderMathIn(el) {
    if (window.renderMathInElement) {
        try {
            renderMathInElement(el, { delimiters: [{ left: '$', right: '$', display: false }], throwOnError: false });
        } catch (e) {
            console.warn('KaTeX render failed', e);
        }
    }
}

function setStatus(message) {
    const el = document.getElementById('test-output');
    if (el) el.textContent = message;
}

function handleInvalidSession(message) {
    console.warn('Invalid session detected:', message);
    alert(message || 'Session expired. Click Deploy System to relaunch.');
    window.gameId = null;
    window.combatState = null;

    // Close modal if open
    const modal = document.getElementById('quiz-modal');
    if (modal) deactivateModal(modal);

    // Hide all secondary screens
    ['syllabus-screen', 'combat-screen', 'victory-screen', 'defeat-screen'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    // Show main menu and re-enable deploy
    const mainMenu = document.getElementById('main-menu');
    if (mainMenu) mainMenu.style.display = 'block';
    const deploy = document.getElementById('deploy-btn');
    if (deploy) deploy.disabled = false;
    hideGameNav();
    setStatus('Session expired. Click Deploy System to relaunch.');
}

async function startGame() {
    console.log('startGame called');
    if (window.__startingGame) {
        console.log('startGame already in progress');
        return;
    }
    window.__startingGame = true;
    const btn = document.getElementById('deploy-btn');
    if (btn) btn.disabled = true;
    setStatus('Starting...');
    try {
        const idToken = await getIdToken();
        const response = await fetch('/api/start-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_token: idToken }),
        });
        const data = await response.json();
        console.log('Game started:', data);
        if (data.status === 'success' && data.game_id) {
            window.gameId = data.game_id;
            setStatus('Loading realms...');
            const syllResponse = await fetch('/api/syllabi');
            const syllData = await syllResponse.json();
            console.log('Syllabi loaded:', syllData);
            if (syllData.status === 'success') {
                document.getElementById('main-menu').style.display = 'none';
                document.getElementById('syllabus-screen').style.display = 'block';
                showGameNav('');
                const grid = document.getElementById('syllabi-grid');
                grid.innerHTML = '';
                syllData.syllabi.forEach(syllabus => {
                    const card = document.createElement('div');
                    card.className = 'syllabus-card';
                    card.dataset.syllabusId = syllabus.id;
                    // Keyboard-operable (issue #3): this was a plain div with only
                    // a click listener, unreachable by keyboard.
                    card.setAttribute('tabindex', '0');
                    card.setAttribute('role', 'button');
                    card.setAttribute('aria-label', `${syllabus.name} realm -- ${syllabus.description}`);
                    // Eyebrow now says "Realm" instead of repeating the syllabus
                    // name a second time right above the <h3> (issue #4 bug).
                    card.innerHTML = `<span class="syllabus-realm">Realm</span><h3>${syllabus.name}</h3><p>${syllabus.description}</p>`;
                    // Difficulty is chosen once here, before combat starts, and
                    // locked in for the whole battle (not a per-turn toggle) --
                    // three buttons instead of one "Initialize Sync" button.
                    const difficultyRow = document.createElement('div');
                    difficultyRow.className = 'syllabus-difficulty-picker';
                    ['easy', 'medium', 'hard'].forEach(diff => {
                        const button = document.createElement('button');
                        button.type = 'button';
                        button.className = `difficulty-btn difficulty-${diff}`;
                        button.textContent = diff.charAt(0).toUpperCase() + diff.slice(1);
                        button.dataset.syllabusId = syllabus.id;
                        button.dataset.difficulty = diff;
                        button.setAttribute('data-syllabus-id', syllabus.id);
                        button.setAttribute('aria-label', `${syllabus.name}, ${diff} difficulty`);
                        button.addEventListener('click', onSyllabusClick);
                        difficultyRow.appendChild(button);
                    });
                    card.addEventListener('click', function (e) {
                        // If a difficulty button was clicked, let its own handler run
                        if (e.target.closest('button')) return;
                        console.log('Card click handler for', syllabus.id, '-- defaulting to medium');
                        selectSyllabus(syllabus.id, 'medium');
                    });
                    card.addEventListener('keydown', function (e) {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            selectSyllabus(syllabus.id, 'medium');
                        }
                    });
                    const caption = document.createElement('p');
                    caption.className = 'neural-btn-caption';
                    caption.textContent = 'Choose a difficulty to begin this realm';
                    card.appendChild(difficultyRow);
                    card.appendChild(caption);
                    grid.appendChild(card);
                    console.log('Created difficulty buttons for:', syllabus.id);
                });
                setStatus('Select a realm to sync');
            } else {
                setStatus('Failed to load syllabi');
                console.error('Syllabi load failed', syllData);
            }
        } else {
            setStatus('Failed to start game');
            console.error('Start game failed', data);
        }
    } catch (e) {
        console.error(e);
        setStatus('Error: ' + e.message);
    } finally {
        if (btn) btn.disabled = false;
        window.__startingGame = false;
    }
}

function onSyllabusClick(e) {
    const id = e.currentTarget.dataset.syllabusId;
    const difficulty = e.currentTarget.dataset.difficulty || 'medium';
    if (!id) {
        console.warn('Difficulty button clicked but no syllabus id found');
        return;
    }
    console.log('Difficulty button clicked:', id, difficulty);
    selectSyllabus(id, difficulty);
}

async function selectSyllabus(id, difficulty) {
    difficulty = ['easy', 'medium', 'hard'].includes(difficulty) ? difficulty : 'medium';
    console.log('=== selectSyllabus called for:', id, 'difficulty:', difficulty);
    if (window.__startingCombat) {
        console.log('Combat start already in progress');
        return;
    }
    window.__startingCombat = true;
    const gridButtons = document.querySelectorAll('#syllabi-grid button');
    gridButtons.forEach(b => b.disabled = true);

    try {
        if (!window.gameId) {
            console.warn('No gameId; starting new game');
            await startGame();
            if (!window.gameId) throw new Error('No game session established');
        }

        console.log('POST /api/start-combat with gameId:', window.gameId);
        const response = await fetch('/api/start-combat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_id: window.gameId, syllabus_id: id, enemy_id: 'misconception_golem', difficulty })
        });
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Response data:', JSON.stringify(data, null, 2));

        if (data.game_id) window.gameId = data.game_id;

        if (data.status === 'success') {
            console.log('SUCCESS - switching screens');
            const mainMenu = document.getElementById('main-menu');
            const syllScreen = document.getElementById('syllabus-screen');
            const combatScreen = document.getElementById('combat-screen');

            mainMenu.style.display = 'none';
            syllScreen.style.display = 'none';
            // NOT 'flex': #combat-screen has no flex CSS of its own -- setting
            // display:flex here turned .combat-hud-outer and #battle-log-content
            // (each independently centered via their own CSS) into side-by-side
            // flex row items instead, which was the actual cause of the
            // "everything pushed left, log floating at top-right" layout bug.
            combatScreen.style.display = 'block';
            combatScreen.style.visibility = 'visible';
            const difficultyLabel = difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
            showGameNav(`${id.charAt(0).toUpperCase() + id.slice(1)} · ${difficultyLabel}`);

            // Force a reflow to ensure DOM updates
            void combatScreen.offsetHeight;

            window.combatState = data.combat_state;
            updateCombatHUD(data.combat_state);
            updateHintsBar(data.hints);
            console.log('Combat screen display:', window.getComputedStyle(combatScreen).display);
            console.log('Combat screen is now visible');
        } else {
            console.error('FAILED - status is not success:', data.status);
            alert('Failed: ' + (data.message || JSON.stringify(data)));
        }
    } catch (e) {
        console.error('EXCEPTION:', e);
        alert('Error: ' + e.message);
    } finally {
        gridButtons.forEach(b => b.disabled = false);
        window.__startingCombat = false;
    }
}

function updateCombatHUD(state) {
    document.getElementById('player-hp').textContent = `${state.player.current_hp}/${state.player.max_hp}`;
    document.getElementById('player-hp-bar-inner').style.width = `${(state.player.current_hp / state.player.max_hp) * 100}%`;
    document.getElementById('player-cap').textContent = `${state.player.current_cap}/${state.player.max_cap}`;
    document.getElementById('player-cap-bar-inner').style.width = `${(state.player.current_cap / state.player.max_cap) * 100}%`;
    document.getElementById('enemy-name').textContent = state.enemy.name;
    document.getElementById('enemy-hp').textContent = `${state.enemy.current_hp}/${state.enemy.max_hp}`;
    document.getElementById('enemy-hp-bar-inner').style.width = `${(state.enemy.current_hp / state.enemy.max_hp) * 100}%`;
    const resolve = state.enemy.resolve ?? 50;
    const maxResolve = state.enemy.max_resolve ?? 100;
    document.getElementById('enemy-resolve').textContent = `${resolve}/${maxResolve}`;
    document.getElementById('enemy-resolve-bar-inner').style.width = `${(resolve / maxResolve) * 100}%`;

    // Update button states based on CAP
    const cap = state.player.current_cap;
    const btnAttack = document.getElementById('attack-btn');
    const btnSkill = document.getElementById('skill-btn');
    const btnDefend = document.getElementById('defend-btn');

    if (btnAttack) {
        const canAfford = cap >= 3;
        btnAttack.disabled = !canAfford;
        btnAttack.style.opacity = canAfford ? '1' : '0.5';
        btnAttack.style.cursor = canAfford ? 'pointer' : 'not-allowed';
    }
    if (btnSkill) {
        const canAfford = cap >= 5;
        btnSkill.disabled = !canAfford;
        btnSkill.style.opacity = canAfford ? '1' : '0.5';
        btnSkill.style.cursor = canAfford ? 'pointer' : 'not-allowed';
    }
    if (btnDefend) {
        btnDefend.disabled = false;
        btnDefend.style.opacity = '1';
        btnDefend.style.cursor = 'pointer';
    }
}

function updateHintsBar(hints) {
    if (!hints) return;
    window.hintsState = hints;
    const simpleEl = document.getElementById('hints-simple-remaining');
    const hardEl = document.getElementById('hints-hard-remaining');
    const creditsEl = document.getElementById('hints-credits');
    if (simpleEl) simpleEl.textContent = hints.simple_remaining;
    if (hardEl) hardEl.textContent = hints.hard_remaining;
    if (creditsEl) creditsEl.textContent = hints.credits;
}

function renderLevelResults(containerId, results) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!results || !results.length) {
        container.innerHTML = '';
        return;
    }
    container.innerHTML = results.map(r => `
        <div class="level-result-entry ${r.correct ? 'correct' : 'incorrect'}">
            <span class="result-icon">${r.correct ? '✓' : '✗'}</span>
            <span>${r.text}</span>
        </div>
    `).join('');
}

function pushRecentMessages(messages) {
    const list = document.getElementById('recent-results-list');
    if (!list || !messages) return;
    const entries = Array.from(messages).map(msg => {
        const div = document.createElement('div');
        div.className = 'recent-list-entry';
        div.textContent = msg;
        return div;
    });
    entries.reverse().forEach(entry => list.prepend(entry));
    while (list.children.length > 6) list.removeChild(list.lastChild);
}

// Combat action handler wired to backend
async function performAction(action) {
    console.log('Action clicked:', action);
    const buttons = document.querySelectorAll('.neural-action-btn');
    buttons.forEach(b => b.disabled = true);

    try {
        if (!window.gameId) {
            handleInvalidSession('Session missing. Click Deploy System to relaunch.');
            return;
        }

        const response = await fetch('/api/combat-action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_id: window.gameId, action })
        });
        const data = await response.json();
        console.log('combat-action result:', data);

        if ((data.message || '').toLowerCase().includes('invalid game session')) {
            handleInvalidSession(data.message);
            return;
        }

        if (data.status === 'question') {
            // Show quiz modal and wait for user answer
            console.log('[DEBUG] performAction received data:', data);
            openQuizModal(data.question, action);
            return; // keep buttons disabled until answer resolves
        } else if (data.status === 'success') {
            if (data.combat_state) {
                window.combatState = data.combat_state;
                updateCombatHUD(data.combat_state);
            }
            updateHintsBar(data.hints);
            (data.messages || []).forEach(msg => addBattleLogEntry(msg, { isCorrect: data.is_correct }));
            pushRecentMessages(data.messages || []);

            if (data.outcome === 'victory') {
                const combat = document.getElementById('combat-screen');
                const victory = document.getElementById('victory-screen');
                renderLevelResults('victory-results-list', data.level_results);
                if (combat && victory) {
                    combat.classList.remove('active');
                    victory.classList.add('active');
                    // Still hide combat screen display to be safe
                    setTimeout(() => combat.style.display = 'none', 800);
                }
            } else if (data.outcome === 'defeat') {
                const combat = document.getElementById('combat-screen');
                const defeat = document.getElementById('defeat-screen');
                renderLevelResults('defeat-results-list', data.level_results);
                if (combat && defeat) {
                    combat.classList.remove('active');
                    defeat.classList.add('active');
                    setTimeout(() => combat.style.display = 'none', 800);
                }
            }
        } else {
            addBattleLogEntry(data.message || 'Action failed.');
        }
    } catch (e) {
        console.error('combat-action error:', e);
        addBattleLogEntry('Error: ' + e.message);
    } finally {
        // Re-enable buttons unless game ended
        const victoryVisible = document.getElementById('victory-screen')?.style.display === 'flex';
        const defeatVisible = document.getElementById('defeat-screen')?.style.display === 'flex';
        if (!victoryVisible && !defeatVisible) {
            if (window.combatState) {
                updateCombatHUD(window.combatState);
            } else {
                buttons.forEach(b => b.disabled = false);
            }
        }
    }
}

function openQuizModal(question, action) {
    console.log('[DEBUG] openQuizModal called with:', question, action);
    console.log('[DEBUG] Full question object:', question);
    console.log('Opening quiz for action:', action, 'question:', question);
    console.log('Question type:', question?.type, 'isMulti check:', question?.type === 'multiple_choice_multiple');
    // Prevent duplicate modals
    const modal = document.getElementById('quiz-modal');
    const qEl = document.getElementById('quiz-question');
    const optsEl = document.getElementById('quiz-options');
    if (!modal || !qEl || !optsEl) {
        console.warn('Quiz modal elements missing');
        return;
    }
    // Rebuild content and (re-)activate unconditionally. A guard here that
    // bailed when the modal was already "active" used to mean: if that class
    // ever failed to clear (a race with the feedback modal, a stale state),
    // every subsequent question would silently fail to display -- the
    // "Attack button doesn't do anything" symptom. Re-rendering is always
    // safe since we rebuild qEl/optsEl from scratch below regardless.
    optsEl.innerHTML = '';
    modal.classList.add('active');
    qEl.innerHTML = normalizeMathText(question?.text) || 'Answer the question to proceed.';
    renderMathIn(qEl);
    optsEl.innerHTML = '';
    // Add hint box directly below question
    let hintBox = document.getElementById('hint-box');
    if (!hintBox) {
        hintBox = document.createElement('div');
        hintBox.id = 'hint-box';
        hintBox.className = 'hint-box';
        qEl.parentNode.insertBefore(hintBox, qEl.nextSibling);
    }
    // Sean's suggestion: don't auto-reveal hints -- the player must explicitly
    // request one. Only fetch from the backend once they click a button.
    // Two separate hint tiers, each with its own per-game budget (see
    // hints-budget-bar): Simple (easy tier only, 3/game) and Deep (all three
    // tiers, 1/game). Correct answers earn credits that unlock more of either.
    const optionsArray = (question?.options || []).map(opt => opt.text || String(opt));
    function requestHint(tier) {
        hintBox.textContent = 'Loading hint...';
        fetch('/api/get-hint', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question?.text || '', options: optionsArray, game_id: window.gameId, tier })
        })
            .then(res => res.json())
            .then(data => {
                updateHintsBar(data.hints);
                if (data.status === 'blocked') {
                    hintBox.textContent = data.message || 'No hints left.';
                    return;
                }
                if (data.status === 'success') {
                    let hint = data.hint;
                    let parsed = null;
                    try {
                        if (typeof hint === 'string') {
                            parsed = JSON.parse(hint);
                        } else if (typeof hint === 'object' && hint !== null) {
                            parsed = hint;
                        }
                    } catch (e) {
                        parsed = null;
                    }
                    if (parsed && (parsed.hard || parsed.medium || parsed.easy)) {
                        // Progressive reveal within whichever tiers this request unlocked
                        const tiers = [];
                        if (parsed.hard) tiers.push({ label: 'Hard', text: parsed.hard, color: '#ff6b6b' });
                        if (parsed.medium) tiers.push({ label: 'Medium', text: parsed.medium, color: '#ffd93d' });
                        if (parsed.easy) tiers.push({ label: 'Easy', text: parsed.easy, color: '#6bff6b' });

                        let currentTier = 0;
                        function renderHints() {
                            let html = '';
                            for (let i = 0; i <= currentTier && i < tiers.length; i++) {
                                html += `<div style="margin-bottom:8px;"><b style="color:${tiers[i].color}">${tiers[i].label}:</b> ${tiers[i].text}</div>`;
                            }
                            if (currentTier < tiers.length - 1) {
                                html += `<button id="reveal-next-hint" class="neural-btn" style="margin-top:6px;padding:6px 16px;font-size:0.9em;opacity:0.85;">Need More Help?</button>`;
                            }
                            hintBox.innerHTML = html;
                            const revealBtn = document.getElementById('reveal-next-hint');
                            if (revealBtn) {
                                revealBtn.addEventListener('click', function () {
                                    currentTier++;
                                    renderHints();
                                });
                            }
                        }
                        renderHints();
                    } else {
                        hintBox.textContent = hint;
                    }
                } else {
                    hintBox.textContent = 'No hint available.';
                }
            })
            .catch((err) => {
                hintBox.textContent = 'No hint available.';
            });
    }
    hintBox.innerHTML = `
        <button id="request-simple-hint-btn" class="neural-btn" style="padding:6px 16px;font-size:0.9em;opacity:0.85;">Simple Hint</button>
        <button id="request-hard-hint-btn" class="neural-btn" style="padding:6px 16px;font-size:0.9em;opacity:0.85;margin-left:8px;">Deep Hint</button>
    `;
    const simpleBtn = document.getElementById('request-simple-hint-btn');
    if (simpleBtn) simpleBtn.addEventListener('click', () => requestHint('simple'), { once: true });
    const hardBtn = document.getElementById('request-hard-hint-btn');
    if (hardBtn) hardBtn.addEventListener('click', () => requestHint('hard'), { once: true });
    const options = question?.options || [];
    const isMulti = question?.type === 'multiple_choice_multiple';
    if (!options.length) {
        optsEl.innerHTML = '<div style="color: red; font-size: 1.2em; font-weight: bold;">ERROR: No answer options found for this question.<br>Check backend response and question format.</div>';
        return;
    }
    optsEl.className = 'quiz-options-grid';
    if (!isMulti) {
        options.forEach((opt, idx) => {
            const btn = document.createElement('button');
            btn.className = 'answer-btn';
            btn.setAttribute('data-idx', idx);
            btn.innerHTML = normalizeMathText(opt?.text || String(opt));
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                e.preventDefault();
                // Immediate visual feedback while the response is in flight
                // (issue #5's "selected" state) -- correct/incorrect isn't
                // shown here since the quiz modal hides as soon as the
                // feedback modal takes over, so there's no visible moment
                // to show those states meaningfully.
                optsEl.querySelectorAll('.answer-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                const idx = parseInt(btn.getAttribute('data-idx'));
                submitQuizAnswer(action, idx, btn);
            });
            optsEl.appendChild(btn);
        });
    } else {
        options.forEach((opt, idx) => {
            const label = document.createElement('label');
            label.className = 'quiz-option-label';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = idx;
            checkbox.id = `quiz-opt-${idx}`;
            const span = document.createElement('span');
            span.innerHTML = normalizeMathText(opt?.text || String(opt));
            label.appendChild(checkbox);
            label.appendChild(span);
            optsEl.appendChild(label);
        });
        const submitBtn = document.createElement('button');
        submitBtn.className = 'neural-btn';
        submitBtn.textContent = 'Submit Answers';
        submitBtn.style.marginTop = '1rem';
        submitBtn.onclick = () => {
            const selected = Array.from(optsEl.querySelectorAll('input[type="checkbox"]:checked')).map(cb => parseInt(cb.value));
            submitQuizAnswerMulti(action, selected);
        };
        optsEl.appendChild(submitBtn);
    }
    renderMathIn(optsEl);

    // Focus trap (issue #5): set up last, once every focusable control
    // (hint buttons, answer options, close button) actually exists in the DOM.
    modal._previouslyFocused = document.activeElement;
    modal._releaseFocusTrap = trapFocus(modal, closeQuizModal);
}

async function submitQuizAnswer(action, answerIndex) {
    console.log('Submitting quiz answer', answerIndex, 'for action', action);
    const modal = document.getElementById('quiz-modal');
    const buttons = document.querySelectorAll('.neural-action-btn');
    buttons.forEach(b => b.disabled = true);

    try {
        console.log('[DEBUG] Sending quiz answer to backend:', { game_id: window.gameId, action, answer_index: answerIndex });
        const response = await fetch('/api/combat-action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_id: window.gameId, action, answer_index: answerIndex })
        });
        const data = await response.json();
        console.log('[DEBUG] combat-action graded result:', data);

        if ((data.message || '').toLowerCase().includes('invalid game session')) {
            handleInvalidSession(data.message);
            return;
        }

        // Always update HUD if combat_state is present
        if (data.combat_state) {
            window.combatState = data.combat_state;
            updateCombatHUD(data.combat_state);
        }
        updateHintsBar(data.hints);
        console.log('[DEBUG] submitQuizAnswer called');
        // Determine correctness if possible
        let isCorrect = false;
        if (typeof data.correct !== 'undefined') {
            isCorrect = data.correct;
        } else if (typeof data.is_correct !== 'undefined') {
            isCorrect = data.is_correct;
        } else if (typeof data.status !== 'undefined' && data.status === 'correct') {
            isCorrect = true;
        }
        // issue #18: this single-select path (the most common one) never
        // wrote anything to the battle log -- the multi-select path did.
        // Same treatment as the other two combat-action response sites.
        (data.messages || []).forEach(msg => addBattleLogEntry(msg, { isCorrect }));
        pushRecentMessages(data.messages || []);
        // Always show feedback modal after answer submission
        let feedbackMsg = "Answer submitted! Await further results or check the game log for more info.";
        if (data.messages && data.messages.length > 0) {
            feedbackMsg = data.messages[0];
        } else if (data.message) {
            feedbackMsg = data.message;
        }
        // Hide quiz modal before showing feedback
        if (modal) closeQuizModal();
        showFeedbackModal({ message: feedbackMsg, correct: isCorrect }, () => {
            // After closing feedback, advance as needed
            if (data.outcome === 'victory') {
                // #victory-screen is opacity:0/visibility:hidden by default and only
                // becomes visible via the 'active' class (see style-neural.css) --
                // setting style.display='flex' alone (as this used to) leaves it
                // permanently invisible. This was the single-select path; the
                // multi-select path already did this correctly.
                const combat = document.getElementById('combat-screen');
                const victory = document.getElementById('victory-screen');
                renderLevelResults('victory-results-list', data.level_results);
                if (combat && victory) {
                    combat.classList.remove('active');
                    victory.classList.add('active');
                    setTimeout(() => combat.style.display = 'none', 800);
                }
            } else if (data.outcome === 'defeat') {
                const combat = document.getElementById('combat-screen');
                const defeat = document.getElementById('defeat-screen');
                renderLevelResults('defeat-results-list', data.level_results);
                if (combat && defeat) {
                    combat.classList.remove('active');
                    defeat.classList.add('active');
                    setTimeout(() => combat.style.display = 'none', 800);
                }
            } else if (data.status === 'question' && data.question) {
                // Show next question after feedback is dismissed
                openQuizModal(data.question, action);
            }
        });
        if (data.status === 'error') {
            addBattleLogEntry(data.message || 'Action failed.');
        } else if (!(data.combat_state || data.status === 'question' || data.status === 'error')) {
            console.warn('[DEBUG] Unexpected backend response:', data);
        }
    } catch (e) {
        console.error('submitQuizAnswer error:', e);
        addBattleLogEntry('Error: ' + e.message);
    } finally {
        const victoryVisible = document.getElementById('victory-screen')?.style.display === 'flex';
        const defeatVisible = document.getElementById('defeat-screen')?.style.display === 'flex';
        if (!victoryVisible && !defeatVisible) {
            if (window.combatState) {
                updateCombatHUD(window.combatState);
            } else {
                buttons.forEach(b => b.disabled = false);
            }
        }
    }
}

async function submitQuizAnswerMulti(action, answerIndices) {
    console.log('Submitting multi-select quiz answers', answerIndices, 'for action', action);
    const modal = document.getElementById('quiz-modal');
    const buttons = document.querySelectorAll('.neural-action-btn');
    buttons.forEach(b => b.disabled = true);

    try {
        const response = await fetch('/api/combat-action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_id: window.gameId, action, answer_indices: answerIndices })
        });
        const data = await response.json();
        console.log('combat-action graded multi result:', data);

        if ((data.message || '').toLowerCase().includes('invalid game session')) {
            handleInvalidSession(data.message);
            return;
        }

        // Determine correctness from backend response
        let isCorrect = false;
        if (typeof data.correct !== 'undefined') {
            isCorrect = data.correct;
        } else if (typeof data.is_correct !== 'undefined') {
            isCorrect = data.is_correct;
        } else if (data.status === 'correct') {
            isCorrect = true;
        }

        if (data.combat_state) {
            window.combatState = data.combat_state;
            updateCombatHUD(data.combat_state);
        }
        updateHintsBar(data.hints);

        (data.messages || []).forEach(msg => addBattleLogEntry(msg, { isCorrect }));
        pushRecentMessages(data.messages || []);

        if (data.status === 'error') {
            addBattleLogEntry(data.message || 'Action failed.');
        } else {
            // Always show feedback modal with correct/incorrect styling
            let feedbackMsg = "Answer submitted! Await further results or check the game log for more info.";
            if (data.messages && data.messages.length > 0) {
                feedbackMsg = data.messages.join('\n');
            } else if (data.message) {
                feedbackMsg = data.message;
            }
            // Hide quiz modal before showing feedback. Must use classList (matching
            // submitQuizAnswer's single-select path), NOT modal.style.display='none':
            // the modal's show/hide is driven by opacity/visibility via the 'active'
            // class (display stays 'flex' always per the stylesheet). Setting an
            // inline display:none here permanently overrides that stylesheet rule --
            // nothing later ever clears the inline style, so openQuizModal()'s
            // classList.add('active') stops being able to show the modal at all for
            // the rest of the session, the instant a player answers ANY multi-select
            // question. This was the real cause of "Attack stops working."
            if (modal) closeQuizModal();
            showFeedbackModal({ message: feedbackMsg, correct: isCorrect }, () => {
                if (data.outcome === 'victory') {
                    const combat = document.getElementById('combat-screen');
                    const victory = document.getElementById('victory-screen');
                    renderLevelResults('victory-results-list', data.level_results);
                    if (combat && victory) {
                        combat.classList.remove('active');
                        victory.classList.add('active');
                        setTimeout(() => combat.style.display = 'none', 800);
                    }
                } else if (data.outcome === 'defeat') {
                    const combat = document.getElementById('combat-screen');
                    const defeat = document.getElementById('defeat-screen');
                    renderLevelResults('defeat-results-list', data.level_results);
                    if (combat && defeat) {
                        combat.classList.remove('active');
                        defeat.classList.add('active');
                        setTimeout(() => combat.style.display = 'none', 800);
                    }
                } else if (data.status === 'question' && data.question) {
                    openQuizModal(data.question, action);
                }
            });
        }
    } catch (e) {
        console.error('submitQuizAnswerMulti error:', e);
        addBattleLogEntry('Error: ' + e.message);
    } finally {
        const victoryVisible = document.getElementById('victory-screen')?.style.display === 'flex';
        const defeatVisible = document.getElementById('defeat-screen')?.style.display === 'flex';
        if (!victoryVisible && !defeatVisible) {
            if (window.combatState) {
                updateCombatHUD(window.combatState);
            } else {
                buttons.forEach(b => b.disabled = false);
            }
        }
    }
}
// Show feedback modal with message, then call callback after close
function showFeedbackModal(feedback, onClose) {
    console.log('[DEBUG] showFeedbackModal called with:', feedback);
    let modal = document.getElementById('feedback-modal');
    if (!modal) {
        // Create modal if missing
        const modalDiv = document.createElement('div');
        modalDiv.id = 'feedback-modal';
        modalDiv.className = 'modal';
        modalDiv.style.display = 'flex';
        modalDiv.innerHTML = `
            <div class="modal-content" style="z-index: 10001; background: #182033; border-radius: 12px; box-shadow: 0 0 32px #00eaffcc; padding: 2rem 2.5rem; min-width: 320px; text-align: center;">
                <h3 id="feedback-title" style="color: #9ad1ff; font-size: 1.5em; margin-bottom: 1rem;">Feedback</h3>
                <div id="feedback-message" style="color: #fff; font-size: 1.2em; margin-bottom: 1.5rem;"></div>
                <button id="close-feedback-btn" class="neural-btn" style="margin-top: 1rem;">Close</button>
            </div>
            <div style="position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.55);z-index:10000;"></div>
        `;
        document.body.appendChild(modalDiv);
        modal = modalDiv;
    }
    const msgEl = document.getElementById('feedback-message');
    const titleEl = document.getElementById('feedback-title');
    const closeBtnEl = document.getElementById('close-feedback-btn');
    // Set feedback message (handle string or object)
    const isObject = typeof feedback === 'object' && feedback !== null;
    const msgText = isObject ? (feedback.message || '') : String(feedback);
    if (msgEl) {
        // Escape HTML then convert newlines to <br> for multi-line display
        const escaped = msgText.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        msgEl.innerHTML = escaped.replace(/\n/g, '<br>');
    }
    // Style for correct/incorrect
    if (modal) {
        modal.classList.add('active');
        modal.classList.remove('good', 'bad');
        if (isObject && typeof feedback.correct !== 'undefined') {
            modal.classList.add(feedback.correct ? 'good' : 'bad');
            if (titleEl) titleEl.textContent = feedback.correct ? '✅ Correct!' : '❌ Incorrect';
            if (window.HoloCard) {
                const playerCard = document.getElementById('player-card');
                const enemyCard = document.getElementById('enemy-card');
                if (feedback.correct) {
                    window._holoStreak = (window._holoStreak || 0) + 1;
                    window.HoloCard.pulse(playerCard);
                    window.HoloCard.setIntensity(playerCard, window._holoStreak);
                } else {
                    window._holoStreak = 0;
                    window.HoloCard.flash(enemyCard);
                    window.HoloCard.setIntensity(playerCard, 0);
                }
            }
        } else {
            if (titleEl) titleEl.textContent = 'Feedback';
        }
    }
    function closeFeedbackModal() {
        if (modal) deactivateModal(modal);
        if (onClose) onClose();
    }
    if (modal) {
        modal._previouslyFocused = document.activeElement;
        modal._releaseFocusTrap = trapFocus(modal, closeFeedbackModal);
    }
    // Remove any previous event listeners by cloning the node
    if (closeBtnEl) {
        const newBtn = closeBtnEl.cloneNode(true);
        closeBtnEl.parentNode.replaceChild(newBtn, closeBtnEl);
        newBtn.addEventListener('click', closeFeedbackModal);
    }
}

// Expose showFeedbackModal globally IMMEDIATELY so it is always available
window.showFeedbackModal = showFeedbackModal;

// Expose globally for inline onclick handlers
window.performAction = performAction;

// Make it global so HTML onclick works
window.startGame = startGame;
window.selectSyllabus = selectSyllabus;
// Reset game session and return to main menu
async function resetGame() {
    console.log('Reset requested');
    if (window.__resetting) return;
    window.__resetting = true;

    // Disable action buttons during reset
    const buttons = document.querySelectorAll('.neural-action-btn');
    buttons.forEach(b => b.disabled = true);

    try {
        const body = window.gameId ? { game_id: window.gameId } : {};
        const response = await fetch('/api/reset-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await response.json();
        console.log('reset-game result:', data);

        if (data.status === 'success') {
            // Update session id and HUD
            if (data.game_id) window.gameId = data.game_id;
            if (data.combat_state) updateCombatHUD(data.combat_state);

            // Clear battle log
            const log = document.getElementById('battle-log-content');
            if (log) log.innerHTML = '';

            // Close any modals (release any focus trap left attached if the
            // player abandoned progress mid-quiz via the nav Home button)
            const quizModal = document.getElementById('quiz-modal');
            if (quizModal) deactivateModal(quizModal);
            const feedbackModal = document.getElementById('feedback-modal');
            if (feedbackModal) deactivateModal(feedbackModal);

            // Hide secondary screens and show main menu.
            // victory/defeat screens use the opacity/visibility + .active-class
            // system (see style-neural.css), NOT inline display -- setting
            // style.display here would permanently block them from ever
            // reappearing via classList.add('active') on a later game.
            ['syllabus-screen', 'combat-screen'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            });
            ['victory-screen', 'defeat-screen'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.classList.remove('active');
            });
            const mainMenu = document.getElementById('main-menu');
            if (mainMenu) mainMenu.style.display = 'block';
            const deploy = document.getElementById('deploy-btn');
            if (deploy) deploy.disabled = false;
            hideGameNav();
            setStatus('Session reset. Click Deploy System to start!');
        } else {
            alert(data.message || 'Reset failed');
        }
    } catch (e) {
        console.error('reset-game error:', e);
        alert('Error: ' + e.message);
    } finally {
        window.__resetting = false;
        // Re-enable buttons on main menu
        const victoryVisible = document.getElementById('victory-screen')?.style.display === 'flex';
        const defeatVisible = document.getElementById('defeat-screen')?.style.display === 'flex';
        if (!victoryVisible && !defeatVisible) {
            buttons.forEach(b => b.disabled = false);
        }
    }
}

function backToMenu() {
    // Route endgame buttons to reset for a clean slate
    resetGame();
}

// Expose globals
window.resetGame = resetGame;
window.backToMenu = backToMenu;
