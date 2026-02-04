let tg = window.Telegram.WebApp;
let backendUrl = "https://tgqweasd.vercel.app";
let currentEventId = null;
let currentOptionIndex = null;

document.addEventListener('DOMContentLoaded', function() {
    tg.expand();
    setTimeout(() => {
        document.getElementById('loading').classList.add('hidden');
    }, 500);
    loadEvents();
    loadUserBalance();
});

async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(`${backendUrl}${url}`, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json();
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
        container.innerHTML = '<div style="text-align:center"><div class="spinner"></div></div>';
        
        const data = await apiRequest('/events');
        
        if (!data.events || data.events.length === 0) {
            container.innerHTML = '<p style="text-align:center;color:var(--text-secondary)">Нет событий</p>';
            return;
        }
        
        container.innerHTML = data.events.map(event => createEventCard(event)).join('');
    } catch (error) {
        showNotification('Не удалось загрузить события', 'error');
    }
}

function createEventCard(event) {
    const timeLeft = formatTimeLeft(event.time_left);
    return `
        <div class="event-card">
            <h3 class="event-title">${escapeHtml(event.title)}</h3>
            ${event.description ? `<p class="event-description">${escapeHtml(event.description)}</p>` : ''}
            <div class="event-timer">⏱️ ${timeLeft}</div>
            <div class="options-container">
                ${event.options.map(opt => createOptionButton(event.id, opt)).join('')}
            </div>
        </div>
    `;
}

function createOptionButton(eventId, option) {
    return `
        <button class="option-btn" onclick="openBetModal(${eventId}, ${option.index}, '${escapeHtml(option.text)}')">
            <span>${escapeHtml(option.text)}</span>
            <span>${Math.floor(option.total_points)} очков</span>
        </button>
    `;
}

function formatTimeLeft(seconds) {
    if (seconds < 0) return "Время вышло";
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return hours > 0 ? `${hours}ч ${minutes}м` : `${minutes}м`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadUserBalance() {
    try {
        const userId = tg.initDataUnsafe?.user?.id;
        if (!userId) return;
        
        const data = await apiRequest(`/user/${userId}`);
        document.getElementById('user-balance').textContent = Math.floor(data.points);
        document.getElementById('profile-balance').textContent = `${Math.floor(data.points)} очков`;
        document.getElementById('active-predictions').textContent = data.stats.active_predictions;
    } catch (error) {
        console.error('Ошибка загрузки баланса:', error);
    }
}

function showSection(sectionName) {
    document.querySelectorAll('.section').forEach(section => section.classList.add('hidden'));
    document.getElementById(`${sectionName}-section`).classList.remove('hidden');
    
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    event.target.closest('.nav-btn').classList.add('active');
}

function openBetModal(eventId, optionIndex, optionText) {
    const eventCard = document.querySelector(`[onclick*="${eventId}"]`).closest('.event-card');
    const title = eventCard.querySelector('.event-title').textContent;
    
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-option').textContent = `Вариант: ${optionText}`;
    document.getElementById('bet-modal').classList.remove('hidden');
    
    currentEventId = eventId;
    currentOptionIndex = optionIndex;
}

function closeModal() {
    document.getElementById('bet-modal').classList.add('hidden');
    currentEventId = null; currentOptionIndex = null;
}

async function confirmPrediction() {
    const points = parseInt(document.getElementById('points-input').value);
    if (!points || points < 1) {
        showNotification('Введите корректную сумму', 'error');
        return;
    }
    
    const userId = tg.initDataUnsafe?.user?.id;
    if (!userId) {
        showNotification('Ошибка авторизации', 'error');
        return;
    }
    
    try {
        const confirmBtn = document.querySelector('.modal-btn.confirm');
        confirmBtn.textContent = 'Отправка...';
        confirmBtn.disabled = true;
        
        await apiRequest('/predict', {
            method: 'POST',
            body: JSON.stringify({
                telegram_id: userId,
                event_id: currentEventId,
                option_index: currentOptionIndex,
                points: points
            })
        });
        
        showNotification('Прогноз принят! ✅', 'success');
        closeModal();
        loadEvents();
        loadUserBalance();
    } catch (error) {
        showNotification(error.message || 'Ошибка прогноза', 'error');
    } finally {
        const confirmBtn = document.querySelector('.modal-btn.confirm');
        confirmBtn.textContent = 'Прогноз';
        confirmBtn.disabled = false;
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
        background: ${type === 'error' ? '#E22134' : 'var(--accent)'}; color: white;
        padding: 12px 20px; border-radius: 8px; z-index: 2000; font-weight: 600;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);

}

