/**
 * PolymarketChartService - Сервис для загрузки реальных данных графиков из Polymarket
 *
 * Особенности:
 * 1. Загружает реальные исторические данные через Polymarket Candles API
 * 2. Поддерживает различные разрешения (minute, hour, day, week)
 * 3. Кэширование данных для производительности
 * 4. Fallback на синтетические данные при недоступности API
 * 5. Интеграция с локальной базой данных PriceHistory
 *
 * API Documentation: https://docs.polymarket.com/
 */

// ==================== Configuration ====================

const POLYMARKET_CANDLES_URL = 'https://gamma-api.polymarket.com/candles';
const POLYMARKET_MARKETS_URL = 'https://gamma-api.polymarket.com/markets';

// Разрешения свечей
const POLYMARKET_RESOLUTIONS = {
    '1m': 'minute',
    '5m': 'minute',
    '15m': 'hour',
    '30m': 'hour',
    '1h': 'hour',
    '4h': 'hour',
    '1d': 'day',
    '1w': 'week'
};

// Лимиты для каждого разрешения
const POLYMARKET_LIMITS = {
    'minute': 100,
    'hour': 168,
    'day': 90,
    'week': 52
};

// Timeout для запросов (15 секунд)
const POLYMARKET_CHART_TIMEOUT_MS = 15000;

// TTL кэша (3 минуты для реальных данных) - УНИКАЛЬНОЕ ИМЯ
const POLYMARKET_CACHE_TTL_MS = 3 * 60 * 1000;

// Headers для запросов
const POLYMARKET_HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
};

// Кэш данных
const polymarketCache = new Map();

// ==================== Helper Functions ====================

/**
 * Получить данные из кэша
 */
function getFromPolymarketCache(key) {
    const cached = polymarketCache.get(key);
    if (!cached) return null;

    const age = Date.now() - cached.timestamp;
    if (age > POLYMARKET_CACHE_TTL_MS) {
        console.log('⚠️ [PolymarketChart] Cache expired for', key);
        polymarketCache.delete(key);
        return null;
    }

    return cached.data;
}

/**
 * Сохранить данные в кэш
 */
function saveToPolymarketCache(key, data) {
    polymarketCache.set(key, {
        data,
        timestamp: Date.now()
    });
    console.log('💾 [PolymarketChart] Cached data for', key);
}

/**
 * Конвертировать интервал в разрешение Polymarket
 */
function getPolymarketResolution(interval) {
    return POLYMARKET_RESOLUTIONS[interval] || 'hour';
}

/**
 * Получить лимит свечей для разрешения
 */
function getPolymarketLimit(resolution) {
    return POLYMARKET_LIMITS[resolution] || 168;
}

// ==================== PolymarketChartService Class ====================

class PolymarketChartService {
    constructor() {
        this.currentMarketId = null;
        this.currentOutcome = null;
        this.currentResolution = null;
    }

    /**
     * Загружает исторические данные свечей из Polymarket API
     * @param {string} marketId - ID рынка (conditionId из Polymarket)
     * @param {string} outcome - Название исхода (например, "Yes", "No")
     * @param {string} interval - Таймфрейм ('1m', '5m', '1h', etc.)
     * @param {number} limit - Количество свечей
     * @returns {Promise<{labels: string[], prices: number[], candles: Array, firstPrice: number, lastPrice: number}>}
     */
    async loadCandles(marketId, outcome, interval = '1h', limit = 168) {
        const resolution = getPolymarketResolution(interval);
        const polymarketLimit = Math.min(limit, getPolymarketLimit(resolution));

        // Нормализация названия исхода
        const normalizedOutcome = this.normalizeOutcome(outcome);

        console.log('📊 [PolymarketChart] ========== ЗАГРУЗКА ДАННЫХ POLYMARKET ==========');
        console.log('📊 [PolymarketChart] Market ID:', marketId);
        console.log('📊 [PolymarketChart] Outcome:', outcome, '→', normalizedOutcome);
        console.log('📊 [PolymarketChart] Interval:', interval, '(', resolution, ')');
        console.log('📊 [PolymarketChart] Limit:', polymarketLimit);

        const cacheKey = `${marketId}-${normalizedOutcome}-${resolution}`;

        // Проверяем кэш
        const cachedData = getFromPolymarketCache(cacheKey);
        if (cachedData) {
            console.log('💾 [PolymarketChart] Кэш найден');
            return cachedData;
        }

        // ПРИОРИТЕТ 1: Backend API (наш proxy)
        try {
            console.log('🔄 [PolymarketChart] Attempt 1: Backend API (/api/polymarket/chart)');

            const backendUrl = `/api/polymarket/chart/${encodeURIComponent(marketId)}?outcome=${encodeURIComponent(normalizedOutcome)}&resolution=${resolution}&limit=${polymarketLimit}`;

            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                console.log('⏱️ [PolymarketChart] Backend request timeout');
                controller.abort();
            }, POLYMARKET_CHART_TIMEOUT_MS);

