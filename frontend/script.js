/**
 * TGMarket - New UI (Polymarket Mobile Style)
 * Modern, clean, mobile-first design
 */

let tg = window.Telegram.WebApp;

// Get user language
function getUserLanguage() {
    try {
        const user = tg.initDataUnsafe?.user;
        if (user && user.language_code) {
            return user.language_code;
        }
    } catch (e) {
        console.log('Telegram WebApp not ready');
    }
    return navigator.language?.startsWith('ru') ? 'ru' : 'en';
}

const userLang = getUserLanguage();
const isRussian = userLang === 'ru';

// Backend URL
const backendUrl = window.location.origin;

// State
let currentCategory = 'all';
let currentEventId = null;
let selectedOutcome = null;
let currentUser = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    // Initialize Telegram WebApp
    tg.ready();
    tg.expand();

    // Apply Telegram theme
    applyTelegramTheme();

    // Load user data
    await loadUser();

    // Load markets
    await loadMarkets();

    // Hide loading screen
    setTimeout(() => {
        document.getElementById('loading').style.display = 'none';
    }, 500);
}

function applyTelegramTheme() {
    const theme = tg.themeParams;
    if (theme) {
        document.documentElement.style.setProperty('--bg-primary', theme.bg_color || '#0d1117');
        document.documentElement.style.setProperty('--text-primary', theme.text_color || '#f0f6fc');
    }
}

async function loadUser() {
    const user = tg.initDataUnsafe?.user;
    if (!user) return;

    currentUser = {
        id: user.id,
        username: user.username || user.first_name,
        firstName: user.first_name,
        lastName: user.last_name,
        balance: 0
    };

    // Update UI
    document.getElementById('header-balance').textContent = '0';
    document.getElementById('portfolio-balance').textContent = '0.00';
    document.getElementById('profile-name').textContent = user.first_name;
    document.getElementById('profile-id').textContent = `ID: ${user.id}`;
    document.getElementById('profile-avatar').textContent = user.first_name.charAt(0).toUpperCase();

    // Try to fetch balance from backend
    try {
        const response = await fetch(`${backendUrl}/user/${user.id}`);
        if (response.ok) {
            const data = await response.json();
            currentUser.balance = data.balance || 0;
            updateBalanceUI();
        }
    } catch (e) {
        console.log('Could not fetch user data');
    }
}

function updateBalanceUI() {
    const balance = currentUser.balance || 0;
    document.getElementById('header-balance').textContent = balance.toFixed(2);
    document.getElementById('portfolio-balance').textContent = balance.toFixed(2);
}

async function loadMarkets() {
    try {
        const category = currentCategory === 'all' ? '' : currentCategory;
        const response = await fetch(`${backendUrl}/events${category ? '?category=' + category : ''}`);
        
        if (!response.ok) throw new Error('Failed to load markets');
        
        const events = await response.json();
        renderMarkets(events);
    } catch (error) {
        console.error('Error loading markets:', error);
        document.getElementById('markets-list').innerHTML = `
            <div class="empty-state">
                <p>Failed to load markets. Please try again.</p>
            </div>
        `;
    }
}

function renderMarkets(events) {
    const container = document.getElementById('markets-list');
    
    if (!events || events.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No markets available</p>
            </div>
        `;
        return;
    }

    container.innerHTML = events.map(event => {
        const volume = event.pool || 0;
        const outcomes = event.options || [];
        
        return `
            <div class="market-card" onclick="openMarketModal('${event.id}')">
                <div class="market-header">
                    <div class="market-title">${escapeHtml(event.title)}</div>
                    <div class="market-volume">$${formatNumber(volume)} Vol</div>
                </div>
                
                <div class="market-outcomes">
                    ${outcomes.slice(0, 2).map((outcome, index) => {
                        const percent = outcome.probability || 50;
                        return `
                            <div class="outcome-btn ${index === 0 ? 'yes' : 'no'}" onclick="event.stopPropagation(); selectOutcome('${event.id}', '${outcome.id}')">
                                <div class="outcome-info">
                                    <span class="outcome-label">${index === 0 ? 'Yes' : 'No'}</span>
                                    <span class="outcome-percent">${percent}%</span>
                                </div>
                                <div class="outcome-bar">
                                    <div class="outcome-bar-fill" style="width: ${percent}%"></div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
                
                <div class="market-footer">
                    <span class="market-date">${formatEventDate(event.end_date)}</span>
                    <span class="market-category">${event.category || 'Other'}</span>
                </div>
            </div>
        `;
    }).join('');
}

function selectCategory(category) {
    currentCategory = category;
    
    // Update active chip
    document.querySelectorAll('.category-chip').forEach(chip => {
        chip.classList.toggle('active', chip.dataset.category === category);
    });
    
    // Reload markets
    loadMarkets();
}

// Navigation
function showSection(sectionName) {
    // Update sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.toggle('active', section.id === `${sectionName}-section`);
    });
    
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === sectionName);
    });
    
    // Scroll to top
    window.scrollTo(0, 0);
}

