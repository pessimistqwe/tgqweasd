/**
 * Betting Engine Frontend Module
 * 
 * Модуль для работы со ставками в Telegram Mini App:
 * - usePlaceBet hook (в vanilla JS стиле)
 * - BetModal компонент
 * - Валидация и обработка ошибок
 */

// ==================== Constants ====================

const BETTING_API_BASE = '/api/betting';

// ==================== Utilities ====================

/**
 * Получить initData из Telegram WebApp
 * @returns {string|null}
 */
function getTelegramInitData() {
    if (window.Telegram?.WebApp?.initData) {
        return window.Telegram.WebApp.initData;
    }
    return null;
}

/**
 * Выполнить API запрос с авторизацией через Telegram
 * @param {string} endpoint 
 * @param {object} options 
 * @returns {Promise<any>}
 */
async function bettingApiRequest(endpoint, options = {}) {
    const initData = getTelegramInitData();
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };
    
    // Добавляем Telegram initData для аутентификации
    if (initData) {
        headers['X-Telegram-Init-Data'] = initData;
    }
    
    const response = await fetch(`${BETTING_API_BASE}${endpoint}`, {
        ...options,
        headers,
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        throw new BettingError(data.detail || 'Request failed');
    }
    
    return data;
}

/**
 * Форматировать число как деньги
 * @param {number|string} value 
 * @returns {string}
 */
function formatMoney(value) {
    const num = parseFloat(value);
    return num.toFixed(2) + ' USDT';
}

// ==================== Error Classes ====================

class BettingError extends Error {
    constructor(message) {
        super(message);
        this.name = 'BettingError';
    }
}

class InsufficientBalanceError extends BettingError {
    constructor(message) {
        super(message);
        this.name = 'InsufficientBalanceError';
    }
}

class ValidationError extends BettingError {
    constructor(message) {
        super(message);
        this.name = 'ValidationError';
    }
}

// ==================== Betting Hook (usePlaceBet) ====================

/**
 * Хук для размещения ставок
 * 
 * Использование:
 * const { placeBet, loading, error } = usePlaceBet();
 * await placeBet({ marketId, amount, direction, ... });
 */
