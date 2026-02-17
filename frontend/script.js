let tg = window.Telegram.WebApp;
// Автоматическое определение backend URL
const configuredBackendUrl = window.__BACKEND_URL__;
let backendUrl = configuredBackendUrl
    || (window.location.hostname === 'localhost'
        ? 'http://localhost:8000'
        : `${window.location.origin}/api`);
    
let currentEventId = null;
let currentOptionIndex = null;
let currentCategory = 'all';
let currentWithdrawalId = null;
let isAdmin = false;
let userBalance = 0;

// Auto-refresh interval (30 seconds)
let autoRefreshInterval = null;
const AUTO_REFRESH_DELAY = 30000;

const categoryNames = {
    'all': 'All',
    'politics': 'Politics',
    'sports': 'Sports',
    'crypto': 'Crypto',
    'pop_culture': 'Culture',
    'business': 'Business',
    'science': 'Science',
    'other': 'Other'
};

document.addEventListener('DOMContentLoaded', function() {
    tg.expand();
    tg.ready();
    
    // Telegram theme colors
    if (tg.themeParams) {
        document.documentElement.style.setProperty('--bg-primary', tg.themeParams.bg_color || '#0a0a0a');
        document.documentElement.style.setProperty('--bg-secondary', tg.themeParams.secondary_bg_color || '#141414');
    }
    
    setTimeout(() => {
        document.getElementById('loading').classList.add('hidden');
    }, 500);
    
    // Initial load
    loadEvents();
    loadUserBalance();
    checkAdminStatus();
    
    // Start auto-refresh
    startAutoRefresh();
});

function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(() => {
        const activeSection = document.querySelector('.section:not(.hidden)');
        if (activeSection && activeSection.id === 'events-section') {
            loadEvents(true); // Silent refresh
        }
    }, AUTO_REFRESH_DELAY);
}

async function apiRequest(url, options = {}) {
    try {
        const fullUrl = `${backendUrl}${url}`;
        
        const response = await fetch(fullUrl, {
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            ...options
        });
        
        if (!response.ok) {
            let error;
            try {
                error = await response.json();
            } catch {
                error = { detail: `HTTP ${response.status}: ${response.statusText}` };
            }
            throw new Error(error.detail || 'Request error');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ==================== USER & AUTH ====================

function getUserId() {
    return tg.initDataUnsafe?.user?.id || 123456789;
}

function getUsername() {
    return tg.initDataUnsafe?.user?.username || 
           tg.initDataUnsafe?.user?.first_name || 
           'User';
}

async function checkAdminStatus() {
    try {
        const userId = getUserId();
        const data = await apiRequest(`/admin/check/${userId}`);
        isAdmin = data.is_admin;
        
        if (isAdmin) {
            document.getElementById('admin-menu-item').style.display = 'flex';
        }
    } catch (error) {
        console.error('Admin check error:', error);
    }
}

// ==================== CATEGORIES & EVENTS ====================

function selectCategory(category) {
    currentCategory = category;

    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === category);
    });

    loadEvents();
}

// Setup horizontal scroll for categories - simple touch/mouse scroll
function setupCategoryScroll() {
    const container = document.getElementById('categories-container');
    if (!container) return;

    // Mouse wheel horizontal scroll
    container.addEventListener('wheel', (e) => {
        if (e.deltaY !== 0) {
            container.scrollLeft += e.deltaY;
            e.preventDefault();
        }
    }, { passive: false });

    // Touch scroll - let native behavior handle it
    container.style.webkitOverflowScrolling = 'touch';
}

