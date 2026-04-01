// --- STATE & DATA ---
let currentUser = JSON.parse(localStorage.getItem('cycura_user')) || null;
let currentDate = new Date();
let myChart = null;

// --- DOM ELEMENTS ---
const views = {
    getStarted: document.getElementById('view-get-started'),
    home: document.getElementById('view-home'),
    trackHub: document.getElementById('view-track-hub'),
    menstrual: document.getElementById('view-menstrual'),
    settings: document.getElementById('view-settings')
};

const nav = document.getElementById('mainNav');
const dateDisplay = document.getElementById('currentDateDisplay');
const diaryEntry = document.getElementById('diaryEntry');


// --- INITIALIZATION ---
// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("App Initialized");

    // Setup Form Listener
    const getStartedForm = document.getElementById('getStartedForm');
    const getStartedBtn = getStartedForm ? getStartedForm.querySelector('button') : null;

    function handleLogin(e) {
        if (e) e.preventDefault();
        console.log("Login attempted");

        const name = document.getElementById('gsName').value;
        const dob = document.getElementById('gsDob').value;
        const age = document.getElementById('gsAge').value;
        const gender = document.getElementById('gsGender').value;

        console.log("Details:", { name, dob, age, gender });

        if (name && dob && age) {
            currentUser = { name, dob, age, gender };
            localStorage.setItem('cycura_user', JSON.stringify(currentUser));
            initApp();
        } else {
            alert("Please fill in all fields.");
        }
    }

    if (getStartedForm) {
        getStartedForm.addEventListener('submit', handleLogin);
    }

    // Explicit button click listener as backup
    if (getStartedBtn) {
        getStartedBtn.addEventListener('click', (e) => {
            // Only manual trigger if type="button" or if form submit fails
            // But since it's type="submit", we let the form handle it usually.
            // However, to be safe against weird bubbling issues:
            // logic is in handleLogin.
        });
    }

    if (!currentUser) {
        switchView('view-get-started');
    } else {
        initApp();
    }
});

function initApp() {
    console.log("Initializing App...");

    // 1. Setup UI with User Data
    document.getElementById('displayUser').textContent = `Welcome, ${currentUser.name.split(' ')[0]}`;
    document.getElementById('displayAvatar').textContent = currentUser.name.charAt(0).toUpperCase();

    // 2. Setup Gender Logic in Hub
    // Hide Menstrual Track if Gender is NOT Female
    if (currentUser.gender === 'Male' || currentUser.gender === 'Other') {
        document.getElementById('btn-open-menstrual').classList.add('hidden');
    } else {
        document.getElementById('btn-open-menstrual').classList.remove('hidden');
    }

    // 3. Load Diary for Today
    renderCalendarStrip(currentDate);
    loadDiary(currentDate);

    // 4. Check for Persisted Menstrual Data
    const dataStr = localStorage.getItem(`cycura_data_${currentUser.name}`);
    if (dataStr) {
        try {
            const data = JSON.parse(dataStr);
            renderDashboard(data);

            // Switch generated view state
            if (uploadSection) uploadSection.classList.add('hidden');
            if (resultsDashboard) resultsDashboard.classList.remove('hidden');
            if (document.getElementById('reUploadBtn')) document.getElementById('reUploadBtn').style.display = 'block';
        } catch (e) {
            console.error("Failed to restore data", e);
        }
    }

    // 5. Start at Home
    switchView('view-home');
}

// --- NAVIGATION & ROUTING ---
function switchView(viewId) {
    // Hide all views
    Object.values(views).forEach(el => {
        el.classList.add('hidden');
        el.classList.remove('page'); // Reset animation trigger
    });

    // Reset any open flip cards when leaving a view
    if (typeof resetFlipCards === 'function') resetFlipCards();

    // Show target
    const target = document.getElementById(viewId);
    target.classList.remove('hidden');
    target.classList.add('page'); // Trigger animation

    // Render Settings if active
    if (viewId === 'view-settings') {
        renderSettings();
    }

    // Handle Bottom Nav Visibility
    // Handle Bottom Nav Visibility
    // Handle Bottom Nav Visibility
    if (viewId === 'view-get-started' || viewId === 'view-menstrual') {
        nav.classList.add('hidden');
    } else {
        nav.classList.remove('hidden');
        // Update active state
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.target === viewId);
        });
    }
}