function usePlaceBet() {
    let loading = false;
    let error = null;
    let callbacks = {
        onSuccess: null,
        onError: null,
        onLoadingChange: null,
    };
    
    /**
     * Разместить ставку на событие
     * @param {object} params 
     * @param {number} params.marketId - ID рынка
     * @param {number} params.optionIndex - Индекс опциона
     * @param {number} params.amount - Сумма ставки
     * @param {'yes'|'no'} params.direction - Направление
     * @returns {Promise<object>}
     */
    async function placeEventBet({ marketId, optionIndex, amount, direction }) {
        loading = true;
        error = null;
        notifyLoadingChange();
        
        try {
            const result = await bettingApiRequest('/event/place', {
                method: 'POST',
                body: JSON.stringify({
                    market_id: marketId,
                    option_index: optionIndex,
                    amount: amount.toString(),
                    direction: direction,
                }),
            });
            
            notifySuccess(result);
            return result;
            
        } catch (err) {
            error = err;
            notifyError(err);
            throw err;
            
        } finally {
            loading = false;
            notifyLoadingChange();
        }
    }
    
    /**
     * Разместить ставку на цену (Long/Short)
     * @param {object} params 
     * @param {number} params.marketId - ID рынка
     * @param {'long'|'short'} params.direction - Направление
     * @param {number} params.amount - Сумма (маржа)
     * @param {number} params.leverage - Плечо (по умолчанию 1)
     * @param {number} params.entryPrice - Цена входа
     * @param {string} params.symbol - Символ актива
     * @param {number} [params.takeProfit] - Тейк-профит
     * @param {number} [params.stopLoss] - Стоп-лосс
     * @returns {Promise<object>}
     */
    async function placePriceBet({ 
        marketId, 
        direction, 
        amount, 
        leverage = 1,
        entryPrice, 
        symbol,
        takeProfit = null,
        stopLoss = null,
    }) {
        loading = true;
        error = null;
        notifyLoadingChange();
        
        try {
            const result = await bettingApiRequest('/price/place', {
                method: 'POST',
                body: JSON.stringify({
                    market_id: marketId,
                    direction: direction,
                    amount: amount.toString(),
                    leverage: leverage.toString(),
                    entry_price: entryPrice.toString(),
                    symbol: symbol,
                    take_profit_price: takeProfit?.toString(),
                    stop_loss_price: stopLoss?.toString(),
                }),
            });
            
            notifySuccess(result);
            return result;
            
        } catch (err) {
            error = err;
            notifyError(err);
            throw err;
            
        } finally {
            loading = false;
            notifyLoadingChange();
        }
    }
    
    /**
     * Разместить краткосрочный прогноз (5 минут)
     * @param {object} params 
     * @param {number} params.marketId - ID рынка
     * @param {'long'|'short'} params.direction - Направление
     * @param {number} params.amount - Сумма ставки
     * @param {number} params.odds - Коэффициент
     * @param {number} params.entryPrice - Цена входа
     * @param {string} params.symbol - Символ актива
     * @param {number} [params.duration=300] - Длительность в секундах
     * @returns {Promise<object>}
     */
    async function placePricePrediction({ 
        marketId, 
        direction, 
        amount, 
        odds, 
        entryPrice, 
        symbol,
        duration = 300,
    }) {
        loading = true;
        error = null;
        notifyLoadingChange();
        
        try {
            const result = await bettingApiRequest('/prediction/place', {
                method: 'POST',
                body: JSON.stringify({
                    market_id: marketId,
                    direction: direction,
                    amount: amount.toString(),
                    odds: odds.toString(),
                    entry_price: entryPrice.toString(),
                    symbol: symbol,
                    duration_seconds: duration,
                }),
            });
            
            notifySuccess(result);
            return result;
            
        } catch (err) {
            error = err;
            notifyError(err);
            throw err;
            
        } finally {
            loading = false;
            notifyLoadingChange();
        }
    }
    
    // Callback notification helpers
    function notifySuccess(result) {
        if (callbacks.onSuccess) {
            callbacks.onSuccess(result);
        }
    }
    
    function notifyError(err) {
        if (callbacks.onError) {
            callbacks.onError(err);
        }
    }
    
    function notifyLoadingChange() {
        if (callbacks.onLoadingChange) {
            callbacks.onLoadingChange(loading);
        }
    }
    
    return {
        placeEventBet,
        placePriceBet,
        placePricePrediction,
        getLoading: () => loading,
        getError: () => error,
        setCallbacks: (newCallbacks) => {
            callbacks = { ...callbacks, ...newCallbacks };
        },
    };
}

// ==================== Bet Modal Component ====================

/**
 * Компонент модального окна для размещения ставки
 * 
 * Использование:
 * const modal = new BetModal();
 * modal.open({ marketId, optionIndex, currentPrice, balance });
 */
class BetModal {
    constructor() {
        this.modal = null;
        this.currentBetType = 'event'; // 'event' | 'price' | 'prediction'
        this.bettingHook = usePlaceBet();
        this.config = {};
        
        this.setupEventListeners();
    }
    
    /**
     * Открыть модальное окно
     * @param {object} config 
     * @param {'event'|'price'|'prediction'} config.type - Тип ставки
     * @param {number} config.marketId - ID рынка
     * @param {number} [config.optionIndex] - Индекс опциона (для event)
     * @param {string} [config.optionText] - Текст опциона (для event)
     * @param {number} [config.currentPrice] - Текущая цена
     * @param {number} [config.odds] - Коэффициент (для prediction)
     * @param {number} config.balance - Баланс пользователя
     * @param {string} [config.symbol] - Символ актива (для price/prediction)
     */
    open(config) {
        this.config = config;
        this.currentBetType = config.type;
        
        this.render();
        this.show();
    }
    
    /**
     * Закрыть модальное окно
     */
    close() {
        if (this.modal) {
            this.modal.classList.add('hidden');
            setTimeout(() => {
                if (this.modal) {
                    this.modal.remove();
                    this.modal = null;
                }
            }, 200);
        }
    }
    
    /**
     * Создать HTML модального окна
     */
    render() {
        const { type, optionText, currentPrice, odds, balance, symbol } = this.config;
        
        const title = type === 'event' 
            ? `Ставка на ${optionText || 'событие'}`
            : type === 'price'
                ? `Прогноз цены (${symbol || 'BTC'})`
                : `Быстрый прогноз (${symbol || 'BTC'})`;
        
        const content = this.renderContent();
        
        const html = `
            <div class="bet-modal-overlay" onclick="betModal.close()">
                <div class="bet-modal" onclick="event.stopPropagation()">
                    <div class="bet-modal-header">
                        <h3>${title}</h3>
                        <button class="bet-modal-close" onclick="betModal.close()">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M18 6L6 18M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    
                    <div class="bet-modal-body">
                        ${content}
                    </div>
                </div>
            </div>
        `;
        
        // Создаём элемент
        const container = document.createElement('div');
        container.innerHTML = html;
        this.modal = container.firstElementChild;
        
        document.body.appendChild(this.modal);
    }
    