async function loadEvents(silent = false) {
    try {
        const container = document.getElementById('events-container');
        
        if (!silent) {
            container.innerHTML = `
                <div class="loading-container">
                    <div class="spinner"></div>
                    <p>Loading markets...</p>
                </div>
            `;
        }
        
        const url = currentCategory && currentCategory !== 'all' 
            ? `/events?category=${currentCategory}` 
            : '/events';
        
        const data = await apiRequest(url);
        
        if (!data.events || data.events.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                        </svg>
                    </div>
                    <div class="empty-state-title">No markets found</div>
                    <div class="empty-state-text">There are no active markets in this category</div>
                    <button class="empty-state-btn" onclick="syncPolymarket()">
                        Load from Polymarket
                    </button>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.events.map(event => createEventCard(event)).join('');
    } catch (error) {
        console.error('Load events error:', error);
        if (!silent) {
            const container = document.getElementById('events-container');
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="12" cy="12" r="10"/>
                            <path d="M12 8v4M12 16h.01"/>
                        </svg>
                    </div>
                    <div class="empty-state-title">Connection Error</div>
                    <div class="empty-state-text">${error.message}</div>
                    <button class="empty-state-btn" onclick="loadEvents()">
                        Try Again
                    </button>
                </div>
            `;
        }
    }
}

async function syncPolymarket() {
    try {
        showNotification('Syncing markets from Polymarket...', 'info');
        await apiRequest('/admin/force-sync', { method: 'GET' });
        showNotification('Markets synced successfully!', 'success');
        loadEvents();
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    }
}

function createEventCard(event) {
    const timeLeft = formatTimeLeft(event.time_left);
    const totalPool = formatNumber(event.total_pool || 0);
    const categoryName = categoryNames[event.category] || 'Other';
    const categoryInitial = categoryName.charAt(0).toUpperCase();
    
    const imageHtml = event.image_url 
        ? `<img src="${event.image_url}" alt="" class="event-image" crossorigin="anonymous" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'"><div class="event-image-placeholder" style="display:none">${categoryInitial}</div>`
        : `<div class="event-image-placeholder">${categoryInitial}</div>`;

    return `
        <div class="event-card" onclick="openEventModal(${event.id})">
            <div class="event-header">
                ${imageHtml}
                <div class="event-info">
                    <div class="event-category">
                        <span class="category-badge">${categoryName}</span>
                    </div>
                    <h3 class="event-title">${escapeHtml(event.title)}</h3>
                </div>
            </div>

            <div class="event-meta">
                <div class="event-timer">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 6v6l4 2"/>
                    </svg>
                    ${timeLeft}
                </div>
                <div class="event-volume">$${totalPool} Vol.</div>
            </div>
            
            <div class="options-container">
                ${event.options.map((opt, idx) => createOptionButton(event.id, opt, idx, event.options.length)).join('')}
            </div>
        </div>
    `;
}

function createOptionButton(eventId, option, idx, totalOptions) {
    const probability = option.probability || 50;
    const isYes = option.text.toLowerCase() === 'yes' || idx === 0;
    const optionClass = totalOptions === 2 ? (isYes ? 'yes-option' : 'no-option') : '';
    
    return `
        <button class="option-btn ${optionClass}" 
                style="--probability: ${probability}%"
                onclick="openBetModal(${eventId}, ${option.index}, '${escapeHtml(option.text)}')">
            <span class="option-text">${escapeHtml(option.text)}</span>
            <div class="option-right">
                <span class="option-probability">${probability}%</span>
            </div>
        </button>
    `;
}

// ==================== BALANCE & WALLET ====================

async function loadUserBalance() {
    try {
        const userId = getUserId();
        const data = await apiRequest(`/wallet/balance/${userId}`);
        
        userBalance = data.balance_usdt || 0;
        const formattedBalance = formatNumber(userBalance);
        
        document.getElementById('user-balance').textContent = formattedBalance;
        document.getElementById('wallet-balance-value').textContent = userBalance.toFixed(2);
        document.getElementById('profile-balance').textContent = userBalance.toFixed(2);
        document.getElementById('available-balance').textContent = userBalance.toFixed(2);
        
        // Update profile info
        document.getElementById('profile-name').textContent = getUsername();
        document.getElementById('profile-telegram-id').textContent = `ID: ${userId}`;
        document.getElementById('profile-avatar').textContent = getUsername().charAt(0).toUpperCase();
        
        // Load transactions
        if (data.transactions) {
            renderTransactions(data.transactions);
        }
        
        // Load user stats
        const userData = await apiRequest(`/user/${userId}`);
        if (userData.stats) {
            document.getElementById('active-predictions').textContent = userData.stats.active_predictions || 0;
            document.getElementById('total-won').textContent = userData.stats.total_won || 0;
        }
    } catch (error) {
        console.error('Balance load error:', error);
        document.getElementById('user-balance').textContent = '0';
    }
}

function renderTransactions(transactions) {
    const container = document.getElementById('transactions-container');
    
    if (!transactions || transactions.length === 0) {
        container.innerHTML = `
            <div class="empty-transactions">
                <p>No transactions yet</p>
            </div>
        `;
        return;
    }
    
    const html = transactions.map(tx => {
        const isDeposit = tx.type === 'deposit';
        const isWithdraw = tx.type === 'withdrawal';
        const statusClass = tx.status === 'completed' ? 'status-completed' : 
                           tx.status === 'pending' ? 'status-pending' :
                           tx.status === 'approved' ? 'status-approved' :
                           tx.status === 'rejected' ? 'status-rejected' : '';
        
        const icon = isDeposit ? 
            `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12l7-7 7 7"/></svg>` :
            `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7 7 7-7"/></svg>`;
        
        const amountClass = isDeposit ? 'amount-positive' : 'amount-negative';
        const amountPrefix = isDeposit ? '+' : '-';
        
        return `
            <div class="transaction-item">
                <div class="transaction-icon ${isDeposit ? 'deposit' : 'withdraw'}">
                    ${icon}
                </div>
                <div class="transaction-info">
                    <span class="transaction-type">${isDeposit ? 'Deposit' : 'Withdrawal'}</span>
                    <span class="transaction-status ${statusClass}">${tx.status}</span>
                </div>
                <div class="transaction-amount ${amountClass}">
                    ${amountPrefix}${tx.amount.toFixed(2)} ${tx.asset}
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

// ==================== DEPOSIT ====================

function openDepositModal() {
    document.getElementById('deposit-modal').classList.remove('hidden');
    document.getElementById('deposit-amount').value = '';
    document.getElementById('deposit-amount').focus();
}

function closeDepositModal() {
    document.getElementById('deposit-modal').classList.add('hidden');
}

function setDepositAmount(amount) {
    document.getElementById('deposit-amount').value = amount;
}

async function processDeposit() {
    const amount = parseFloat(document.getElementById('deposit-amount').value);
    
    if (!amount || amount < 1) {
        showNotification('Minimum deposit is 1 USDT', 'error');
        return;
    }
    
    try {
        const btn = document.querySelector('#deposit-modal .modal-btn.confirm');
        btn.textContent = 'Processing...';
        btn.disabled = true;
        
        const result = await apiRequest('/wallet/deposit', {
            method: 'POST',
            body: JSON.stringify({
                telegram_id: getUserId(),
                amount: amount,
                asset: 'USDT'
            })
        });
        
        if (result.pay_url) {
            // Open CryptoBot payment link
            if (tg.openLink) {
                tg.openLink(result.pay_url);
            } else {
                window.open(result.pay_url, '_blank');
            }
            showNotification('Opening payment page...', 'info');
        }
        
        closeDepositModal();
        
        // Refresh balance after a delay
        setTimeout(loadUserBalance, 3000);
        
    } catch (error) {
        showNotification(error.message || 'Deposit error', 'error');
    } finally {
        const btn = document.querySelector('#deposit-modal .modal-btn.confirm');
        if (btn) {
            btn.textContent = 'Continue';
            btn.disabled = false;
        }
    }
}

// ==================== WITHDRAW ====================

function openWithdrawModal() {
    document.getElementById('withdraw-modal').classList.remove('hidden');
    document.getElementById('withdraw-amount').value = '';
    document.getElementById('available-balance').textContent = userBalance.toFixed(2);
}

function closeWithdrawModal() {
    document.getElementById('withdraw-modal').classList.add('hidden');
}

async function processWithdraw() {
    const amount = parseFloat(document.getElementById('withdraw-amount').value);
    
    if (!amount || amount < 5) {
        showNotification('Minimum withdrawal is 5 USDT', 'error');
        return;
    }
    
    if (amount > userBalance) {
        showNotification('Insufficient balance', 'error');
        return;
    }
    
    try {
        const btn = document.querySelector('#withdraw-modal .modal-btn.confirm');
        btn.textContent = 'Processing...';
        btn.disabled = true;
        
        const result = await apiRequest('/wallet/withdraw', {
            method: 'POST',
            body: JSON.stringify({
                telegram_id: getUserId(),
                amount: amount,
                asset: 'USDT'
            })
        });
        
        showNotification('Withdrawal request submitted! Waiting for approval.', 'success');
        closeWithdrawModal();
        loadUserBalance();
        
        if (tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('success');
        }
        
    } catch (error) {
        showNotification(error.message || 'Withdrawal error', 'error');
    } finally {
        const btn = document.querySelector('#withdraw-modal .modal-btn.confirm');
        if (btn) {
            btn.textContent = 'Request Withdrawal';
            btn.disabled = false;
        }
    }
}

// ==================== BET MODAL ====================

function openBetModal(eventId, optionIndex, optionText) {
    const eventCard = event.target.closest('.event-card');
    const title = eventCard.querySelector('.event-title').textContent;
    
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-option').textContent = `Your prediction: ${optionText}`;
    document.getElementById('bet-modal').classList.remove('hidden');
    document.getElementById('points-input').value = '';
    document.getElementById('points-input').focus();
    
    currentEventId = eventId;
    currentOptionIndex = optionIndex;
}

function closeModal() {
    document.getElementById('bet-modal').classList.add('hidden');
    currentEventId = null;
    currentOptionIndex = null;
}

async function confirmPrediction() {
    const points = parseFloat(document.getElementById('points-input').value);
    
    if (!points || points < 1) {
        showNotification('Enter a valid amount (minimum 1 USDT)', 'error');
        return;
    }
    
    if (points > userBalance) {
        showNotification('Insufficient balance', 'error');
        return;
    }
    
    try {
        const confirmBtn = document.querySelector('#bet-modal .modal-btn.confirm');
        confirmBtn.textContent = 'Processing...';
        confirmBtn.disabled = true;
        
        const result = await apiRequest('/predict', {
            method: 'POST',
            body: JSON.stringify({
                telegram_id: getUserId(),
                event_id: currentEventId,
                option_index: currentOptionIndex,
                points: points
            })
        });
        
        showNotification(`Bet placed! New balance: ${formatNumber(result.new_balance)} USDT`, 'success');
        closeModal();
        loadEvents();
        loadUserBalance();
        
        if (tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('success');
        }
    } catch (error) {
        showNotification(error.message || 'Prediction error', 'error');
        if (tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('error');
        }
    } finally {
        const confirmBtn = document.querySelector('#bet-modal .modal-btn.confirm');
        if (confirmBtn) {
            confirmBtn.textContent = 'Place Bet';
            confirmBtn.disabled = false;
        }
    }
}

// ==================== ADMIN PANEL ====================

async function loadAdminData() {
    if (!isAdmin) return;
    
    try {
        const userId = getUserId();
        
        // Load stats
        const stats = await apiRequest(`/admin/stats?admin_telegram_id=${userId}`);
        document.getElementById('stat-users').textContent = stats.total_users || 0;
        document.getElementById('stat-events').textContent = stats.total_events || 0;
        document.getElementById('stat-pending').textContent = stats.pending_withdrawals || 0;
        
        // Load pending withdrawals
        const withdrawals = await apiRequest(`/admin/withdrawals?admin_telegram_id=${userId}`);
        renderPendingWithdrawals(withdrawals.withdrawals || []);
        
    } catch (error) {
        console.error('Admin data error:', error);
        showNotification('Error loading admin data', 'error');
    }
}

function renderPendingWithdrawals(withdrawals) {
    const container = document.getElementById('pending-withdrawals-container');
    
    if (!withdrawals || withdrawals.length === 0) {
        container.innerHTML = `<div class="empty-state-small">No pending withdrawals</div>`;
        return;
    }
    
    const html = withdrawals.map(w => `
        <div class="withdrawal-card" onclick="openAdminActionModal(${w.id}, ${w.user_telegram_id}, '${w.username || 'Unknown'}', ${w.amount}, '${w.asset}')">
            <div class="withdrawal-user">
                <div class="withdrawal-avatar">${(w.username || 'U').charAt(0).toUpperCase()}</div>
                <div class="withdrawal-user-info">
                    <span class="withdrawal-username">${w.username || 'User'}</span>
                    <span class="withdrawal-user-id">ID: ${w.user_telegram_id}</span>
                </div>
            </div>
            <div class="withdrawal-amount">
                <span class="amount-value">${w.amount.toFixed(2)}</span>
                <span class="amount-currency">${w.asset}</span>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function openAdminActionModal(id, telegramId, username, amount, asset) {
    currentWithdrawalId = id;
    
    document.getElementById('withdrawal-details').innerHTML = `
        <div class="detail-row">
            <span class="detail-label">User:</span>
            <span class="detail-value">${username} (ID: ${telegramId})</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Amount:</span>
            <span class="detail-value">${amount.toFixed(2)} ${asset}</span>
        </div>
    `;
    
    document.getElementById('admin-action-modal').classList.remove('hidden');
}

function closeAdminActionModal() {
    document.getElementById('admin-action-modal').classList.add('hidden');
    currentWithdrawalId = null;
}

async function approveWithdrawal() {
    await processWithdrawalAction('approve');
}

async function rejectWithdrawal() {
    await processWithdrawalAction('reject');
}

async function processWithdrawalAction(action) {
    if (!currentWithdrawalId) return;
    
    try {
        const comment = document.getElementById('admin-comment').value;
        
        await apiRequest('/admin/withdrawal/action', {
            method: 'POST',
            body: JSON.stringify({
                admin_telegram_id: getUserId(),
                transaction_id: currentWithdrawalId,
                action: action,
                comment: comment || null
            })
        });
        
        showNotification(`Withdrawal ${action}ed successfully`, 'success');
        closeAdminActionModal();
        loadAdminData();
        
    } catch (error) {
        showNotification(error.message || 'Error processing withdrawal', 'error');
    }
}

// ==================== NAVIGATION ====================

function showSection(sectionName) {
    document.querySelectorAll('.section').forEach(section => section.classList.add('hidden'));
    document.getElementById(`${sectionName}-section`).classList.remove('hidden');
    
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.section === sectionName);
    });
    
    // Load data for specific sections
    if (sectionName === 'events') {
        loadEvents();
    } else if (sectionName === 'wallet') {
        loadUserBalance();
    } else if (sectionName === 'profile') {
        loadUserBalance();
    } else if (sectionName === 'admin' && isAdmin) {
        loadAdminData();
    }
}

function showMyPredictions() {
    // TODO: Implement predictions history
    showNotification('Coming soon!', 'info');
}

// ==================== EVENT MODAL ====================

let selectedOptionIndex = null;

async function openEventModal(eventId) {
    try {
        const event = await apiRequest(`/events/${eventId}`);
        if (!event) return;

        selectedOptionIndex = null;
        document.getElementById('event-modal-title').textContent = event.title;
        document.getElementById('event-description').innerHTML = `
            <strong>Description:</strong><br>
            ${event.description || 'No description available.'}
        `;

        // Render options
        const optionsContainer = document.getElementById('event-options');
        optionsContainer.innerHTML = event.options.map((opt, idx) => `
            <div class="event-option-btn" onclick="selectEventOption(${idx}, ${opt.probability})">
                <span class="event-option-text">${opt.text}</span>
                <span class="event-option-probability">${opt.probability}%</span>
            </div>
        `).join('');

        // Show modal
        document.getElementById('event-modal').classList.remove('hidden');

        // Render chart after modal is shown
        setTimeout(() => renderEventChart(event.options), 100);
    } catch (e) {
        console.error('Error loading event:', e);
        showNotification('Failed to load event details', 'error');
    }
}

function selectEventOption(index, probability) {
    selectedOptionIndex = index;
    document.querySelectorAll('.event-option-btn').forEach((btn, idx) => {
        btn.classList.toggle('selected', idx === index);
    });

    // Open bet modal after selection
    setTimeout(() => {
        const eventTitle = document.getElementById('event-modal-title').textContent;
        const optionText = document.querySelectorAll('.event-option-text')[index]?.textContent;
        openBetModal(eventTitle, optionText, probability);
    }, 200);
}

function closeEventModal() {
    document.getElementById('event-modal').classList.add('hidden');
    selectedOptionIndex = null;
}

function openBetModal(title, option, probability) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-option').textContent = `Predicting: ${option}`;
    document.getElementById('bet-modal').classList.remove('hidden');
}

// Simple chart rendering using CSS
function renderEventChart(options) {
    const canvas = document.getElementById('event-chart-canvas');
    if (!canvas) return;

    // Clear canvas
    const ctx = canvas.getContext('2d');
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width - 40;
    canvas.height = rect.height - 40;

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 20;

    // Draw pie chart
    let startAngle = -Math.PI / 2;
    const colors = ['#22c55e', '#ef4444', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899'];

    options.forEach((opt, idx) => {
        const sliceAngle = (opt.probability / 100) * 2 * Math.PI;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
        ctx.closePath();
        ctx.fillStyle = colors[idx % colors.length];
        ctx.fill();
        startAngle += sliceAngle;
    });

    // Draw center circle (donut chart)
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.6, 0, 2 * Math.PI);
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg-secondary');
    ctx.fill();

    // Draw total in center
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 18px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('100%', centerX, centerY);
}

// ==================== UTILITY FUNCTIONS ====================

function formatTimeLeft(seconds) {
    if (seconds < 0) return "Ended";
    
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 30) {
        const months = Math.floor(days / 30);
        return `${months}mo`;
    }
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return Math.floor(num).toString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('notification-hide');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Close modals on backdrop click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.add('hidden');
    }
});

// Initialize category scroll on page load
setupCategoryScroll();