// LOGOUT LOGIC
document.getElementById('logoutBtn').addEventListener('click', () => {
    if (confirm("Are you sure you want to log out? This will clear your session.")) {
        localStorage.removeItem('cycura_user');
        currentUser = null;
        switchView('view-get-started');
        showToast("Logged out successfully.");
    }
});

// Bottom Nav Click
document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        if (!currentUser) return;
        switchView(btn.dataset.target);
    });
});

// Back to Hub Logic
document.getElementById('backToHub').addEventListener('click', () => {
    switchView('view-track-hub');
});

// Open Menstrual View
document.getElementById('btn-open-menstrual').addEventListener('click', () => {
    switchView('view-menstrual');
    loadMenstrualData();
});


// Re-upload Logic
document.getElementById('reUploadBtn').addEventListener('click', () => {
    if (confirm("Upload new data? This will replace your current analysis.")) {
        localStorage.removeItem(`cycura_data_${currentUser.name}`);
        resetUploadUI(); // Show upload, hide dash
        document.getElementById('reUploadBtn').style.display = 'none';

        // Ensure dash is hidden
        uploadSection.classList.remove('hidden');
        resultsDashboard.classList.add('hidden');
    }
});

function loadMenstrualData() {
    const key = `cycura_data_${currentUser.name}`;
    const savedData = localStorage.getItem(key);

    if (savedData) {
        const data = JSON.parse(savedData);
        renderDashboard(data);

        // UI State: Show Dash, Hide Upload
        uploadSection.classList.add('hidden');
        resultsDashboard.classList.remove('hidden');
        document.getElementById('reUploadBtn').style.display = 'block';
    } else {
        // UI State: Show Upload, Hide Dash
        resetUploadUI();
        uploadSection.classList.remove('hidden');
        resultsDashboard.classList.add('hidden');
        document.getElementById('reUploadBtn').style.display = 'none';
    }
}


// --- GET STARTED LOGIC ---
document.getElementById('getStartedForm').addEventListener('submit', (e) => {
    e.preventDefault();

    const name = document.getElementById('gsName').value;
    const age = document.getElementById('gsAge').value;
    const gender = document.getElementById('gsGender').value;
    const dob = document.getElementById('gsDob').value;

    currentUser = { name, age, gender, dob };
    localStorage.setItem('cycura_user', JSON.stringify(currentUser));

    initApp();
});


// --- DIARY & CALENDAR LOGIC (NEW STRIP) ---

document.getElementById('saveDiary').addEventListener('click', () => {
    const key = `diary_${getISODate(currentDate)}`;
    const text = diaryEntry.value;
    localStorage.setItem(key, text);
    showToast("Note saved successfully!");
});

// Listener for Calendar Date Picker
// MOVED TO PERIOD CALENDAR SECTION


function renderCalendarStrip(selectedDate) {
    const strip = document.getElementById('calendarStrip');
    strip.innerHTML = ''; // Clear current

    // Sync Date Picker
    // No picker here anymore (Health Diary)


    // Generate a 14-day window centered on selectedDate (or 2 weeks starting from a bit back)
    // Let's do: -3 days to +3 days (7 days visible) for cleanliness, 
    // but maybe just generate 7 days centered for now to keep it simple and aesthetic.

    // Create range: -3 to +3
    for (let i = -3; i <= 3; i++) {
        const date = new Date(selectedDate);
        date.setDate(selectedDate.getDate() + i);

        const dayEl = document.createElement('div');
        dayEl.className = `calendar-day ${i === 0 ? 'active' : ''}`;

        // Format
        const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
        const dayNum = date.getDate();

        dayEl.innerHTML = `
            <span class="day-name">${dayName}</span>
            <span class="day-number">${dayNum}</span>
        `;

        // Interaction
        dayEl.addEventListener('click', () => {
            // Auto-save before switching
            const currentKey = `diary_${getISODate(currentDate)}`;
            localStorage.setItem(currentKey, diaryEntry.value);

            currentDate = date;
            renderCalendarStrip(currentDate); // Re-center and update styling
            loadDiary(currentDate);
        });

        strip.appendChild(dayEl);
    }
}

function loadDiary(date) {
    const key = `diary_${getISODate(date)}`;
    const savedText = localStorage.getItem(key) || "";
    diaryEntry.value = savedText;
}

function getISODate(date) {
    return date.toISOString().split('T')[0];
}