// Market Modal
async function openMarketModal(eventId) {
    currentEventId = eventId;
    selectedOutcome = null;
    
    try {
        const response = await fetch(`${backendUrl}/events/${eventId}`);
        if (!response.ok) throw new Error('Event not found');
        
        const event = await response.json();
        
        // Update modal content
        document.getElementById('market-modal-title').textContent = event.title;
        document.getElementById('market-title').textContent = event.title;
        document.getElementById('market-end-date').textContent = `Ends ${formatEventDate(event.end_date)}`;
        
        // Render outcomes
        renderOutcomes(event);
        
        // Render chart
        renderMarketChart(event);
        
        // Show modal
        document.getElementById('market-modal').classList.remove('hidden');
        
        // Load activity/comments
        loadActivity(eventId);
        loadComments(eventId);
        
    } catch (error) {
        console.error('Error opening market:', error);
    }
}

function renderOutcomes(event) {
    const container = document.getElementById('outcomes-container');
    const outcomes = event.options || [];
    
    container.innerHTML = outcomes.map(outcome => {
        const percent = outcome.probability || 50;
        const isSelected = selectedOutcome === outcome.id;
        
        return `
            <div class="outcome-card ${isSelected ? 'selected' : ''} ${outcome.text.toLowerCase().includes('no') ? 'no' : 'yes'}" 
                 onclick="selectOutcome('${event.id}', '${outcome.id}')">
                <div class="outcome-card-header">
                    <span class="outcome-card-label">${escapeHtml(outcome.text)}</span>
                    <span class="outcome-card-percent">${percent}%</span>
                </div>
                <div class="outcome-progress">
                    <div class="outcome-progress-fill" style="width: ${percent}%"></div>
                </div>
            </div>
        `;
    }).join('');
}

