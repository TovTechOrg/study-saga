// DOM elements
const modal = document.getElementById('optionsModal');
const closeBtn = document.querySelector('.close');
const musicVolumeSlider = document.getElementById('musicVolume');
const sfxVolumeSlider = document.getElementById('sfxVolume');
const musicVolumeValue = document.getElementById('musicVolumeValue');
const sfxVolumeValue = document.getElementById('sfxVolumeValue');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Set up event listeners
    setupEventListeners();
    
    // Load current options
    loadOptions();
    
    // Add button click sound effect
    addButtonSoundEffects();
});

// Set up all event listeners
function setupEventListeners() {
    // Modal close functionality
    closeBtn.onclick = function() {
        modal.style.display = "none";
    }
    
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
    
    // Volume slider updates
    musicVolumeSlider.addEventListener('input', function() {
        musicVolumeValue.textContent = this.value + '%';
    });
    
    sfxVolumeSlider.addEventListener('input', function() {
        sfxVolumeValue.textContent = this.value + '%';
    });
}

// Add sound effects to buttons
function addButtonSoundEffects() {
    const buttons = document.querySelectorAll('.menu-btn');
    
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            // Create a simple click sound effect
            playButtonSound();
        });
    });
}

// Play button click sound
function playButtonSound() {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(400, audioContext.currentTime + 0.1);
    
    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.1);
}

// Start Game Function
async function startGame() {
    try {
        showLoadingState('start-btn', 'STARTING...');
        
        const response = await fetch('/api/start-game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccessMessage('Game started successfully!');
            // Here you can add logic to transition to the actual game
            setTimeout(() => {
                updateContentArea('Game is now running!', 'Enjoy your adventure!');
            }, 1000);
        } else {
            showErrorMessage('Failed to start game: ' + data.message);
        }
    } catch (error) {
        showErrorMessage('Error starting game: ' + error.message);
    } finally {
        resetButtonState('start-btn', 'START GAME');
    }
}

// Open Options Function
function openOptions() {
    modal.style.display = "block";
    loadOptions();
}

// Save Options Function
async function saveOptions() {
    try {
        const options = {
            difficulty: document.getElementById('difficulty').value,
            sound_enabled: document.getElementById('soundEnabled').checked,
            music_volume: parseInt(musicVolumeSlider.value) / 100,
            sfx_volume: parseInt(sfxVolumeSlider.value) / 100
        };
        
        const response = await fetch('/api/options', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(options)
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccessMessage('Options saved successfully!');
            modal.style.display = "none";
        } else {
            showErrorMessage('Failed to save options: ' + data.message);
        }
    } catch (error) {
        showErrorMessage('Error saving options: ' + error.message);
    }
}

// Cancel Game Function
async function cancelGame() {
    try {
        showLoadingState('cancel-btn', 'CANCELLING...');
        
        const response = await fetch('/api/cancel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccessMessage('Game cancelled successfully!');
            setTimeout(() => {
                updateContentArea('Game cancelled', 'Return to menu to start a new game');
            }, 1000);
        } else {
            showErrorMessage('Failed to cancel game: ' + data.message);
        }
    } catch (error) {
        showErrorMessage('Error cancelling game: ' + error.message);
    } finally {
        resetButtonState('cancel-btn', 'CANCEL');
    }
}

// Load current options from server
async function loadOptions() {
    try {
        const response = await fetch('/api/options');
        const data = await response.json();
        
        // Update form with current values
        document.getElementById('difficulty').value = data.difficulty[0];
        document.getElementById('soundEnabled').checked = data.sound_enabled;
        musicVolumeSlider.value = Math.round(data.music_volume * 100);
        sfxVolumeSlider.value = Math.round(data.sfx_volume * 100);
        musicVolumeValue.textContent = Math.round(data.music_volume * 100) + '%';
        sfxVolumeValue.textContent = Math.round(data.sfx_volume * 100) + '%';
    } catch (error) {
        console.error('Error loading options:', error);
    }
}

// Show loading state for buttons
function showLoadingState(buttonClass, text) {
    const button = document.querySelector('.' + buttonClass);
    const btnText = button.querySelector('.btn-text');
    btnText.textContent = text;
    button.disabled = true;
    button.style.opacity = '0.7';
}

// Reset button state
function resetButtonState(buttonClass, text) {
    const button = document.querySelector('.' + buttonClass);
    const btnText = button.querySelector('.btn-text');
    btnText.textContent = text;
    button.disabled = false;
    button.style.opacity = '1';
}

// Show success message
function showSuccessMessage(message) {
    const notification = createNotification(message, 'success');
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Show error message
function showErrorMessage(message) {
    const notification = createNotification(message, 'error');
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Create notification element
function createNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 2rem;
        border-radius: 10px;
        color: white;
        font-weight: 600;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    `;
    
    if (type === 'success') {
        notification.style.background = 'linear-gradient(45deg, #4CAF50, #45a049)';
    } else {
        notification.style.background = 'linear-gradient(45deg, #f44336, #d32f2f)';
    }
    
    return notification;
}

// Update main content area
function updateContentArea(title, description) {
    const welcomeText = document.querySelector('.welcome-text');
    welcomeText.innerHTML = `
        <h2>${title}</h2>
        <p>${description}</p>
    `;
}

// Add CSS animation for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);
