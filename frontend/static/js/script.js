/**
 * MODULE 2: Frontend Script - Options & Utility Functions
 * Main game logic is in models.js
 */

// Setup options modal
function setupOptionsModal() {
    const modal = document.getElementById('optionsModal');
    const closeBtn = document.querySelector('#optionsModal .close');
    const musicVolumeSlider = document.getElementById('musicVolume');
    const sfxVolumeSlider = document.getElementById('sfxVolume');
    const musicVolumeValue = document.getElementById('musicVolumeValue');
    const sfxVolumeValue = document.getElementById('sfxVolumeValue');

    // Close modal
    if (closeBtn) {
        closeBtn.onclick = function() {
            modal.style.display = "none";
        }
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    // Volume slider updates
    if (musicVolumeSlider) {
        musicVolumeSlider.addEventListener('input', function() {
            musicVolumeValue.textContent = this.value + '%';
        });
    }

    if (sfxVolumeSlider) {
        sfxVolumeSlider.addEventListener('input', function() {
            sfxVolumeValue.textContent = this.value + '%';
        });
    }
}

// Load options from localStorage
function loadOptions() {
    const difficulty = localStorage.getItem('difficulty') || 'Medium';
    const soundEnabled = localStorage.getItem('soundEnabled') !== 'false';
    const musicVolume = localStorage.getItem('musicVolume') || '70';
    const sfxVolume = localStorage.getItem('sfxVolume') || '80';

    const difficultySelect = document.getElementById('difficulty');
    const soundCheckbox = document.getElementById('soundEnabled');
    const musicVolumeSlider = document.getElementById('musicVolume');
    const sfxVolumeSlider = document.getElementById('sfxVolume');
    const musicVolumeValue = document.getElementById('musicVolumeValue');
    const sfxVolumeValue = document.getElementById('sfxVolumeValue');

    if (difficultySelect) difficultySelect.value = difficulty;
    if (soundCheckbox) soundCheckbox.checked = soundEnabled;
    if (musicVolumeSlider) musicVolumeSlider.value = musicVolume;
    if (sfxVolumeSlider) sfxVolumeSlider.value = sfxVolume;
    if (musicVolumeValue) musicVolumeValue.textContent = musicVolume + '%';
    if (sfxVolumeValue) sfxVolumeValue.textContent = sfxVolume + '%';
}

// Save options to localStorage
function saveOptions() {
    const difficultySelect = document.getElementById('difficulty');
    const soundCheckbox = document.getElementById('soundEnabled');
    const musicVolumeSlider = document.getElementById('musicVolume');
    const sfxVolumeSlider = document.getElementById('sfxVolume');

    if (difficultySelect) localStorage.setItem('difficulty', difficultySelect.value);
    if (soundCheckbox) localStorage.setItem('soundEnabled', soundCheckbox.checked);
    if (musicVolumeSlider) localStorage.setItem('musicVolume', musicVolumeSlider.value);
    if (sfxVolumeSlider) localStorage.setItem('sfxVolume', sfxVolumeSlider.value);

    alert('Options saved!');
    const modal = document.getElementById('optionsModal');
    if (modal) modal.style.display = "none";
}

// Play button click sound
function playButtonSound() {
    try {
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
    } catch (e) {
        // Audio context may not be available
    }
}