// --- MENSTRUAL TRACKER LOGIC (Existing + Adapted) ---
const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const uploadSection = document.getElementById('uploadSection');
const loadingIndicator = document.getElementById('loadingIndicator');
const resultsDashboard = document.getElementById('resultsDashboard');

// Drag & Drop
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFile(e.target.files[0]);
});

// Confirm Period Button
// Confirm Period Button - DEPRECATED
// document.getElementById('confirmPeriodBtn').addEventListener('click', () => {
//    showDateModal();
// });

// --- DATE WHEEL LOGIC ---
const dateModal = document.getElementById('dateModal');
const dateWheel = document.getElementById('dateScrollWheel');
const cancelDateBtn = document.getElementById('cancelDateBtn');
const confirmDateBtn = document.getElementById('confirmDateBtn');
let selectedISOString = null;
let dateItems = [];

function showDateModal() {
    dateModal.classList.remove('hidden');
    populateDateWheel();
}

function closeDateModal() {
    dateModal.classList.add('hidden');
}

cancelDateBtn.addEventListener('click', closeDateModal);

confirmDateBtn.addEventListener('click', () => {
    if (selectedISOString) {
        confirmPeriodAPI(selectedISOString);
        closeDateModal();
    }
});

function populateDateWheel() {
    dateWheel.innerHTML = '';
    dateItems = [];

    // Generate Space padding for snap
    // We'll mimic this by simply adding dates and using CSS padding.

    const today = new Date();

    // Generate dates: 30 days back to Today
    for (let i = 30; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);

        const el = document.createElement('div');
        el.className = 'date-item';
        el.dataset.iso = getISODate(d);

        // Format: "Mon, Jan 5"
        const dayName = d.toLocaleDateString('en-US', { weekday: 'short' });
        const month = d.toLocaleDateString('en-US', { month: 'short' });
        const dayNum = d.getDate();

        el.textContent = `${dayName} ${month} ${dayNum}`;
        dateWheel.appendChild(el);
        dateItems.push(el);

        el.addEventListener('click', () => {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    }

    // Scroll event to detect active
    dateWheel.addEventListener('scroll', handleWheelScroll);

    // Initial scroll to bottom (Today) after render
    // Use timeout to allow render
    setTimeout(() => {
        // Auto-select latest
        const lastItem = dateItems[dateItems.length - 1];
        lastItem.scrollIntoView({ block: 'center' });
        handleWheelScroll();
    }, 100);
}

function handleWheelScroll() {
    const parentRect = dateWheel.getBoundingClientRect();
    const wheelCenter = parentRect.top + (parentRect.height / 2);

    let closestDist = Infinity;
    let closestEl = null;

    dateItems.forEach(el => {
        const rect = el.getBoundingClientRect();
        const elCenter = rect.top + (rect.height / 2);
        const dist = Math.abs(wheelCenter - elCenter);

        if (dist < closestDist) {
            closestDist = dist;
            closestEl = el;
        }
    });

    dateItems.forEach(el => el.classList.remove('active-date'));
    if (closestEl) {
        closestEl.classList.add('active-date');
        selectedISOString = closestEl.dataset.iso;
    }
}

async function confirmPeriodAPI(dateStr) {
    try {
        console.log(`[Frontend] Confirming period for date: ${dateStr}`);
        const formData = new FormData();
        formData.append('date', dateStr);

        const response = await fetch('/confirm-period', {
            method: 'POST',
            body: formData
        });

        console.log(`[Frontend] Response status: ${response.status}`);

        if (!response.ok) {
            const errText = await response.text();
            let errMsg = `Server Error (${response.status})`;
            try {
                // Try to parse as JSON if possible
                const errJson = JSON.parse(errText);
                if (errJson.detail) errMsg = errJson.detail;
            } catch (e) {
                // If not JSON, use text or partial text
                errMsg = errText || errMsg;
            }
            throw new Error(errMsg);
        }


        const data = await response.json();
        console.log("[Frontend] Success:", data);

        // --- VALIDATION LOGIC START ---
        let matchMsg = "";
        try {
            const savedDataStr = localStorage.getItem(`cycura_data_${currentUser.name}`);
            if (savedDataStr) {
                const savedData = JSON.parse(savedDataStr);
                const daily = savedData.daily_data;
                const predictedWindow = savedData.outputs.Next_Period_Window; // e.g. "Day 27 - Day 33"

                if (daily && daily.length > 0 && predictedWindow && predictedWindow.includes("Day")) {
                    const startDate = new Date(daily[0].date);
                    const confirmedDate = new Date(dateStr);

                    // Calculate Day Number of Confirmed Date (1-indexed)
                    const diffTime = confirmedDate - startDate;
                    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)) + 1;

                    // Parse Window
                    // Handle potential "Day 27 - Day 33" or "Day 27 – Day 33" (en-dash)
                    const nums = predictedWindow.match(/(\d+)/g);
                    if (nums && nums.length >= 2) {
                        const minDay = parseInt(nums[0]);
                        const maxDay = parseInt(nums[1]);

                        let matchScore = 0;

                        if (diffDays >= minDay && diffDays <= maxDay) {
                            matchScore = 100;
                            matchMsg = `Perfect Match (100%)! You logged on Day ${diffDays}, within the predicted range (${minDay}-${maxDay}).`;
                        } else {
                            // Calculate distance
                            const dist = Math.min(Math.abs(diffDays - minDay), Math.abs(diffDays - maxDay));
                            // Deduct 10% per day off, min 0
                            matchScore = Math.max(0, 100 - (dist * 10));
                            matchMsg = `Match Score: ${matchScore}%. Logged Day: ${diffDays}. Prediction: ${minDay}-${maxDay}.`;
                        }
                    }
                }
            }
        } catch (calcErr) {
            console.warn("Validation calc failed", calcErr);
        }
        // --- VALIDATION LOGIC END ---

        showToast(`Confirmed! ${matchMsg}`, false);
        // Note: Extended toast duration or make it sticky? standard toast is 3s.
        // Maybe alert for better visibility?
        if (matchMsg) alert(matchMsg);

        document.getElementById('alertContainer').classList.add('hidden');

        // Refresh?
        if (currentUser) {
            loadMenstrualData();
        }

    } catch (e) {
        console.error("[Frontend] Error confirming period:", e);
        showToast(`Error: ${e.message}`, true);
    }
}

