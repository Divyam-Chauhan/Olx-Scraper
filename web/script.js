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

    startBtn.style.display = 'none';
    stopBtn.style.display = 'block';
    statusDot.className = 'dot running';
    statusText.innerText = 'Scraping...';

    // Reset stats
    statProcessed.innerText = '0';
    statSaved.innerText = '0';
    statDuplicates.innerText = '0';
    
    log(`Starting scraper for: ${result.location}...`, "info");
    
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
    captchaModal.style.display = 'none';
    eel.resume_scraping();
    log("Resumed scraping.", "info");
});

// Database Viewer Logic
viewDbBtn.addEventListener('click', async () => {
    // Show modal and loading state
    dbModal.classList.add('active');
    dbTableBody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Loading database...</td></tr>';

    // Fetch data from python backend
    const rows = await eel.fetch_database()();

    // Render table
    dbTableBody.innerHTML = '';
    if (rows.length === 0) {
        dbTableBody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No listings found in database.</td></tr>';
        return;
    }

    rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
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
