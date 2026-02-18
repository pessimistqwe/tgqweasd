/**
 * BinanceService - Единая точка доступа к Binance API
 * 
 * Особенности:
 * 1. Загружает реальные исторические свечи через REST API
 * 2. Подключается к WebSocket для обновления в реальном времени
 * 3. Подробное логирование для отладки
 * 4. Проверка уникальности данных для разных монет
 */

// ==================== Конфигурация ====================

const BINANCE_API_BASE = 'https://api.binance.com/api/v3';
const BINANCE_WS_BASE = 'wss://stream.binance.com:9443/ws';

// Интервалы Binance
const BINANCE_INTERVALS = {
    '1m': '1m',
    '5m': '5m',
    '15m': '15m',
    '1h': '1h',
    '4h': '4h',
    '1d': '1d'
};

// Количество свечей для загрузки
const CANDLE_LIMITS = {
    '1m': 100,
    '5m': 100,
    '15m': 96,
    '1h': 168,
    '4h': 168,
    '1d': 90
};

// Хэш для проверки уникальности данных
let dataHashes = new Map();

// ==================== BinanceService Class ====================

class BinanceService {
    constructor() {
        this.webSocket = null;
        this.webSocketBuffer = [];
        this.webSocketUpdateTimeout = null;
        this.currentSymbol = null;
        this.currentInterval = null;
        this.priceCallback = null;
        this.tradeCallback = null;
        this.errorCallback = null;
    }