    /**
     * Рендер контента в зависимости от типа ставки
     */
    renderContent() {
        const { type, currentPrice, odds, balance, symbol } = this.config;
        
        if (type === 'event') {
            return this.renderEventBetContent();
        } else if (type === 'prediction') {
            return this.renderPredictionContent();
        } else {
            return this.renderPriceBetContent();
        }
    }
    
    /**
     * Контент для ставки на событие
     */
    renderEventBetContent() {
        const { currentPrice, balance } = this.config;
        const price = currentPrice || 0.5;
        
        return `
            <div class="bet-form">
                <div class="bet-info-row">
                    <span>Цена за акцию:</span>
                    <span class="bet-info-value">${price.toFixed(2)}</span>
                </div>
                
                <div class="bet-input-group">
                    <label for="bet-amount">Сумма ставки (USDT)</label>
                    <input 
                        type="number" 
                        id="bet-amount" 
                        class="bet-amount-input"
                        placeholder="0.00" 
                        step="0.01"
                        min="0.01"
                        max="${balance}"
                    />
                    <div class="bet-balance-hint">
                        Доступно: ${balance.toFixed(2)} USDT
                    </div>
                </div>
                
                <div class="bet-potential-profit">
                    <div class="bet-info-row">
                        <span>Количество акций:</span>
                        <span class="bet-info-value" id="shares-value">--</span>
                    </div>
                    <div class="bet-info-row">
                        <span>Потенциальный выигрыш:</span>
                        <span class="bet-info-value profit" id="potential-profit">--</span>
                    </div>
                </div>
                
                <button 
                    class="bet-submit-btn" 
                    id="place-bet-btn"
                    onclick="betModal.submitEventBet()"
                    disabled
                >
                    Разместить ставку
                </button>
                
                <div class="bet-error" id="bet-error" style="display: none;"></div>
            </div>
        `;
    }
    
    /**
     * Контент для прогноза цены
     */
    renderPredictionContent() {
        const { odds, balance, symbol, direction } = this.config;
        
        return `
            <div class="bet-form">
                <div class="bet-info-row">
                    <span>Направление:</span>
                    <span class="bet-info-value ${direction === 'long' ? 'up' : 'down'}">
                        ${direction === 'long' ? '▲ ВВЕРХ' : '▼ ВНИЗ'}
                    </span>
                </div>
                
                <div class="bet-info-row">
                    <span>Коэффициент:</span>
                    <span class="bet-info-value">${odds.toFixed(2)}x</span>
                </div>
                
                <div class="bet-input-group">
                    <label for="bet-amount">Сумма ставки (USDT)</label>
                    <input 
                        type="number" 
                        id="bet-amount" 
                        class="bet-amount-input"
                        placeholder="0.00" 
                        step="0.01"
                        min="0.01"
                        max="${balance}"
                    />
                    <div class="bet-balance-hint">
                        Доступно: ${balance.toFixed(2)} USDT
                    </div>
                </div>
                
                <div class="bet-potential-profit">
                    <div class="bet-info-row">
                        <span>Потенциальный выигрыш:</span>
                        <span class="bet-info-value profit" id="potential-profit">--</span>
                    </div>
                    <div class="bet-info-row">
                        <span>Длительность:</span>
                        <span class="bet-info-value">5 минут</span>
                    </div>
                </div>
                
                <button 
                    class="bet-submit-btn" 
                    id="place-bet-btn"
                    onclick="betModal.submitPrediction()"
                    disabled
                >
                    Разместить прогноз
                </button>
                
                <div class="bet-error" id="bet-error" style="display: none;"></div>
            </div>
        `;
    }
    