async function confirmPeriodAndReset() {
    // Deprecated by showDateModal
}

function handleFile(file) {
    if (file.name.split('.').pop().toLowerCase() !== 'csv') {
        showToast("Please upload a CSV file.", true);
        return;
    }
    uploadFile(file);
}

async function uploadFile(file) {
    // UI Loading
    dropZone.querySelector('h3').classList.add('hidden');
    dropZone.querySelector('p').classList.add('hidden');
    dropZone.querySelector('button').classList.add('hidden');
    dropZone.querySelector('.upload-icon').classList.add('hidden');
    loadingIndicator.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

    // USE CURRENT USER DATA
    formData.append('age', currentUser.age);
    formData.append('name', currentUser.name);
    formData.append('gender', currentUser.gender);

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            // Extract the real error message from the server
            let errorDetail = `Server error (${response.status})`;
            try {
                const errJson = await response.json();
                if (errJson.detail) errorDetail = errJson.detail;
            } catch (_) {
                const errText = await response.text();
                if (errText) errorDetail = errText.substring(0, 200);
            }
            console.error('[CYCURA] Server error response:', errorDetail);
            throw new Error(errorDetail);
        }

        const data = await response.json();

        // PERSISTENCE: Save Data for User
        localStorage.setItem(`cycura_data_${currentUser.name}`, JSON.stringify(data));

        renderDashboard(data);

        // Hide upload, show dash
        uploadSection.classList.add('hidden');
        resultsDashboard.classList.remove('hidden');
        document.getElementById('reUploadBtn').style.display = 'block'; // Show Re-upload
        showToast("Analysis Complete!");

    } catch (error) {
        console.error('[CYCURA] Upload error:', error);
        let userMsg = error.message || 'Unknown error';
        // Detect if backend server is not running (Network Error)
        if (error.name === 'TypeError' && (error.message.includes('fetch') || error.message.includes('NetworkError'))) {
            userMsg = 'Cannot connect to server. Please start the backend (start_server.bat) and open the app via http://localhost:5000';
        } else if (error.name === 'TypeError') {
            // This is a code error/bug, not a connection error
            userMsg = 'App error: ' + error.message;
        }
        showToast(userMsg, true);
        resetUploadUI();
    }
}