            const response = await fetch(backendUrl, {
                signal: controller.signal,
                headers: { 'Accept': 'application/json' }
            });
            clearTimeout(timeoutId);

            if (response.ok) {
                const data = await response.json();
                console.log('✅ [PolymarketChart] Backend API success:', data.candles?.length || 0, 'candles');

                const result = {
                    labels: data.labels || [],
                    prices: data.prices || [],
                    candles: data.candles || [],
                    firstPrice: data.first_price || 0,
                    lastPrice: data.last_price || 0,
                    priceChange: data.price_change || 0,
                    source: data.source || 'polymarket'
                };

                // Сохраняем в кэш
                saveToPolymarketCache(cacheKey, result);

                return result;
            } else {
                console.warn('⚠️ [PolymarketChart] Backend API returned:', response.status);
            }
        } catch (error) {
            console.warn('⚠️ [PolymarketChart] Backend API failed:', error.message);
        }

        // ПРИОРИТЕТ 2: Прямой Polymarket API
        try {
            console.log('🔄 [PolymarketChart] Attempt 2: Direct Polymarket API');

            const url = `${POLYMARKET_CANDLES_URL}?market=${encodeURIComponent(marketId)}&outcome=${encodeURIComponent(normalizedOutcome)}&resolution=${resolution}&limit=${polymarketLimit}`;
            console.log('📊 [PolymarketChart] Request URL:', url);

            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                console.log('⏱️ [PolymarketChart] Polymarket request timeout');
                controller.abort();
            }, POLYMARKET_CHART_TIMEOUT_MS);

            const response = await fetch(url, {
                signal: controller.signal,
                headers: POLYMARKET_HEADERS
            });
            clearTimeout(timeoutId);

            console.log('📊 [PolymarketChart] Response status:', response.status);

            if (response.status === 404) {
                console.warn('⚠️ [PolymarketChart] No candles data for this market/outcome');
                // Не выбрасываем ошибку, пробуем fallback
            } else if (!response.ok) {
                throw new Error(`Polymarket API error: ${response.status}`);
            } else {
                const rawData = await response.json();
                console.log('📊 [PolymarketChart] Raw candles data:', rawData?.length || 0, 'items');

                if (!rawData || rawData.length === 0) {
                    console.warn('⚠️ [PolymarketChart] Empty response from Polymarket');
                } else {
                    // Polymarket возвращает массив [timestamp_ms, open, high, low, close, volume]
                    const candles = rawData.map(candle => ({
                        timestamp: candle[0],
                        open: candle[1] / 100,  // Конвертируем 0-100 в 0-1
                        high: candle[2] / 100,
                        low: candle[3] / 100,
                        close: candle[4] / 100,
                        volume: candle[5]
                    }));

                    const labels = candles.map(c => new Date(c.timestamp).toISOString());
                    const prices = candles.map(c => c.close);
                    const firstPrice = prices[0] || 0;
                    const lastPrice = prices[prices.length - 1] || 0;
                    const priceChange = firstPrice > 0 ? ((lastPrice - firstPrice) / firstPrice * 100) : 0;

                    const result = {
                        labels,
                        prices,
                        candles,
                        firstPrice,
                        lastPrice,
                        priceChange,
                        source: 'polymarket'
                    };

                    console.log('📊 [PolymarketChart] Processed:', candles.length, 'candles');
                    console.log('📊 [PolymarketChart] Price range:', firstPrice.toFixed(3), '-', lastPrice.toFixed(3));
                    console.log('📊 [PolymarketChart] Price change:', priceChange.toFixed(2), '%');

                    // Сохраняем в кэш
                    saveToPolymarketCache(cacheKey, result);

                    return result;
                }
            }
        } catch (error) {
            console.error('❌ [PolymarketChart] Direct API error:', error.message);
        }

        // ПРИОРИТЕТ 3: Fallback на локальную базу данных (через backend)
        try {
            console.log('🔄 [PolymarketChart] Attempt 3: Local DB fallback');

            // Пытаемся получить данные из локальной БД через backend
            // Это работает если данные были ранее синхронизированы
            const response = await fetch(`/events/polymarket/${marketId}/chart?outcome=${encodeURIComponent(normalizedOutcome)}`);

            if (response.ok) {
                const data = await response.json();
                console.log('✅ [PolymarketChart] Local DB fallback success');

                const result = {
                    labels: data.labels || [],
                    prices: data.prices || [],
                    candles: data.candles || [],
                    firstPrice: data.first_price || 0,
                    lastPrice: data.last_price || 0,
                    source: 'local_db'
                };

                saveToPolymarketCache(cacheKey, result);
                return result;
            }
        } catch (error) {
            console.warn('⚠️ [PolymarketChart] Local DB fallback failed');
        }

        // ПРИОРИТЕТ 4: Данные недоступны (Синтетические данные удалены)
        console.warn('⚠️ [PolymarketChart] All sources failed, no data available');
        throw new Error("Исторические данные графика недоступны для данного рынка.");
    }



    /**
     * Нормализует название исхода
     */
    normalizeOutcome(outcome) {
        if (!outcome) return 'Yes';

        const normalized = outcome.trim();

        // Polymarket использует точные названия исходов
        return normalized;
    }

    /**
     * Получает интервал в миллисекундах для разрешения
     */
    getIntervalMs(resolution) {
        const intervals = {
            'minute': 60 * 1000,
            'hour': 60 * 60 * 1000,
            'day': 24 * 60 * 60 * 1000,
            'week': 7 * 24 * 60 * 60 * 1000
        };
        return intervals[resolution] || intervals['hour'];
    }

    /**
     * Простой хэш строки
     */
    hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash);
    }

    /**
     * Получить детали рынка из Polymarket
     */
    async getMarketDetails(marketId) {
        try {
            console.log('📊 [PolymarketChart] Fetching market details for', marketId);

            const response = await fetch(`${POLYMARKET_MARKETS_URL}?ids=${marketId}`, {
                headers: POLYMARKET_HEADERS
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            const markets = data.markets || data.events || [];

            return markets.find(m => m.id === marketId || m.conditionId === marketId) || null;
        } catch (error) {
            console.error('❌ [PolymarketChart] Market details error:', error.message);
            return null;
        }
    }

    /**
     * Очистить кэш
     */
    clearCache(marketId) {
        if (marketId) {
            const keysToDelete = Array.from(polymarketCache.keys())
                .filter(key => key.startsWith(marketId));
            keysToDelete.forEach(key => polymarketCache.delete(key));
            console.log('🧹 [PolymarketChart] Cleared cache for', marketId);
        } else {
            polymarketCache.clear();
            console.log('🧹 [PolymarketChart] Cleared all cache');
        }
    }

    /**
     * Получить статус сервиса
     */
    getStatus() {
        return {
            cacheSize: polymarketCache.size,
            currentMarketId: this.currentMarketId,
            currentOutcome: this.currentOutcome
        };
    }
}

// ==================== Export ====================

// Создаём глобальный экземпляр безопасно
try {
    window.polymarketChartService = new PolymarketChartService();
    window.PolymarketChartService = PolymarketChartService;
    window.POLYMARKET_RESOLUTIONS = POLYMARKET_RESOLUTIONS;
    window.POLYMARKET_LIMITS = POLYMARKET_LIMITS;
    console.log('✅ [PolymarketChartService] Модуль загружен');
} catch (e) {
    console.error('❌ [PolymarketChartService] Failed to initialize:', e);
    window.polymarketChartService = null;
    window.PolymarketChartService = null;
}
