let tg = window.Telegram.WebApp;
let backendUrl = "https://tgqweasd.vercel.app";
let currentEventId = null;
let currentOptionIndex = null;

document.addEventListener('DOMContentLoaded', function() {
    tg.expand();
    tg.ready();
    
    // Убираем загрузку
    setTimeout(() => {
        document.getElementById('loading').classList.add('hidden');
    }, 500);
    
    // Сначала синхронизируем с Polymarket (crypto раздел), потом грузим события
    syncPolymarketAndLoadEvents();
    loadUserBalance();
});

// Синхронизация с Polymarket + загрузка событий
async function syncPolymarketAndLoadEvents() {
    const eventsContainer = document.getElementById('events-container');
    eventsContainer.innerHTML = '<div class="loading-spinner"></div><p style="text-align:center;color:#888;">Синхронизация с Polymarket...</p>';
    
    try {
        // Шаг 1: Запускаем синхронизацию с Polymarket (только crypto события)
        const syncResponse = await fetch(`${backendUrl}/sync/polymarket`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        if (!syncResponse.ok) {
            console.warn('Sync warning:', await syncResponse.text());
        } else {
            const syncData = await syncResponse.json();
            console.log('Sync status:', syncData);
        }
        
        // Подождём немного для фоновой обработки
        await new Promise(r => setTimeout(r, 2000));
        
        // Шаг 2: Загружаем события
        await loadEvents();
        
    } catch (error) {
        console.error('Sync error:', error);
        // Если синхронизация не сработала - пробуем просто загрузить
        await loadEvents();
    }
}

// Загрузка событий
async function loadEvents() {
    const eventsContainer = document.getElementById('events-container');
    
    try {
        const response = await fetch(`${backendUrl}/events`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Events loaded:', data);
        
        if (!data.events || data.events.length === 0) {
            eventsContainer.innerHTML = `
                <div style="text-align:center;padding:40px;color:#888;">
                    <p>😕 Нет активных событий</p>
                    <button onclick="syncPolymarketAndLoadEvents()" 
                            style="margin-top:20px;padding:10px 20px;background:#22c55e;border:none;border-radius:8px;color:white;cursor:pointer;">
                        🔄 Обновить с Polymarket
                    </button>
                </div>
            `;
            return;
        }
        
        // Отображаем события
        eventsContainer.innerHTML = data.events.map(event => `
            <div class="event-card" onclick="openEvent(${event.id})">
                <div class="event-header">
                    <h3>${escapeHtml(event.title)}</h3>
                    <span class="time-left">⏱️ ${formatTime(event.time_left)}</span>
                </div>
                <p class="event-description">${escapeHtml(event.description || '')}</p>
                <div class="event-pool">💰 Пул: ${event.total_pool || 0} USDT</div>
                <div class="options-preview">
                    ${event.options.map((opt, idx) => `
                        <span class="option-tag">${escapeHtml(opt.text)}</span>
                    `).join('')}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading events:', error);
        eventsContainer.innerHTML = `
            <div style="text-align:center;padding:40px;color:#ff6b6b;">
                <p>❌ Ошибка загрузки</p>
                <p style="font-size:12px;color:#666;">${error.message}</p>
                <button onclick="syncPolymarketAndLoadEvents()" 
                        style="margin-top:20px;padding:10px 20px;background:#22c55e;border:none;border-radius:8px;color:white;cursor:pointer;">
                    🔄 Повторить
                </button>
            </div>
        `;
    }
}

// Загрузка баланса пользователя
async function loadUserBalance() {
    if (!tg.initDataUnsafe?.user?.id) {
        console.log('No user data');
        return;
    }
    
    const userId = tg.initDataUnsafe.user.id;
    
    try {
        const response = await fetch(`${backendUrl}/user/${userId}`);
        const data = await response.json();
        
        // Обновляем отображение баланса
        const balanceEl = document.getElementById('user-balance');
        if (balanceEl && data.balance_usdt !== undefined) {
            balanceEl.innerHTML = `💎 ${data.balance_usdt.toFixed(2)} USDT`;
        }
    } catch (error) {
        console.error('Balance load error:', error);
    }
}

// Открытие события для ставки
function openEvent(eventId) {
    currentEventId = eventId;
    // TODO: показать модальное окно с опциями
    console.log('Open event:', eventId);
}

// Вспомогательные функции
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(seconds) {
    if (!seconds || seconds < 0) return 'Завершено';
    const hours = Math.floor(seconds / 3600);
    const days = Math.floor(hours / 24);
    if (days > 0) return `${days}д ${hours % 24}ч`;
    return `${hours}ч ${Math.floor((seconds % 3600) / 60)}м`;
}

// Экспорт для использования в HTML
window.syncPolymarketAndLoadEvents = syncPolymarketAndLoadEvents;
window.loadEvents = loadEvents;
