/**
 * PolymarketPriceService - Сервис для получения реальных цен из Polymarket
 * 
 * Функционал:
 * - Получение цен через backend API
 * - Кэширование цен (30 секунд TTL)
 * - Массовый запрос цен для нескольких токенов
 * - Авто-обновление цен в реальном времени
 * 
 * Usage:
 *   const price = await PolymarketPriceService.getPrice(tokenId);
 *   const prices = await PolymarketPriceService.getPrices([tokenId1, tokenId2]);
 */

// ==================== Configuration ====================

const PRICE_CONFIG = {
    CACHE_TTL_MS: 30 * 1000,  // 30 секунд
    API_BASE: '',  // Будет установлен при инициализации
    AUTO_REFRESH_INTERVAL_MS: 30 * 1000,  // Авто-обновление каждые 30 секунд
};

// ==================== State ====================

let priceCache = new Map();  // token_id -> { price, timestamp }
let autoRefreshInterval = null;
let priceSubscribers = [];  // Callbacks для обновления цен

// ==================== Helper Functions ====================

/**
 * Получить API base URL
 */
function getPriceApiBase() {
    return window.__BACKEND_URL__
        || (window.location.hostname === 'localhost'
            ? 'http://localhost:8000'
            : window.location.origin);
}

/**
 * Получить цену из кэша
 */
function getCachedPrice(tokenId) {
    const cached = priceCache.get(tokenId);
    if (!cached) return null;
    
    const age = Date.now() - cached.timestamp;
    if (age > PRICE_CONFIG.CACHE_TTL_MS) {
        priceCache.delete(tokenId);
        return null;
    }
    
    return cached.price;
}

/**
 * Сохранить цену в кэш
 */
function saveToCache(tokenId, price) {
    priceCache.set(tokenId, {
        price,
        timestamp: Date.now()
    });
    
    // Очищаем старый кэш (максимум 100 записей)
    if (priceCache.size > 100) {
        const firstKey = priceCache.keys().next().value;
        priceCache.delete(firstKey);
    }
}

/**
 * Уведомить подписчиков об обновлении цен
 */
function notifySubscribers(prices) {
    priceSubscribers.forEach(callback => {
        try {
            callback(prices);
        } catch (e) {
            console.error('Error in price subscriber callback:', e);
        }
    });
}

// ==================== API Functions ====================

/**
 * Получить цену для одного токена
 * @param {string} tokenId - Polymarket token ID
 * @param {boolean} useCache - Использовать ли кэш
 * @returns {Promise<Object|null>}
 */
