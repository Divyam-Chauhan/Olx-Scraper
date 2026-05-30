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

// BYOU URL Elements
const locationUrlInput = document.getElementById('location-url');
const urlStatus = document.getElementById('url-status');
const urlHint = document.getElementById('url-hint');
const howToBtn = document.getElementById('how-to-btn');
const guideModal = document.getElementById('guide-modal');
const closeGuideBtn = document.getElementById('close-guide-modal');

// DB Modal Elements
const dbModal = document.getElementById('db-modal');
const viewDbBtn = document.getElementById('view-db-btn');
const closeDbModalBtn = document.getElementById('close-db-modal');
const dbTableBody = document.getElementById('db-table-body');

// Stats Elements
const statProcessed = document.getElementById('stat-processed');
const statSaved = document.getElementById('stat-saved');
const statDuplicates = document.getElementById('stat-duplicates');

let activeRunStage = 'idle';

function setActiveRunState(status, dotClass = 'dot running', stopLabel = 'Stop Scraping') {
    activeRunStage = status;
    startBtn.disabled = true;
    startBtn.classList.add('is-loading');
    startBtn.style.display = 'none';
    stopBtn.disabled = false;
    stopBtn.innerText = stopLabel;
    stopBtn.style.display = 'block';
    statusDot.className = dotClass;
    statusText.innerText = status;
}

