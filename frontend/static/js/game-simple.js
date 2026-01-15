console.log('=== GAME SCRIPT V10 LOADED ===');
console.log('selectSyllabus function:', typeof window.selectSyllabus);

// Make sure these are globally accessible
window.startGame = startGame;
window.selectSyllabus = selectSyllabus;

console.log('After assignment - selectSyllabus:', typeof window.selectSyllabus);

// Start game function
async function startGame() {
    console.log('Starting game...');
    
    try {
        const response = await fetch('/api/start-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        console.log('Game started:', data);
        
        if (data.status === 'success' && data.game_id) {
            window.gameId = data.game_id;
            
            // Load syllabi
            const syllResponse = await fetch('/api/syllabi');
            const syllData = await syllResponse.json();
            console.log('Syllabi loaded:', syllData);
            
            if (syllData.status === 'success') {
                // Hide main menu, show syllabus screen
                document.getElementById('main-menu').style.display = 'none';
                document.getElementById('syllabus-screen').style.display = 'block';
                
                // Render syllabi cards
                const grid = document.getElementById('syllabi-grid');
                grid.innerHTML = '';
                
                syllData.syllabi.forEach(syllabus => {
                    const card = document.createElement('div');
                    card.className = 'syllabus-card';
                    
                    const realm = document.createElement('span');
                    realm.className = 'syllabus-realm';
                    realm.textContent = syllabus.name;
                    
                    const title = document.createElement('h3');
                    title.textContent = syllabus.name;
                    
                    const desc = document.createElement('p');
                    desc.textContent = syllabus.description;
                    
                    const button = document.createElement('button');
                    button.textContent = 'Initialize Sync';
                    console.log('Creating button for ' + syllabus.name + ', selectSyllabus type:', typeof selectSyllabus);
                    button.onclick = function() {
                        console.log('Button clicked for ' + syllabus.name);
                        selectSyllabus(syllabus.id);
                    };
                    
                    card.appendChild(realm);
                    card.appendChild(title);
                    card.appendChild(desc);
                    card.appendChild(button);
                    grid.appendChild(card);
                });
            }
        } else {
            alert('Error: Failed to start game');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error: ' + error.message);
    }
}

// Select syllabus function
async function selectSyllabus(syllabusId) {
    console.log('=== INITIALIZE SYNC CLICKED! ===');
    console.log('Syllabus ID:', syllabusId);
    console.log('Game ID:', window.gameId);
    
    if (!window.gameId) {
        console.error('Error: No game ID found');
        alert('Error: No game ID found. Please restart from main menu.');
        return;
    }
    
    try {
        const requestBody = {
            game_id: window.gameId,
            syllabus_id: syllabusId,
            enemy_id: 'misconception_golem'
        };
        console.log('Request body:', requestBody);
        
        const response = await fetch('/api/start-combat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Combat response:', data);
        
        if (data.status === 'success') {
            console.log('Combat started successfully!');
            // Hide syllabus, show combat
            document.getElementById('syllabus-screen').style.display = 'none';
            document.getElementById('combat-screen').style.display = 'block';
            
            // Store combat state
            window.combatState = data.combat_state;
            
            // Update HUD
            updateCombatHUD(data.combat_state);
            console.log('Combat screen should be visible now');
        } else {
            console.error('Combat start failed:', data);
            alert('Failed to start combat: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error starting combat:', error);
        alert('Error: ' + error.message);
    }
}

// Update combat HUD
function updateCombatHUD(state) {
    document.getElementById('player-hp').textContent = `${state.player.current_hp}/${state.player.max_hp}`;
    document.getElementById('player-hp-bar').style.width = `${(state.player.current_hp / state.player.max_hp) * 100}%`;
    
    document.getElementById('player-cap').textContent = `${state.player.current_cap}/${state.player.max_cap}`;
    document.getElementById('player-cap-bar').style.width = `${(state.player.current_cap / state.player.max_cap) * 100}%`;
    
    document.getElementById('enemy-name').textContent = state.enemy.name;
    document.getElementById('enemy-hp').textContent = `${state.enemy.current_hp}/${state.enemy.max_hp}`;
    document.getElementById('enemy-hp-bar').style.width = `${(state.enemy.current_hp / state.enemy.max_hp) * 100}%`;
}

console.log('All game functions defined!');