function resetUploadUI() {
    loadingIndicator.classList.add('hidden');
    dropZone.querySelector('h3').classList.remove('hidden');
    dropZone.querySelector('p').classList.remove('hidden');
    dropZone.querySelector('button').classList.remove('hidden');
    dropZone.querySelector('.upload-icon').classList.remove('hidden');
}

function renderDashboard(data) {
    const outputs = data.outputs;
    const dailyData = data.daily_data;

    // Metrics
    document.getElementById('personType').textContent = outputs.Person_Type || "Unclassified";

    // Set Explanation for Cycle Type (Flip Card Back)
    const typeDesc = document.getElementById('personTypeDesc');
    const pType = outputs.Person_Type || "";

    if (pType === "Normal Ovulatory") {
        typeDesc.textContent = "Your body showed a clear temperature rise followed by a stable phase, which usually happens when ovulation occurs normally. This pattern suggests that your hormones worked together well during this cycle.";
    } else if (pType.includes("Anovulatory")) {
        typeDesc.textContent = "We didn't see a clear sustained temperature rise this cycle. This is common occasionally due to stress or other factors, meaning ovulation might not have happened.";
    } else if (pType.includes("Luteal")) {
        typeDesc.textContent = "Your temperature rose after ovulation but dropped too quickly (short luteal phase). This might affect hormonal balance.";
    } else if (pType.includes("Pregnancy")) {
        typeDesc.textContent = "Your high temperature phase has lasted longer than 18 days! This is a strong indicator of potential pregnancy.";
    } else {
        typeDesc.textContent = "We detected an irregular pattern. Please continue tracking to improve accuracy and see more specific insights.";
    }

    if (outputs.Ovulation_Window) {
        const [start, end] = outputs.Ovulation_Window;
        document.getElementById('ovulationWindow').textContent = `Day ${start} - ${end}`;
        document.getElementById('ovulationConf').textContent = `Confidence: ${outputs.Ovulation_Confidence_pct}%`;
    } else {
        document.getElementById('ovulationWindow').textContent = "Not Detected";
        document.getElementById('ovulationConf').textContent = "";
    }

    // Hide Next Period if Pregnancy or Anovulatory or Perimenopause
    const periodCard = document.querySelector('.period-card');
    const type = outputs.Person_Type || "";

    // Check for special cases where Period prediction is invalid
    if (type.includes("Pregnancy") || type.includes("Anovulatory") || type.includes("Perimenopause")) {
        periodCard.classList.add('hidden');
    } else {
        periodCard.classList.remove('hidden');
        document.getElementById('nextPeriod').textContent = outputs.Next_Period_Window || "Unknown";
    }

    // Insight (Removed)
    // document.getElementById('todaysInsight').innerHTML = outputs.Todays_Insight || "Insight not available";

    // Why & Suggestion
    document.getElementById('whyText').textContent = outputs.Explanation || "Analysis pending...";
    document.getElementById('suggestionText').textContent = outputs.Suggestion || "Start tracking to see suggestions.";

    // Chart
    renderChart(dailyData, outputs);

    // Reset cards to front when new data loads
    resetFlipCards();

    // Check Alerts
    const alertData = outputs.Alerts;

    if (alertData && alertData.show_alert) {
        // Use Toast for all alerts
        showToast(`${alertData.alert_type}: ${alertData.message}`, alertData.severity !== 'success');
    }

    // Render Inline Calendar (Removed)
    // renderPeriodCalendar();
}

// --- FLIP CARD LOGIC ---
const flipCards = document.querySelectorAll('.flip-card');
flipCards.forEach(card => {
    card.addEventListener('click', () => {
        const isFlipped = card.classList.contains('flipped');

        if (isFlipped) {
            // Manual Reset to front
            card.classList.remove('flipped');
            clearTimeout(card.dataset.timerId); // Clear any existing timer
        } else {
            // Flip to back
            card.classList.add('flipped');

            // Auto-close timer (2 minutes = 120000 ms)
            const timerId = setTimeout(() => {
                if (card.classList.contains('flipped')) {
                    card.classList.remove('flipped'); // Auto-flip back
                }
            }, 120000);

            card.dataset.timerId = timerId; // Store timer ID
        }
    });
});

function resetFlipCards() {
    flipCards.forEach(card => {
        card.classList.remove('flipped');
        clearTimeout(card.dataset.timerId);
    });
}