function selectOutcome(eventId, outcomeId) {
    selectedOutcome = outcomeId;
    
    // Update UI
    document.querySelectorAll('.outcome-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    event.target.closest('.outcome-card')?.classList.add('selected');
    
    // Open bet modal after short delay
    setTimeout(() => {
        openBetModal(eventId, outcomeId);
    }, 200);
}

// Bet Modal
function openBetModal(eventId, outcomeId) {
    document.getElementById('bet-modal').classList.remove('hidden');
    
    // Reset bet amount
    document.getElementById('bet-amount').value = '';
    updateBetDetails();
}

function closeBetModal() {
    document.getElementById('bet-modal').classList.add('hidden');
}

function setMaxBet() {
    const balance = currentUser?.balance || 0;
    document.getElementById('bet-amount').value = balance.toFixed(2);
    updateBetDetails();
}

document.getElementById('bet-amount')?.addEventListener('input', updateBetDetails);

function updateBetDetails() {
    const amount = parseFloat(document.getElementById('bet-amount').value) || 0;
    
    // Get current price (simplified - should fetch from event)
    const price = 0.50; // This should come from the actual outcome
    const shares = amount / price;
    const potentialReturn = shares * 1.00; // $1 per share if win
    
    document.getElementById('bet-shares').textContent = shares.toFixed(2);
    document.getElementById('bet-price').textContent = `$${price.toFixed(2)}`;
    document.getElementById('bet-return').textContent = `$${potentialReturn.toFixed(2)}`;
}

async function placeBet() {
    const amount = parseFloat(document.getElementById('bet-amount').value);
    
    if (!amount || amount <= 0) {
        alert('Please enter a valid amount');
        return;
    }
    
    if (amount > (currentUser?.balance || 0)) {
        alert('Insufficient balance');
        return;
    }
    
    try {
        const user = tg.initDataUnsafe?.user;
        const response = await fetch(`${backendUrl}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: user.id,
                event_id: currentEventId,
                option_id: selectedOutcome,
                amount: amount
            })
        });
        
        if (!response.ok) throw new Error('Bet placement failed');
        
        const result = await response.json();
        
        // Update balance
        currentUser.balance = result.new_balance || (currentUser.balance - amount);
        updateBalanceUI();
        
        // Close modal
        closeBetModal();
        closeMarketModal();
        
        // Show success
        tg.showPopup({
            title: 'Bet Placed!',
            message: `Successfully placed ${amount} USDT`,
            buttons: [{ type: 'ok' }]
        });
        
    } catch (error) {
        console.error('Error placing bet:', error);
        alert('Failed to place bet. Please try again.');
    }
}

function closeMarketModal() {
    document.getElementById('market-modal').classList.add('hidden');
}

// Tabs
function switchTab(tabName) {
    // Update tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    
    // Update panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `${tabName}-tab`);
    });
}

// Activity
async function loadActivity(eventId) {
    try {
        const response = await fetch(`${backendUrl}/events/${eventId}/bet-history`);
        const activity = response.ok ? await response.json() : [];
        
        const container = document.getElementById('activity-list');
        
        if (activity.length === 0) {
            container.innerHTML = '<div class="empty-state">No activity yet</div>';
            return;
        }
        
        container.innerHTML = activity.slice(0, 20).map(bet => `
            <div class="activity-item">
                <div class="comment-header">
                    <div class="comment-avatar">${bet.username?.charAt(0).toUpperCase() || 'U'}</div>
                    <div>
                        <div class="comment-username">${escapeHtml(bet.username || 'Anonymous')}</div>
                        <div class="comment-time">${formatTimeAgo(new Date(bet.timestamp).getTime())}</div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 600; color: var(--success);">${bet.amount.toFixed(2)} USDT</div>
                    <div style="font-size: 12px; color: var(--text-muted);">${bet.shares.toFixed(2)} shares</div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading activity:', error);
    }
}

// Comments
let comments = [];

async function loadComments(eventId) {
    // For now, use local storage for comments
    const stored = localStorage.getItem(`comments-${eventId}`);
    comments = stored ? JSON.parse(stored) : [];
    
    renderComments();
}

function renderComments() {
    const container = document.getElementById('comments-list');
    
    if (comments.length === 0) {
        container.innerHTML = '<div class="empty-state">No comments yet. Be first!</div>';
        return;
    }
    
    container.innerHTML = comments.slice().reverse().map(comment => `
        <div class="comment-item">
            <div class="comment-header">
                <div class="comment-avatar">${comment.username.charAt(0).toUpperCase()}</div>
                <div>
                    <div class="comment-username">${escapeHtml(comment.username)}</div>
                    <div class="comment-time">${formatTimeAgo(comment.timestamp)}</div>
                </div>
            </div>
            <div class="comment-text">${escapeHtml(comment.text)}</div>
        </div>
    `).join('');
}

function addComment() {
    const input = document.getElementById('comment-input');
    const text = input.value.trim();
    
    if (!text) return;
    
    const user = tg.initDataUnsafe?.user;
    const comment = {
        id: Date.now(),
        username: user?.first_name || 'Anonymous',
        text: text,
        timestamp: Date.now()
    };
    
    comments.push(comment);
    
    // Save to local storage
    if (currentEventId) {
        localStorage.setItem(`comments-${currentEventId}`, JSON.stringify(comments));
    }
    
    input.value = '';
    renderComments();
}

// Chart
let marketChart = null;

function renderMarketChart(event) {
    const canvas = document.getElementById('market-chart-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart
    if (marketChart) {
        marketChart.destroy();
    }
    
    // Generate sample data (should come from API)
    const labels = [];
    const data = [];
    const now = Date.now();
    
    for (let i = 50; i >= 0; i--) {
        labels.push(new Date(now - i * 3600000).toISOString());
        data.push(0.3 + Math.random() * 0.4);
    }
    
    marketChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Price',
                data: data,
                borderColor: '#2f81f7',
                backgroundColor: 'rgba(47, 129, 247, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(13, 17, 23, 0.98)',
                    titleColor: '#2f81f7',
                    bodyColor: '#f0f6fc',
                    callbacks: {
                        label: (ctx) => `$${ctx.parsed.y.toFixed(2)}`
                    }
                }
            },
            scales: {
                x: { display: false },
                y: {
                    display: true,
                    position: 'right',
                    grid: {
                        color: 'rgba(48, 54, 61, 0.3)'
                    },
                    ticks: {
                        color: '#8b949e',
                        font: { size: 10 },
                        callback: (value) => `$${value.toFixed(2)}`
                    }
                }
            }
        }
    });
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatEventDate(dateStr) {
    if (!dateStr) return 'TBD';
    const date = new Date(dateStr);
    return date.toLocaleDateString(isRussian ? 'ru-RU' : 'en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatTimeAgo(timestamp) {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

// Admin functions (placeholder)
async function loadAdminData() {
    // Implement admin data loading
}

function showUsersList() {
    // Implement users list
}

function syncPolymarket() {
    // Implement sync
}

function showMyPredictions() {
    // Implement my predictions view
}

function openDepositModal() {
    // Implement deposit modal
    tg.showPopup({
        title: 'Deposit',
        message: 'Deposit functionality coming soon!',
        buttons: [{ type: 'ok' }]
    });
}

function openWithdrawModal() {
    // Implement withdraw modal
    tg.showPopup({
        title: 'Withdraw',
        message: 'Withdraw functionality coming soon!',
        buttons: [{ type: 'ok' }]
    });
}

function toggleTheme() {
    // Implement theme toggle
    tg.showPopup({
        title: 'Theme',
        message: 'Theme toggle coming soon!',
        buttons: [{ type: 'ok' }]
    });
}
