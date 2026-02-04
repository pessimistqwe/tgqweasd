let tg = window.Telegram.WebApp;
// Автоматическое определение backend URL
let backendUrl = window.location.hostname === 'localhost' 
    ? "http://localhost:8000" 
    : "https://tgqweasd.vercel.app/api";
    
let currentEventId = null;
let currentOptionIndex = null;

document.addEventListener('DOMContentLoaded', function() {
    tg.expand();
    tg.ready();
    
    setTimeout(() => {
        document.getElementById('loading').classList.add('hidden');
    }, 500);
    
    loadEvents();
    loadUserBalance();
});

async function apiRequest(url, options = {}) {
    try {
        const fullUrl = `${backendUrl}${url}`;
        console.log('API Request:', fullUrl);
        
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
            throw new Error(error.detail || 'Ошибка запроса');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

async function loadEvents() {
    try {
        const container = document.getElementById('events-container');
        container.innerHTML = '<div style="text-align:center; padding: 40px;"><div class="spinner"></div><p style="color: var(--text-secondary); margin-top: 20px;">Загрузка событий...</p></div>';
        
        const data = await apiRequest('/events');
        console.log('Events loaded:', data);
        
        if (!data.events || data.events.length === 0) {
            container.innerHTML = `
                <div style="text-align:center; padding: 40px;">
                    <p style="color:var(--text-secondary); font-size: 18px;">📭 Нет активных событий</p>
                    <button onclick="syncPolymarket()" style="margin-top: 20px; padding: 12px 24px; background: var(--accent); color: white; border: none; border-radius: 8px; cursor: pointer;">
                        🔄 Загрузить события из Polymarket
                    </button>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.events.map(event => createEventCard(event)).join('');
    } catch (error) {
        console.error('Load events error:', error);
        const container = document.getElementById('events-container');
        container.innerHTML = `
            <div style="text-align:center; padding: 40px;">
                <p style="color: #E22134; font-size: 18px;">❌ ${error.message}</p>
                <button onclick="loadEvents()" style="margin-top: 20px; padding: 12px 24px; background: var(--accent); color: white; border: none; border-radius: 8px; cursor: pointer;">
                    🔄 Повторить
                </button>
            </div>
        `;
    }
}

async function syncPolymarket() {
    try {
        showNotification('⏳ Загрузка событий из Polymarket...', 'info');
        await apiRequest('/admin/sync-polymarket', { method: 'POST' });
        showNotification('✅ События загружены!', 'success');
        loadEvents();
    } catch (error) {
        showNotification('❌ Ошибка загрузки: ' + error.message, 'error');
    }
}

function createEventCard(event) {
    const timeLeft = formatTimeLeft(event.time_left);
    const totalPool = Math.floor(event.total_pool || 0);
    
    return `
        <div class="event-card">
            <h3 class="event-title">${escapeHtml(event.title)}</h3>
            ${event.description ? `<p class="event-description">${escapeHtml(event.description.substring(0, 150))}${event.description.length > 150 ? '...' : ''}</p>` : ''}
            <div style="display: flex; justify-content: space-between; align-items: center; margin: 12px 0;">
                <div class="event-timer">⏱️ ${timeLeft}</div>
                <div style="color: var(--accent); font-weight: 600;">💰 ${totalPool} USDT</div>
            </div>
            <div class="options-container">
                ${event.options.map(opt => createOptionButton(event.id, opt)).join('')}
            </div>
        </div>
    `;
}

function createOptionButton(eventId, option) {
    const points = Math.floor(option.total_points || 0);
    return `
        <button class="option-btn" onclick="openBetModal(${eventId}, ${option.index}, '${escapeHtml(option.text)}')">
            <span>${escapeHtml(option.text)}</span>
            <span class="option-stake">${points} USDT</span>
        </button>
    `;
}

function formatTimeLeft(seconds) {
    if (seconds < 0) return "⏰ Время вышло";
    
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}д ${hours}ч`;
    if (hours > 0) return `${hours}ч ${minutes}м`;
    return `${minutes}м`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadUserBalance() {
    try {
        const userId = tg.initDataUnsafe?.user?.id || 123456789; // Fallback для тестирования
        
        const data = await apiRequest(`/user/${userId}`);
        const balance = Math.floor(data.points);
        
        document.getElementById('user-balance').textContent = balance;
        document.getElementById('profile-balance').textContent = `${balance} USDT`;
        document.getElementById('active-predictions').textContent = data.stats.active_predictions;
    } catch (error) {
        console.error('Ошибка загрузки баланса:', error);
        document.getElementById('user-balance').textContent = '0';
    }
}

function showSection(sectionName) {
    document.querySelectorAll('.section').forEach(section => section.classList.add('hidden'));
    document.getElementById(`${sectionName}-section`).classList.remove('hidden');
    
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    event.target.closest('.nav-btn').classList.add('active');
    
    if (sectionName === 'events') {
        loadEvents();
    }
}

function openBetModal(eventId, optionIndex, optionText) {
    const eventCard = event.target.closest('.event-card');
    const title = eventCard.querySelector('.event-title').textContent;
    
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-option').textContent = `Вариант: ${optionText}`;
    document.getElementById('bet-modal').classList.remove('hidden');
    document.getElementById('points-input').value = '';
    
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
        showNotification('Введите корректную сумму (минимум 1 USDT)', 'error');
        return;
    }
    
    const userId = tg.initDataUnsafe?.user?.id || 123456789;
    
    try {
        const confirmBtn = document.querySelector('.modal-btn.confirm');
        const originalText = confirmBtn.textContent;
        confirmBtn.textContent = '⏳ Отправка...';
        confirmBtn.disabled = true;
        
        const result = await apiRequest('/predict', {
            method: 'POST',
            body: JSON.stringify({
                telegram_id: userId,
                event_id: currentEventId,
                option_index: currentOptionIndex,
                points: points
            })
        });
        
        showNotification(`✅ Прогноз принят! Новый баланс: ${Math.floor(result.new_balance)} USDT`, 'success');
        closeModal();
        loadEvents();
        loadUserBalance();
    } catch (error) {
        showNotification('❌ ' + (error.message || 'Ошибка прогноза'), 'error');
    } finally {
        const confirmBtn = document.querySelector('.modal-btn.confirm');
        if (confirmBtn) {
            confirmBtn.textContent = 'Прогноз';
            confirmBtn.disabled = false;
        }
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const bgColor = type === 'error' ? '#E22134' : type === 'success' ? '#10B981' : 'var(--accent)';
    
    notification.style.cssText = `
        position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
        background: ${bgColor}; color: white;
        padding: 12px 24px; border-radius: 12px; z-index: 2000; 
        font-weight: 600; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        max-width: 90%; text-align: center;
        animation: slideDown 0.3s ease;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideUp 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Добавляем CSS анимации
const style = document.createElement('style');
style.textContent = `
    @keyframes slideDown {
        from { transform: translate(-50%, -100%); opacity: 0; }
        to { transform: translate(-50%, 0); opacity: 1; }
    }
    @keyframes slideUp {
        from { transform: translate(-50%, 0); opacity: 1; }
        to { transform: translate(-50%, -100%); opacity: 0; }
    }
    .spinner {
        border: 3px solid var(--bg-secondary);
        border-top: 3px solid var(--accent);
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 0 auto;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .option-stake {
        font-size: 0.9em;
        opacity: 0.8;
    }
`;
document.head.appendChild(style);