function renderChart(dailyData, outputs) {
    const ctx = document.getElementById('cycleChart').getContext('2d');
    if (myChart) myChart.destroy();

    const labels = dailyData.map(d => `Day ${d.day}`);
    const values = dailyData.map(d => d.sleep_min_cbt);
    const phases = dailyData.map(d => d.cycle_phase);

    // Color Logic
    let pointColors;
    if (!outputs.Ovulation_Day) {
        pointColors = '#2dd4bf'; // Teal (Single Color)
    } else {
        pointColors = phases.map(p => {
            if (p === 'Follicular') return '#60a5fa';
            if (p === 'Ovulatory') return '#f472b6';
            if (p === 'Luteal') return '#fbbf24';
            return '#94a3b8';
        });
    }

    // Dynamic Y-Axis
    let yMin = 36.0;
    let yMax = 37.5;
    if (values.length > 0) {
        yMin = Math.min(...values) - 0.2;
        yMax = Math.max(...values) + 0.2;
    }

    myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Temperature (°C)',
                data: values,
                borderColor: '#ffffff',
                borderWidth: 2,
                pointBackgroundColor: pointColors,
                pointRadius: 5,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            return `${ctx.raw} °C (${phases[ctx.dataIndex] || 'Data'})`;
                        }
                    }
                },
                annotation: {
                    annotations: {
                        line1: {
                            type: 'line',
                            yMin: outputs.Ovulation_Day && values.length > 0 ? (values.reduce((a, b) => a + b, 0) / values.length) : null,
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderWidth: 1,
                        }
                    }
                }
            },
            scales: {
                y: {
                    min: yMin, max: yMax,
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}

function showToast(msg, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.style.background = isError ? '#ef4444' : '#334155';
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 3000);
}

// --- SETTINGS LOGIC ---
function renderSettings() {
    if (!currentUser) return;

    // 1. Account Details
    document.getElementById('settingsName').textContent = currentUser.name;
    document.getElementById('settingsGender').textContent = currentUser.gender || 'Not Specified';

    // 2. Analytics History
    const list = document.getElementById('historyList');
    list.innerHTML = '';

    const historyItems = [];

    // Check Menstrual
    if (localStorage.getItem(`cycura_data_${currentUser.name}`)) {
        historyItems.push({ type: 'Menstrual', date: 'Latest Analysis', icon: 'water_drop', color: '#f472b6' });
    }

    if (historyItems.length === 0) {
        list.innerHTML = '<li style="text-align: center; color: var(--text-muted); padding: 1rem;">No details recorded yet.</li>';
    } else {
        historyItems.forEach(item => {
            const li = document.createElement('li');
            li.style.display = 'flex';
            li.style.alignItems = 'center';
            li.style.justifyContent = 'space-between';
            li.style.padding = '0.8rem';
            li.style.background = 'rgba(255,255,255,0.05)';
            li.style.borderRadius = '12px';
            li.style.marginBottom = '0.5rem';

            li.innerHTML = `
                <div style="display:flex; align-items:center; gap:0.8rem;">
                    <span class="material-symbols-rounded" style="color:${item.color};">${item.icon}</span>
                    <span style="color:white; font-size:0.95rem;">${item.type} Analysis</span>
                </div>
                <span style="color:var(--text-muted); font-size:0.8rem;">${item.date}</span>
            `;
            list.appendChild(li);
        });
    }
}

// --- GLOBAL ANIMATION HANDLER ---
document.body.addEventListener('click', (e) => {
    // Select interactive elements
    const target = e.target.closest('button, .nav-item, .hub-card, .file-label');

    if (target) {
        // Remove class if currently animating to reset
        target.classList.remove('click-animate');

        // Force reflow
        void target.offsetWidth;

        // Add class
        target.classList.add('click-animate');

        // Cleanup after animation duration (300ms)
        setTimeout(() => {
            target.classList.remove('click-animate');
        }, 300);
    }
});

/* --- NEW INLINE CALENDAR LOGIC (v2) --- */

// --- PERIOD LOGGING (Removed)
// renderPeriodCalendar logic removed to keep results clean.