async function getPrice(tokenId, useCache = true) {
    // Проверяем кэш
    if (useCache) {
        const cached = getCachedPrice(tokenId);
        if (cached) {
            console.log('💾 [PriceService] Cache hit for', tokenId);
            return cached;
        }
    }
    
    try {
        const url = `${getPriceApiBase()}/api/polymarket/price/${encodeURIComponent(tokenId)}`;
        console.log('📊 [PriceService] Fetching price:', url);
        
        const response = await fetch(url, {
            headers: { 'Accept': 'application/json' },
            signal: AbortSignal.timeout(10000)  // 10 секунд timeout
        });
        
        if (!response.ok) {
            if (response.status === 404) {
                console.warn('⚠️ [PriceService] Price not found for', tokenId);
                return null;
            }
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ [PriceService] Price received:', data);
        
        const priceData = {
            token_id: data.token_id,
            price: data.price,  // 0-1 format
            price_percent: data.price_percent,  // 0-100 format
            bid: data.bid,
            ask: data.ask,
            last_trade: data.last_trade,
            volume_24h: data.volume_24h,
            change_24h: data.change_24h,
            cached: data.cached
        };
        
        saveToCache(tokenId, priceData);
        return priceData;
        
    } catch (error) {
        console.error('❌ [PriceService] Error fetching price:', error.message);
        return getCachedPrice(tokenId);  // Fallback на кэш
    }
}

/**
 * Массовый запрос цен для нескольких токенов
 * @param {string[]} tokenIds - Список token ID
 * @param {boolean} useCache - Использовать ли кэш
 * @returns {Promise<Object>}
 */
async function getPrices(tokenIds, useCache = true) {
    if (!tokenIds || tokenIds.length === 0) {
        return {};
    }
    
    // Фильтруем уже закэшированные
    const toFetch = [];
    const results = {};
    
    if (useCache) {
        tokenIds.forEach(id => {
            const cached = getCachedPrice(id);
            if (cached) {
                results[id] = cached;
            } else {
                toFetch.push(id);
            }
        });
    } else {
        toFetch.push(...tokenIds);
    }
    
    if (toFetch.length === 0) {
        console.log('💾 [PriceService] All prices from cache:', tokenIds.length);
        return results;
    }
    
    try {
        // Массовый запрос
        const url = `${getPriceApiBase()}/api/polymarket/prices?token_ids=${encodeURIComponent(toFetch.join(','))}`;
        console.log('📊 [PriceService] Fetching prices:', url);
        
        const response = await fetch(url, {
            headers: { 'Accept': 'application/json' },
            signal: AbortSignal.timeout(15000)  // 15 секунд timeout
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        const prices = data.prices || {};
        
        // Сохраняем в кэш и результат
        Object.entries(prices).forEach(([tokenId, priceData]) => {
            results[tokenId] = priceData;
            saveToCache(tokenId, priceData);
        });
        
        console.log('✅ [PriceService] Prices received:', Object.keys(prices).length);
        return results;
        
    } catch (error) {
        console.error('❌ [PriceService] Error fetching prices:', error.message);
        // Fallback на кэш для всех
        tokenIds.forEach(id => {
            const cached = getCachedPrice(id);
            if (cached) results[id] = cached;
        });
        return results;
    }
}

/**
 * Получить цены для всех исходов события
 * @param {string} marketId - Polymarket market ID
 * @returns {Promise<Object>}
 */
async function getMarketPrices(marketId) {
    try {
        const url = `${getPriceApiBase()}/api/polymarket/price/market/${encodeURIComponent(marketId)}`;
        console.log('📊 [PriceService] Fetching market prices:', url);
        
        const response = await fetch(url, {
            headers: { 'Accept': 'application/json' },
            signal: AbortSignal.timeout(15000)
        });
        
        if (!response.ok) {
            return {};
        }
        
        const data = await response.json();
        return data.outcomes || {};
        
    } catch (error) {
        console.error('❌ [PriceService] Error fetching market prices:', error.message);
        return {};
    }
}

// ==================== Auto Refresh ====================

/**
 * Запустить авто-обновление цен
 * @param {string[]} tokenIds - Список token ID для обновления
 */
function startAutoRefresh(tokenIds) {
    if (autoRefreshInterval) {
        stopAutoRefresh();
    }
    
    console.log('🔄 [PriceService] Starting auto-refresh for', tokenIds.length, 'tokens');
    
    autoRefreshInterval = setInterval(async () => {
        console.log('🔄 [PriceService] Auto-refreshing prices...');
        const prices = await getPrices(tokenIds, false);  // Не использовать кэш
        notifySubscribers(prices);
    }, PRICE_CONFIG.AUTO_REFRESH_INTERVAL_MS);
}

/**
 * Остановить авто-обновление цен
 */
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        console.log('⏹️ [PriceService] Auto-refresh stopped');
    }
}

/**
 * Подписаться на обновления цен
 * @param {Function} callback - Функция callback(prices)
 */
function subscribeToPrices(callback) {
    priceSubscribers.push(callback);
    console.log('📬 [PriceService] Subscriber added, total:', priceSubscribers.length);
}

/**
 * Отписаться от обновлений цен
 * @param {Function} callback - Функция callback для удаления
 */
function unsubscribeFromPrices(callback) {
    const index = priceSubscribers.indexOf(callback);
    if (index > -1) {
        priceSubscribers.splice(index, 1);
        console.log('📬 [PriceService] Subscriber removed, total:', priceSubscribers.length);
    }
}

// ==================== Sync with Event Cards ====================

/**
 * Обновить цены в карточках событий
 * @param {Array} events - Список событий с options
 */
async function updateEventPrices(events) {
    console.log('🔄 [PriceService] Updating event prices for', events.length, 'events');
    
    // Собираем все token_id из событий
    const tokenIds = [];
    const eventOptionMap = new Map();  // token_id -> { eventId, optionIndex }
    
    events.forEach(event => {
        if (!event.polymarket_id || !event.options) return;
        
        event.options.forEach(option => {
            if (option.polymarket_token_id) {
                tokenIds.push(option.polymarket_token_id);
                eventOptionMap.set(option.polymarket_token_id, {
                    eventId: event.id,
                    optionIndex: option.index
                });
            }
        });
    });
    
    if (tokenIds.length === 0) {
        console.log('💾 [PriceService] No token_ids to fetch');
        return;
    }
    
    // Получаем цены
    const prices = await getPrices(tokenIds);
    
    // Обновляем UI
    Object.entries(prices).forEach(([tokenId, priceData]) => {
        const mapping = eventOptionMap.get(tokenId);
        if (!mapping) return;
        
        const optionElement = document.querySelector(
            `[data-event-id="${mapping.eventId}"][data-option-index="${mapping.optionIndex}"]`
        );
        
        if (optionElement) {
            // Обновляем цену в UI
            const pricePercent = priceData.price_percent || (priceData.price * 100) || 0;
            const priceEl = optionElement.querySelector('.option-price, .probability');
            if (priceEl) {
                priceEl.textContent = `${pricePercent.toFixed(1)}%`;
            }
            
            // Добавляем индикатор изменения
            const changeEl = optionElement.querySelector('.price-change');
            if (changeEl && priceData.change_24h !== undefined) {
                const change = priceData.change_24h;
                changeEl.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
                changeEl.className = `price-change ${change >= 0 ? 'positive' : 'negative'}`;
            }
        }
    });
    
    console.log('✅ [PriceService] Prices updated in UI');
}

// ==================== Stats ====================

/**
 * Получить статистику кэша
 */
function getCacheStats() {
    return {
        cachedPrices: priceCache.size,
        cacheTTL: PRICE_CONFIG.CACHE_TTL_MS / 1000,
        subscribers: priceSubscribers.length
    };
}

/**
 * Очистить кэш
 */
function clearCache() {
    priceCache.clear();
    console.log('🧹 [PriceService] Cache cleared');
}

// ==================== Export ====================

// Делаем функции доступными глобально безопасно
try {
    window.PolymarketPriceService = {
        getPrice,
        getPrices,
        getMarketPrices,
        startAutoRefresh,
        stopAutoRefresh,
        subscribeToPrices,
        unsubscribeFromPrices,
        updateEventPrices,
        getCacheStats,
        clearCache
    };
    console.log('✅ [PolymarketPriceService] Модуль загружен');
} catch (e) {
    console.error('❌ [PolymarketPriceService] Failed to initialize:', e);
    window.PolymarketPriceService = null;
}