    /**
     * Контент для ставки на цену
     */
    renderPriceBetContent() {
        const { balance, symbol, direction, currentPrice } = this.config;
        
        return `
            <div class="bet-form">
                <div class="bet-info-row">
                    <span>Направление:</span>
                    <span class="bet-info-value ${direction === 'long' ? 'up' : 'down'}">
                        ${direction === 'long' ? '▲ LONG' : '▼ SHORT'}
                    </span>
                </div>
                
                <div class="bet-info-row">
                    <span>Текущая цена:</span>
                    <span class="bet-info-value">${currentPrice?.toFixed(2) || '--'}</span>
                </div>
                
                <div class="bet-input-group">
                    <label for="bet-amount">Маржа (USDT)</label>
                    <input 
                        type="number" 
                        id="bet-amount" 
                        class="bet-amount-input"
                        placeholder="0.00" 
                        step="0.01"
                        min="0.01"
                        max="${balance}"
                    />
                    <div class="bet-balance-hint">
                        Доступно: ${balance.toFixed(2)} USDT
                    </div>
                </div>
                
                <div class="bet-input-group">
                    <label for="bet-leverage">Плечо</label>
                    <select id="bet-leverage" class="bet-leverage-select" onchange="betModal.updateLeverage()">
                        <option value="1">1x</option>
                        <option value="5">5x</option>
                        <option value="10">10x</option>
                        <option value="20">20x</option>
                        <option value="50">50x</option>
                        <option value="100">100x</option>
                    </select>
                </div>
                
                <div class="bet-potential-profit">
                    <div class="bet-info-row">
                        <span>Размер позиции:</span>
                        <span class="bet-info-value" id="position-size">--</span>
                    </div>
                    <div class="bet-info-row">
                        <span>Цена ликвидации:</span>
                        <span class="bet-info-value" id="liquidation-price">--</span>
                    </div>
                </div>
                
                <button 
                    class="bet-submit-btn" 
                    id="place-bet-btn"
                    onclick="betModal.submitPriceBet()"
                    disabled
                >
                    Открыть позицию
                </button>
                
                <div class="bet-error" id="bet-error" style="display: none;"></div>
            </div>
        `;
    }
    