async function confirmPeriodAPI(dateStr) {
    try {
        console.log(`[Frontend] Confirming period for date: ${dateStr}`);
        const formData = new FormData();
        formData.append('date', dateStr);

        const response = await fetch('/confirm-period', {
            method: 'POST',
            body: formData
        });

        console.log(`[Frontend] Response status: ${response.status}`);

        if (!response.ok) {
            const errText = await response.text();
            let errMsg = `Server Error (${response.status})`;
            try {
                const errJson = JSON.parse(errText);
                if (errJson.detail) errMsg = errJson.detail;
            } catch (e) {
                errMsg = errText || errMsg;
            }
            throw new Error(errMsg);
        }

        const data = await response.json();
        console.log("[Frontend] Success:", data);

        // --- VALIDATION LOGIC ---
        let matchMsg = "";
        try {
            const savedDataStr = localStorage.getItem(`cycura_data_${currentUser.name}`);
            if (savedDataStr) {
                const savedData = JSON.parse(savedDataStr);
                const daily = savedData.daily_data;
                const predictedWindow = savedData.outputs.Next_Period_Window;

                if (daily && daily.length > 0 && predictedWindow && predictedWindow.includes("Day")) {
                    const startDate = new Date(daily[0].date);
                    const confirmedDate = new Date(dateStr);
                    const diffTime = confirmedDate - startDate;
                    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)) + 1;
                    const nums = predictedWindow.match(/(\d+)/g);
                    if (nums && nums.length >= 2) {
                        const minDay = parseInt(nums[0]);
                        const maxDay = parseInt(nums[1]);
                        let matchScore = 0;
                        if (diffDays >= minDay && diffDays <= maxDay) {
                            matchScore = 100;
                            matchMsg = `Perfect Match (100%)! You logged on Day ${diffDays}, within the predicted range (${minDay}-${maxDay}).`;
                        } else {
                            const dist = Math.min(Math.abs(diffDays - minDay), Math.abs(diffDays - maxDay));
                            matchScore = Math.max(0, 100 - (dist * 10));
                            matchMsg = `Match Score: ${matchScore}%. Logged Day: ${diffDays}. Prediction: ${minDay}-${maxDay}.`;
                        }
                    }
                }
            }
        } catch (calcErr) {
            console.warn("Validation calc failed", calcErr);
        }

        // Show Custom Feedback Modal if Match Msg exists
        if (matchMsg) {
            const feedbackModal = document.getElementById('feedbackModal');
            document.getElementById('feedbackMessage').textContent = matchMsg;
            feedbackModal.classList.remove('hidden');

            // Auto close toast to avoid clutter
            // showToast handles its own timeout
        } else {
            showToast(`Confirmed!`, false);
        }



        if (currentUser) {
            loadMenstrualData();
        }

    } catch (e) {
        console.error("[Frontend] Error confirming period:", e);
        showToast(`Error: ${e.message}`, true);
    }
}

/* --- RECOVERED FUNCTIONS --- */
// --- CALENDAR STRIP LOGIC ---
function renderCalendarStrip(selectedDate) {
    const strip = document.getElementById('calendarStrip');
    if (!strip) return;

    strip.innerHTML = '';

    // Render sliding window: -3 days to +3 days
    for (let i = -3; i <= 3; i++) {
        const d = new Date(selectedDate);
        d.setDate(selectedDate.getDate() + i);

        const el = document.createElement('div');
        el.className = 'calendar-day';
        if (i === 0) el.classList.add('active');

        el.innerHTML = `
            <span class="day-name">${d.toLocaleDateString('en-US', { weekday: 'short' })}</span>
            <span class="day-number">${d.getDate()}</span>
        `;

        el.addEventListener('click', () => {
            currentDate = d;
            renderCalendarStrip(d);
            loadDiary(d);
        });

        strip.appendChild(el);
    }
}

// --- DIARY LOGIC ---
function loadDiary(date) {
    const key = `diary_${date.toDateString()}`;
    const val = localStorage.getItem(key) || '';
    if (diaryEntry) {
        diaryEntry.value = val;
    }
}

// Add Save Listener
const saveBtn = document.getElementById('saveDiary');
if (saveBtn) {
    saveBtn.addEventListener('click', () => {
        if (diaryEntry) {
            const key = `diary_${currentDate.toDateString()}`;
            localStorage.setItem(key, diaryEntry.value);
            showToast('Diary saved!');
        }
    });
}

// Feedback Modal Listener
const closeFeedbackBtn = document.getElementById('closeFeedbackBtn');
if (closeFeedbackBtn) {
    closeFeedbackBtn.addEventListener('click', () => {
        document.getElementById('feedbackModal').classList.add('hidden');
    });
}

function getISODate(d) {
    // Return YYYY-MM-DD local time 
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}