// === URL Validator ===
function validateOlxUrl(url) {
    if (!url) return { valid: false, location: null, cleanUrl: null };
    
    // Match geographic node pattern: anything_gXXXXXX
    const geoMatch = url.match(/\/([a-z0-9-]+_g\d+)\//i);
    if (!geoMatch) return { valid: false, location: null, cleanUrl: null };
    
    // Extract the geographic slug
    const geoSlug = geoMatch[1];
    
    // Make the location name readable: "sundarpur_g5343637" -> "Sundarpur"
    const locationName = geoSlug
        .split('_g')[0]
        .replace(/-/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
    
    // Build a clean base URL from the geo slug
    const cleanUrl = `https://www.olx.in/en-in/${geoSlug}/for-rent-houses-apartments_c1723`;
    
    return { valid: true, location: locationName, cleanUrl: cleanUrl };
}

// Live URL validation on input
locationUrlInput.addEventListener('input', () => {
    const val = locationUrlInput.value.trim();
    if (!val) {
        locationUrlInput.classList.remove('valid', 'invalid');
        urlStatus.textContent = '';
        urlHint.textContent = 'Paste the URL from OLX after selecting your exact neighborhood from the sidebar.';
        urlHint.className = '';
        return;
    }
    
    const result = validateOlxUrl(val);
    if (result.valid) {
        locationUrlInput.classList.add('valid');
        locationUrlInput.classList.remove('invalid');
        urlStatus.textContent = '\u2705';
        urlHint.textContent = `\u2705 Location Detected: ${result.location}`;
        urlHint.className = 'valid';
    } else {
        locationUrlInput.classList.add('invalid');
        locationUrlInput.classList.remove('valid');
        urlStatus.textContent = '\u274C';
        urlHint.textContent = '\u274C Invalid URL \u2014 make sure you select a neighborhood from the sidebar, not the search bar.';
        urlHint.className = 'invalid';
    }
});

// === Guide Modal ===
howToBtn.addEventListener('click', () => {
    guideModal.classList.add('active');
});
closeGuideBtn.addEventListener('click', () => {
    guideModal.classList.remove('active');
});

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
    const rawUrl = locationUrlInput.value.trim();
    const result = validateOlxUrl(rawUrl);
    
    if (!rawUrl || !result.valid) {
        log("Please paste a valid OLX location URL. Click 'How to get this?' for help.", "error");
        return;
    }

    // Gather config
    const config = {
        geo_url: result.cleanUrl,
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

    setActiveRunState('Preparing browser...', 'dot warning', 'Cancel Setup');

    // Reset stats
    statProcessed.innerText = '0';
    statSaved.innerText = '0';
    statDuplicates.innerText = '0';
    
    log(`Preparing scraper for: ${result.location}...`, "info");
    
    // Call Python backend
    try {
        await eel.start_scraping(config)();
    } catch (error) {
        log(`Could not start scraper: ${error}`, "error");
        resetUI();
    }
});

// Stop Scraping
stopBtn.addEventListener('click', () => {
    log("Sending stop signal...", "warning");
    setActiveRunState('Stopping...', 'dot warning', 'Stopping...');
    stopBtn.disabled = true;
    eel.stop_scraping()();
});

// Resume from Captcha
resumeBtn.addEventListener('click', () => {
    captchaModal.style.display = 'none';
    eel.resume_scraping();
    log("Resumed scraping.", "info");
});

// Database Viewer Logic

const renderDatabaseTable = (rows) => {
    dbTableBody.innerHTML = '';
    if (rows.length === 0) {
        dbTableBody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No listings found in database.</td></tr>';
        document.getElementById('delete-selected-btn').style.display = 'none';
        return;
    }

    rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="text-align:center;"><input type="checkbox" class="db-row-checkbox" value="${row.id}"></td>
            <td>${row.bhk}</td>
            <td><strong>${row.price}</strong></td>
            <td>${row.seller_type}</td>
            <td>${row.furnishing}</td>
            <td>${row.posted_date}</td>
            <td>${row.title}</td>
            <td><a href="${row.url}" target="_blank" class="table-link">View Ad</a></td>
        `;
        dbTableBody.appendChild(tr);
    });

    // Wire up row checkboxes to show/hide delete button
    const rowCheckboxes = document.querySelectorAll('.db-row-checkbox');
    const selectAllCheckbox = document.getElementById('select-all-db');
    const deleteBtn = document.getElementById('delete-selected-btn');
    
    selectAllCheckbox.checked = false;
    deleteBtn.style.display = 'none';

    const updateDeleteBtn = () => {
        const checkedCount = document.querySelectorAll('.db-row-checkbox:checked').length;
        deleteBtn.style.display = checkedCount > 0 ? 'block' : 'none';
        deleteBtn.innerText = `Delete Selected (${checkedCount})`;
        selectAllCheckbox.checked = checkedCount === rowCheckboxes.length && rowCheckboxes.length > 0;
    };

    rowCheckboxes.forEach(cb => cb.addEventListener('change', updateDeleteBtn));

    selectAllCheckbox.addEventListener('change', (e) => {
        rowCheckboxes.forEach(cb => cb.checked = e.target.checked);
        updateDeleteBtn();
    });
};

const loadDatabase = async () => {
    // Show loading state
    dbTableBody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Loading database...</td></tr>';
    document.getElementById('select-all-db').checked = false;
    document.getElementById('delete-selected-btn').style.display = 'none';

    // Fetch data from python backend
    const rows = await eel.fetch_database()();
    renderDatabaseTable(rows);
};

// Database Viewer Logic
viewDbBtn.addEventListener('click', async () => {
    dbModal.classList.add('active');
    await loadDatabase();
});

// Delete Selected Logic
document.getElementById('delete-selected-btn').addEventListener('click', async () => {
    const selectedIds = Array.from(document.querySelectorAll('.db-row-checkbox:checked'))
                            .map(cb => parseInt(cb.value));
    
    if (selectedIds.length === 0) return;

    if (confirm(`Are you sure you want to delete ${selectedIds.length} listings?`)) {
        await eel.delete_selected_listings(selectedIds)();
        await loadDatabase(); // Refresh table
    }
});

closeDbModalBtn.addEventListener('click', () => {
    dbModal.classList.remove('active');
});

// Close modals when clicking outside
window.addEventListener('click', (event) => {
    if (event.target == dbModal) {
        dbModal.classList.remove('active');
    }
    if (event.target == guideModal) {
        guideModal.classList.remove('active');
    }
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

eel.expose(on_browser_setup_started);
function on_browser_setup_started() {
    setActiveRunState('Preparing browser...', 'dot warning', 'Cancel Setup');
    log("Preparing Playwright browser...", "info");
}

eel.expose(on_browser_setup_progress);
function on_browser_setup_progress(message) {
    if (message.toLowerCase().includes('download')) {
        setActiveRunState('Downloading browser...', 'dot warning', 'Cancel Download');
    }
    log(message, "info");
}

eel.expose(on_browser_setup_finished);
function on_browser_setup_finished() {
    setActiveRunState('Browser ready...', 'dot running', 'Stop Scraping');
}

eel.expose(on_browser_setup_failed);
function on_browser_setup_failed(message) {
    const type = message.toLowerCase().includes('cancel') ? "warning" : "error";
    log(message, type);
    resetUI();
}

eel.expose(on_scraper_started);
function on_scraper_started() {
    setActiveRunState('Scraping...', 'dot running', 'Stop Scraping');
    log("Browser ready. Starting scraper...", "info");
}

eel.expose(trigger_captcha_modal);
function trigger_captcha_modal() {
    captchaModal.classList.add('active');
    statusDot.className = 'dot warning';
    statusText.innerText = 'CAPTCHA Blocked';
    log("CAPTCHA or Block detected! Waiting for user resolution.", "warning");
}

function resetUI() {
    activeRunStage = 'idle';
    startBtn.style.display = 'block';
    startBtn.disabled = false;
    startBtn.classList.remove('is-loading');
    stopBtn.style.display = 'none';
    stopBtn.disabled = false;
    stopBtn.innerText = 'Stop Scraping';
    statusDot.className = 'dot';
    statusText.innerText = 'Ready';
}
