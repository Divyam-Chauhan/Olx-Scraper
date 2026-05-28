// Connect UI Checkboxes to inputs
document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
        const bhk = e.target.value;
        const inputsDiv = document.getElementById(`price-inputs-${bhk}`);
        if (e.target.checked) {
            inputsDiv.classList.remove('disabled');
        } else {
            inputsDiv.classList.add('disabled');
        }
    });
});

// UI Elements
const terminal = document.getElementById('terminal');
const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const clearBtn = document.getElementById('clear-log-btn');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const captchaModal = document.getElementById('captcha-modal');
const resumeBtn = document.getElementById('resume-btn');

// Stats Elements
const statProcessed = document.getElementById('stat-processed');
const statSaved = document.getElementById('stat-saved');
const statDuplicates = document.getElementById('stat-duplicates');

function log(message, type = 'system') {
    const el = document.createElement('div');
    el.className = `log-line ${type}`;
    
    // Add timestamp
    const now = new Date();
    const time = now.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    el.innerText = `[${time}] ${message}`;
    terminal.appendChild(el);
    terminal.scrollTop = terminal.scrollHeight;
}

clearBtn.addEventListener('click', () => {
    terminal.innerHTML = '';
});

// Start Scraping
startBtn.addEventListener('click', async () => {
    // Gather config
    const config = {
        bhk_config: {},
        max_pages: parseInt(document.getElementById('max-pages').value) || 50
    };

    let hasSelected = false;
    for (let i = 1; i <= 3; i++) {
        const checkbox = document.getElementById(`bhk${i}`);
        if (checkbox.checked) {
            hasSelected = true;
            config.bhk_config[i.toString()] = {
                min: parseInt(document.getElementById(`min-${i}`).value) || 0,
                max: parseInt(document.getElementById(`max-${i}`).value) || 9999999
            };
        }
    }

    if (!hasSelected) {
        log("Please select at least one BHK type.", "warning");
        return;
    }

    startBtn.style.display = 'none';
    stopBtn.style.display = 'block';
    statusDot.className = 'dot running';
    statusText.innerText = 'Scraping...';
    
    // Reset stats
    statProcessed.innerText = '0';
    statSaved.innerText = '0';
    statDuplicates.innerText = '0';
    
    log("Starting scraper...", "info");
    
    // Call Python backend
    await eel.start_scraping(config)();
});

// Stop Scraping
stopBtn.addEventListener('click', () => {
    log("Sending stop signal...", "warning");
    eel.stop_scraping()();
    resetUI();
});

// Resume from Captcha
resumeBtn.addEventListener('click', () => {
    captchaModal.classList.remove('active');
    log("Resuming execution...", "info");
    statusDot.className = 'dot running';
    statusText.innerText = 'Scraping...';
    eel.resume_scraping()();
});

// --- Callbacks from Python ---

eel.expose(log_message);
function log_message(message, type) {
    log(message, type);
}

eel.expose(update_stats);
function update_stats(processed, saved, duplicates) {
    statProcessed.innerText = processed;
    statSaved.innerText = saved;
    statDuplicates.innerText = duplicates;
}

eel.expose(on_scraping_finished);
function on_scraping_finished(message) {
    log(message, "success");
    resetUI();
}

eel.expose(trigger_captcha_modal);
function trigger_captcha_modal() {
    captchaModal.classList.add('active');
    statusDot.className = 'dot warning';
    statusText.innerText = 'CAPTCHA Blocked';
    log("CAPTCHA or Block detected! Waiting for user resolution.", "warning");
}

function resetUI() {
    startBtn.style.display = 'block';
    stopBtn.style.display = 'none';
    statusDot.className = 'dot';
    statusText.innerText = 'Ready';
}