    show() {
        if (this.modal) {
            this.modal.classList.remove('hidden');
        }
        
        // Добавляем обработчик изменения суммы
        const amountInput = document.getElementById('bet-amount');
        if (amountInput) {
            amountInput.addEventListener('input', () => this.onAmountChange());
        }
        
        // Показываем Haptic Feedback
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
        }
    }
    
    /**
     * Обработчик изменения суммы ставки
     */
    onAmountChange() {
        const amountInput = document.getElementById('bet-amount');
        const submitBtn = document.getElementById('place-bet-btn');
        const amount = parseFloat(amountInput.value);
        
        // Валидация
        if (isNaN(amount) || amount <= 0) {
            submitBtn.disabled = true;
            this.updateProfitDisplay(0);
            return;
        }
        
        if (amount > this.config.balance) {
            submitBtn.disabled = true;
            this.showError('Недостаточно средств');
            return;
        }
        
        this.hideError();
        submitBtn.disabled = false;
        
        // Обновляем отображение потенциального выигрыша
        this.updateProfitDisplay(amount);
    }
    
    /**
     * Обновить отображение потенциального выигрыша
     */
    updateProfitDisplay(amount) {
        const profitEl = document.getElementById('potential-profit');
        const sharesEl = document.getElementById('shares-value');
        const positionSizeEl = document.getElementById('position-size');
        const liqPriceEl = document.getElementById('liquidation-price');
        
        if (!profitEl) return;
        
        if (this.currentBetType === 'event') {
            const price = this.config.currentPrice || 0.5;
            const shares = amount / price;
            const potential = shares * 1.0; // $1 за акцию если выиграл
            
            if (sharesEl) sharesEl.textContent = shares.toFixed(4);
            profitEl.textContent = formatMoney(potential);
            
        } else if (this.currentBetType === 'prediction') {
            const odds = this.config.odds || 1;
            const potential = amount * odds;
            profitEl.textContent = formatMoney(potential);
            
        } else if (this.currentBetType === 'price') {
            const leverage = parseFloat(document.getElementById('bet-leverage')?.value || '1');
            const positionSize = amount * leverage;
            
            if (positionSizeEl) positionSizeEl.textContent = formatMoney(positionSize);
            
            // Расчёт цены ликвидации (упрощённо)
            const entryPrice = this.config.currentPrice || 0;
            if (entryPrice > 0) {
                const liqPrice = this.config.direction === 'long'
                    ? entryPrice * (1 - 1/leverage)
                    : entryPrice * (1 + 1/leverage);
                if (liqPriceEl) liqPriceEl.textContent = '$' + liqPrice.toFixed(2);
            }
            
            profitEl.textContent = '--'; // Для price bet PnL зависит от движения
        }
    }
    
    /**
     * Обновить плечо (для price bet)
     */
    updateLeverage() {
        this.onAmountChange();
    }
    
    /**
     * Отправить ставку на событие
     */
    async submitEventBet() {
        const amountInput = document.getElementById('bet-amount');
        const amount = parseFloat(amountInput.value);
        const submitBtn = document.getElementById('place-bet-btn');
        
        if (!amount || amount <= 0) return;
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Размещение...';
        
        try {
            await this.bettingHook.placeEventBet({
                marketId: this.config.marketId,
                optionIndex: this.config.optionIndex,
                amount: amount,
                direction: this.config.direction || 'yes',
            });
            
            // Успех
            if (window.Telegram?.WebApp) {
                window.Telegram.WebApp.showPopup({
                    title: 'Ставка размещена!',
                    message: `Ваша ставка ${formatMoney(amount)} принята.`,
                });
            }
            
            this.close();
            
            // Callback если есть
            if (this.config.onSuccess) {
                this.config.onSuccess();
            }
            
        } catch (err) {
            this.showError(err.message || 'Ошибка при размещении ставки');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Разместить ставку';
        }
    }
    
    /**
     * Отправить прогноз
     */
    async submitPrediction() {
        const amountInput = document.getElementById('bet-amount');
        const amount = parseFloat(amountInput.value);
        const submitBtn = document.getElementById('place-bet-btn');
        
        if (!amount || amount <= 0) return;
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Размещение...';
        
        try {
            await this.bettingHook.placePricePrediction({
                marketId: this.config.marketId,
                direction: this.config.direction,
                amount: amount,
                odds: this.config.odds,
                entryPrice: this.config.entryPrice,
                symbol: this.config.symbol,
            });
            
            // Успех
            if (window.Telegram?.WebApp) {
                window.Telegram.WebApp.showPopup({
                    title: 'Прогноз размещён!',
                    message: `Ваш прогноз ${formatMoney(amount)} принят. Результат через 5 минут.`,
                });
            }
            
            this.close();
            
            if (this.config.onSuccess) {
                this.config.onSuccess();
            }
            
        } catch (err) {
            this.showError(err.message || 'Ошибка при размещении прогноза');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Разместить прогноз';
        }
    }
    
    /**
     * Отправить ставку на цену
     */
    async submitPriceBet() {
        const amountInput = document.getElementById('bet-amount');
        const leverageInput = document.getElementById('bet-leverage');
        const amount = parseFloat(amountInput.value);
        const leverage = parseFloat(leverageInput.value);
        const submitBtn = document.getElementById('place-bet-btn');
        
        if (!amount || amount <= 0) return;
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Открытие...';
        
        try {
            await this.bettingHook.placePriceBet({
                marketId: this.config.marketId,
                direction: this.config.direction,
                amount: amount,
                leverage: leverage,
                entryPrice: this.config.entryPrice,
                symbol: this.config.symbol,
            });
            
            // Успех
            if (window.Telegram?.WebApp) {
                window.Telegram.WebApp.showPopup({
                    title: 'Позиция открыта!',
                    message: `Ваша позиция ${formatMoney(amount)} с плечом ${leverage}x открыта.`,
                });
            }
            
            this.close();
            
            if (this.config.onSuccess) {
                this.config.onSuccess();
            }
            
        } catch (err) {
            this.showError(err.message || 'Ошибка при открытии позиции');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Открыть позицию';
        }
    }
    
    showError(message) {
        const errorEl = document.getElementById('bet-error');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
        
        // Haptic feedback для ошибки
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.notificationOccurred('error');
        }
    }
    
    hideError() {
        const errorEl = document.getElementById('bet-error');
        if (errorEl) {
            errorEl.style.display = 'none';
        }
    }
    
    setupEventListeners() {
        // Закрытие по ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal) {
                this.close();
            }
        });
    }
}

// Глобальный экземпляр для доступа из HTML
window.betModal = new BetModal();

// Экспорт для модульного использования
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        usePlaceBet,
        BetModal,
        bettingApiRequest,
        getTelegramInitData,
        formatMoney,
    };
}