    /**
     * Загружает исторические свечи с Binance REST API
     * @param {string} symbol - Торговая пара (например, 'BTCUSDT')
     * @param {string} interval - Таймфрейм ('1m', '5m', '1h', etc.)
     * @returns {Promise<{labels: string[], prices: number[], candles: Array, firstPrice: number, lastPrice: number}>}
     */
    async loadHistoricalCandles(symbol, interval) {
        const binanceInterval = BINANCE_INTERVALS[interval] || '15m';
        const limit = CANDLE_LIMITS[interval] || 96;

        // Нормализация символа: ВЕРХНИЙ регистр для REST API
        const normalizedSymbol = symbol.toUpperCase();

        console.log('📊 [BinanceService] Загрузка исторических данных...');
        console.log('📊 [BinanceService] Символ:', symbol, '→', normalizedSymbol);
        console.log('📊 [BinanceService] Таймфрейм:', interval, '(', binanceInterval, ')');
        console.log('📊 [BinanceService] Лимит свечей:', limit);

        try {
            const url = `${BINANCE_API_BASE}/klines?symbol=${normalizedSymbol}&interval=${binanceInterval}&limit=${limit}`;
            console.log('📊 [BinanceService] REST запрос URL:', url);

            const response = await fetch(url);
            console.log('📊 [BinanceService] Статус ответа:', response.status, response.ok ? '✅' : '❌');

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Binance API error: ${response.status} - ${errorText}`);
            }

            const data = await response.json();
            console.log('📊 [BinanceService] Получено свечей:', data.length);

            if (data.length === 0) {
                console.warn('⚠️ [BinanceService] Нет данных от Binance API');
                return { labels: [], prices: [], candles: [], firstPrice: 0, lastPrice: 0 };
            }

            // Логируем первую и последнюю свечу
            const firstCandle = data[0];
            const lastCandle = data[data.length - 1];
            
            console.log('📊 [BinanceService] Первая свеча:', {
                timestamp: new Date(firstCandle[0]).toISOString(),
                open: parseFloat(firstCandle[1]),
                high: parseFloat(firstCandle[2]),
                low: parseFloat(firstCandle[3]),
                close: parseFloat(firstCandle[4])
            });
            
            console.log('📊 [BinanceService] Последняя свеча:', {
                timestamp: new Date(lastCandle[0]).toISOString(),
                open: parseFloat(lastCandle[1]),
                high: parseFloat(lastCandle[2]),
                low: parseFloat(lastCandle[3]),
                close: parseFloat(lastCandle[4])
            });

            // Обрабатываем данные
            const labels = [];
            const prices = [];
            const candles = [];

            data.forEach(candle => {
                const timestamp = candle[0];
                const open = parseFloat(candle[1]);
                const high = parseFloat(candle[2]);
                const low = parseFloat(candle[3]);
                const close = parseFloat(candle[4]);
                const volume = parseFloat(candle[5]);

                labels.push(new Date(timestamp).toISOString());
                prices.push(close);
                candles.push({ timestamp, open, high, low, close, volume });
            });

            const firstPrice = prices[0];
            const lastPrice = prices[prices.length - 1];

            console.log('📊 [BinanceService] Обработано данных - labels:', labels.length, 'prices:', prices.length);
            console.log('📊 [BinanceService] Диапазон цен:', firstPrice.toFixed(4), '-', lastPrice.toFixed(4));

            // Проверка уникальности данных
            const dataHash = this.calculateDataHash(prices);
            if (dataHashes.has(symbol) && dataHashes.get(symbol) === dataHash) {
                console.warn('⚠️ [BinanceService] Данные идентичны предыдущей загрузке для', symbol);
            }
            dataHashes.set(symbol, dataHash);

            // Проверка на шаблонные данные (если цены одинаковые - это подозрительно)
            const uniquePrices = new Set(prices);
            if (uniquePrices.size < prices.length * 0.9) {
                console.error('❌ [BinanceService] Подозрительные данные: много повторяющихся цен!', symbol);
            }

            return { labels, prices, candles, firstPrice, lastPrice };

        } catch (error) {
            console.error('❌ [BinanceService] Error loading historical candles:', error);
            if (this.errorCallback) {
                this.errorCallback(error);
            }
            throw error;
        }
    }

    /**
     * Подключается к Binance WebSocket для обновления в реальном времени
     * @param {string} symbol - Торговая пара (например, 'BTCUSDT')
     * @param {string} interval - Таймфрейм для kline стрима
     * @param {Function} onTrade - Callback для каждой сделки (price, timestamp)
     * @param {Function} onKline - Callback для каждой свечи (kline data)
     */
    connectWebSocket(symbol, interval = '1m', onTrade, onKline) {
        this.disconnectWebSocket();

        this.currentSymbol = symbol;
        this.currentInterval = interval;

        // Нормализация символа: НИЖНИЙ регистр для WebSocket
        const wsSymbol = symbol.toLowerCase();

        // Используем trade stream для реальных сделок
        const streamName = `${wsSymbol}@trade`;
        const wsUrl = `${BINANCE_WS_BASE}/${streamName}`;

        console.log('🔌 [BinanceService] Подключение к Binance WebSocket...');
        console.log('🔌 [BinanceService] URL:', wsUrl);
        console.log('🔌 [BinanceService] Символ:', symbol, '→', wsSymbol);

        this.webSocket = new WebSocket(wsUrl);
        this.webSocketBuffer = [];

        console.log('🔌 [BinanceService] Статус после создания:', this.getWebSocketStatus(this.webSocket.readyState));

        // Обработчик открытия соединения
        this.webSocket.onopen = () => {
            console.log('✅ [BinanceService] WebSocket соединение открыто!');
        };

        // Обработчик входящих сообщений
        this.webSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            // Формат trade сообщения: { e: 'trade', E: timestamp, s: symbol, t: tradeId, p: price, q: qty, ... }
            const price = parseFloat(data.p);
            const timestamp = new Date(data.E);
            const tradeId = data.t;

            console.log('🔌 [BinanceService] Получена сделка: price =', price.toFixed(4), 'tradeId =', tradeId);

            // Добавляем в буфер
            this.webSocketBuffer.push({ price, timestamp, tradeId });

            // Debounce обновления для плавности (обновляем каждые 200мс)
            if (this.webSocketUpdateTimeout) {
                clearTimeout(this.webSocketUpdateTimeout);
            }

            this.webSocketUpdateTimeout = setTimeout(() => {
                this.processWebSocketBuffer(onTrade);
            }, 200);
        };

        // Обработчик ошибок
        this.webSocket.onerror = (err) => {
            console.error('❌ [BinanceService] WebSocket error:', err);
            if (this.errorCallback) {
                this.errorCallback(err);
            }
        };

        // Обработчик закрытия - авто-реконнект
        this.webSocket.onclose = () => {
            console.log('🔌 [BinanceService] WebSocket закрыт, переподключение через 5с...');
            if (this.webSocketUpdateTimeout) {
                clearTimeout(this.webSocketUpdateTimeout);
            }
            setTimeout(() => {
                if (this.webSocket && this.webSocket.readyState === WebSocket.CLOSED) {
                    this.connectWebSocket(symbol, interval, onTrade, onKline);
                }
            }, 5000);
        };

        return this.webSocket;
    }

    /**
     * Обрабатывает буфер WebSocket сообщений
     */
    processWebSocketBuffer(onTrade) {
        if (this.webSocketBuffer.length === 0) {
            console.log('🔌 [BinanceService] Пропуск обновления: буфер пуст');
            return;
        }

        // Получаем последнюю цену из буфера
        const lastTrade = this.webSocketBuffer[this.webSocketBuffer.length - 1];
        const lastPrice = lastTrade.price;
        const lastTimestamp = lastTrade.timestamp;

        console.log('🔌 [BinanceService] Обработка буфера:', this.webSocketBuffer.length, 'сделок, последняя цена =', lastPrice.toFixed(4));

        // Вызываем callback для каждой сделки
        if (onTrade) {
            onTrade(lastPrice, lastTimestamp, this.webSocketBuffer);
        }

        // Вызываем глобальный callback
        if (this.priceCallback) {
            this.priceCallback(lastPrice, lastTimestamp);
        }

        // Очищаем буфер
        this.webSocketBuffer = [];
    }

    /**
     * Отключается от WebSocket
     */
    disconnectWebSocket() {
        if (this.webSocket) {
            console.log('🔌 [BinanceService] Отключение WebSocket...');
            this.webSocket.close();
            this.webSocket = null;
        }
        if (this.webSocketUpdateTimeout) {
            clearTimeout(this.webSocketUpdateTimeout);
            this.webSocketUpdateTimeout = null;
        }
        this.webSocketBuffer = [];
        this.currentSymbol = null;
        this.currentInterval = null;
    }

    /**
     * Устанавливает callback для обновления цены
     */
    setPriceCallback(callback) {
        this.priceCallback = callback;
    }

    /**
     * Устанавливает callback для ошибок
     */
    setErrorCallback(callback) {
        this.errorCallback = callback;
    }

    /**
     * Получает текущий символ
     */
    getCurrentSymbol() {
        return this.currentSymbol;
    }

    /**
     * Хэш для проверки уникальности данных
     */
    calculateDataHash(prices) {
        // Простой хэш на основе суммы и количества уникальных значений
        const sum = prices.reduce((a, b) => a + b, 0);
        const unique = new Set(prices).size;
        return `${prices.length}-${sum.toFixed(4)}-${unique}`;
    }

    /**
     * Статус WebSocket в текстовом формате
     */
    getWebSocketStatus(status) {
        const statuses = {
            [WebSocket.CONNECTING]: 'CONNECTING',
            [WebSocket.OPEN]: 'OPEN',
            [WebSocket.CLOSING]: 'CLOSING',
            [WebSocket.CLOSED]: 'CLOSED'
        };
        return statuses[status] || 'UNKNOWN';
    }

    /**
     * Полный цикл: загрузка истории + подключение WebSocket
     * @param {string} symbol - Торговая пара
     * @param {string} interval - Таймфрейм
     * @param {Function} onPriceUpdate - Callback для обновления цены
     * @param {Function} onTrade - Callback для каждой сделки
     * @returns {Promise<{firstPrice: number, lastPrice: number}>}
     */
    async initialize(symbol, interval, onPriceUpdate, onTrade) {
        console.log('🚀 [BinanceService] Инициализация для:', symbol, interval);
        
        this.setErrorCallback(onPriceUpdate);
        
        // Загружаем исторические данные
        const { labels, prices, firstPrice, lastPrice } = await this.loadHistoricalCandles(symbol, interval);

        // Подключаем WebSocket
        this.connectWebSocket(symbol, interval, onTrade);

        return { firstPrice, lastPrice, labels, prices };
    }
}

// ==================== Экспорт ====================

// Создаём глобальный экземпляр
window.binanceService = new BinanceService();

// Экспортируем класс и экземпляр
window.BinanceService = BinanceService;

console.log('✅ [BinanceService] Модуль загружен');
