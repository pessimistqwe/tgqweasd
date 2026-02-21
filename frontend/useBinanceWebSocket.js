/**
 * useBinanceWebSocket - Хук для работы с Binance WebSocket
 *
 * Особенности:
 * 1. Загружает реальные исторические свечи через REST API при старте
 * 2. Подключается к WebSocket для обновления в реальном времени
 * 3. Корректно обрабатывает смену таймфрейма
 * 4. Оптимизирован для производительности (обновляет график без полных ре-рендеров)
 * 5. Обработка ошибки 451 и других ошибок API
 * 6. Failover между зеркалами Binance
 * 7. Timeout для защиты от зависания
 * 8. Fallback UI при недоступности данных
 */

// Константы определяются в binanceService.js - используем глобальные
// const BINANCE_ENDPOINTS - из binanceService.js
// const BINANCE_INTERVALS - из binanceService.js
// const CANDLE_LIMITS - из binanceService.js
// const REQUEST_TIMEOUT_MS - из binanceService.js

let chartInstance = null;
let priceCallback = null;
let currentEndpointIndex = 0;

// Количество свечей для загрузки в зависимости от таймфрейма
const CANDLE_LIMITS = {
    '1m': 100,
    '5m': 100,
    '15m': 96,   // 24 часа
    '1h': 168,   // 7 дней
    '4h': 168,   // 28 дней
    '1d': 90     // 90 дней
};

// Timeout для запросов (15 секунд максимум)
// Используем REQUEST_TIMEOUT_MS из binanceService.js
// const REQUEST_TIMEOUT_MS = 15000;  // ЗАКОММЕНТИРОВАНО - используется из binanceService.js

// Состояние WebSocket
let binanceWebSocket = null;
let webSocketBuffer = [];
let webSocketUpdateTimeout = null;
// chartInstance уже объявлен выше (строка 21)
let currentChartLabels = [];
let currentChartPrices = [];
let chartYMin = null;
let chartYMax = null;
// priceCallback уже объявлен выше (строка 22)
// currentEndpointIndex уже объявлен выше (строка 23)
let lastCachedData = null; // Кэш последних данных для fallback

/**
 * Инициализирует хук с Chart.js инстансом
 * @param {Chart} chart - Chart.js инстанс
 * @param {Function} onPriceUpdate - Callback для обновления цены (price, change)
 */
function initBinanceWebSocket(chart, onPriceUpdate) {
    chartInstance = chart;
    priceCallback = onPriceUpdate;
    console.log('🔌 [WebSocket] Initialized with chart instance');
}

/**
 * Загружает исторические свечи с Binance REST API с обработкой ошибок
 * @param {string} symbol - Торговая пара (например, 'BTCUSDT')
 * @param {string} interval - Таймфрейм ('1m', '5m', '1h', etc.)
 * @returns {Promise<{labels: string[], prices: number[], firstPrice: number, lastPrice: number}>}
 */
async function loadHistoricalCandles(symbol, interval) {
    const binanceInterval = BINANCE_INTERVALS[interval] || '15m';
    const limit = CANDLE_LIMITS[interval] || 96;

    // Нормализация символа: ВЕРХНИЙ регистр для REST API
    const normalizedSymbol = symbol.toUpperCase();

    console.log('📊 [Chart] Загрузка исторических данных...');
    console.log('📊 [Chart] Символ:', symbol, '→', normalizedSymbol);
    console.log('📊 [Chart] Таймфрейм:', interval, '(', binanceInterval, ')');
    console.log('📊 [Chart] Лимит свечей:', limit);

    // Пробуем каждый endpoint с timeout
    const endpointsToTry = [
        BINANCE_ENDPOINTS[currentEndpointIndex],
        ...BINANCE_ENDPOINTS.filter((_, i) => i !== currentEndpointIndex)
    ];

    for (let i = 0; i < endpointsToTry.length; i++) {
        const endpoint = endpointsToTry[i];
        console.log(`🔄 [Chart] Attempt ${i + 1}: Trying endpoint ${endpoint}`);

        try {
            const url = `${endpoint}/api/v3/klines?symbol=${normalizedSymbol}&interval=${binanceInterval}&limit=${limit}`;
            console.log('📊 [Chart] REST запрос URL:', url);

            // Создаем AbortController для timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                console.log('⏱️ [Chart] Request timeout exceeded');
                controller.abort();
            }, REQUEST_TIMEOUT_MS);

            const response = await fetch(url, {
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                }
            });
            clearTimeout(timeoutId);

            console.log('📊 [Chart] Статус ответа:', response.status, response.ok ? '✅' : '❌');

            // Обработка ошибки 451
            if (response.status === 451) {
                console.error('🚫 [Chart] Binance blocked request (451) from', endpoint);
                currentEndpointIndex = (currentEndpointIndex + 1) % BINANCE_ENDPOINTS.length;
                continue; // Пробуем следующий endpoint
            }

            if (!response.ok) {
                throw new Error(`Binance API error: ${response.status}`);
            }

            const data = await response.json();
            console.log('📊 [Chart] Получено свечей:', data.length);

            if (data.length > 0) {
                console.log('📊 [Chart] Первая свеча:', {
                    timestamp: new Date(data[0][0]).toISOString(),
                    open: parseFloat(data[0][1]),
                    close: parseFloat(data[0][4])
                });
                console.log('📊 [Chart] Последняя свеча:', {
                    timestamp: new Date(data[data.length - 1][0]).toISOString(),
                    open: parseFloat(data[data.length - 1][1]),
                    close: parseFloat(data[data.length - 1][4])
                });
            }

            const labels = [];
            const prices = [];
            let firstPrice = 0;
            let lastPrice = 0;

            data.forEach(candle => {
                // Формат свечи Binance: [timestamp, open, high, low, close, volume, ...]
                const timestamp = candle[0];
                const close = parseFloat(candle[4]);
                const time = new Date(timestamp);

                labels.push(time.toISOString());
                prices.push(close);
            });

            if (prices.length > 0) {
                firstPrice = prices[0];
                lastPrice = prices[prices.length - 1];
                
                // Кэшируем успешные данные для fallback
                lastCachedData = { labels: [...labels], prices: [...prices] };
                console.log('💾 [Chart] Cached data for fallback:', prices.length, 'prices');
            }

            console.log('📊 [Chart] Обработано данных - labels:', labels.length, 'prices:', prices.length);
            console.log('📊 [Chart] Диапазон цен:', firstPrice.toFixed(2), '-', lastPrice.toFixed(2));

            return { labels, prices, firstPrice, lastPrice };

        } catch (error) {
            console.error(`❌ [Chart] Error from endpoint ${endpoint}:`, error.message);
            
            // Переключаемся на следующий endpoint при ошибке
            currentEndpointIndex = (currentEndpointIndex + 1) % BINANCE_ENDPOINTS.length;
            
            // Если это была ошибка timeout или network error, продолжаем пробовать другие endpoints
            if (error.name === 'AbortError' || error.message.includes('Failed to fetch')) {
                console.log('🔄 [Chart] Will try next endpoint...');
                continue;
            }
            
            // Для других ошибок тоже пробуем следующий endpoint
            continue;
        }
    }

    // Все endpoints не сработали - используем fallback
    console.error('🚫 [Chart] All Binance endpoints failed, using fallback');
    
    if (lastCachedData && lastCachedData.prices.length > 0) {
        console.log('💾 [Chart] Using cached fallback data:', lastCachedData.prices.length, 'prices');
        return {
            labels: lastCachedData.labels,
            prices: lastCachedData.prices,
            firstPrice: lastCachedData.prices[0],
            lastPrice: lastCachedData.prices[lastCachedData.prices.length - 1]
        };
    }

    // Если кэша нет - возвращаем пустые данные с ошибкой
    throw new Error('Binance API unavailable and no cached data');
}

/**
 * Подключается к Binance WebSocket для обновления в реальном времени
 * @param {string} symbol - Торговая пара (например, 'BTCUSDT')
 * @param {Function} onTrade - Callback для каждой новой сделки (price, timestamp)
 */
function connectWebSocket(symbol, onTrade) {
    // Закрываем предыдущее соединение если есть
    disconnectWebSocket();

    // Нормализация символа: НИЖНИЙ регистр для WebSocket
    const wsSymbol = symbol.toLowerCase();

    const streamName = `${wsSymbol}@trade`;
    const wsUrl = `wss://stream.binance.com:9443/ws/${streamName}`;

    console.log('🔌 [WebSocket] Подключение к Binance WebSocket...');
    console.log('🔌 [WebSocket] URL:', wsUrl);
    console.log('🔌 [WebSocket] Символ:', symbol, '→', wsSymbol);

    try {
        binanceWebSocket = new WebSocket(wsUrl);
        webSocketBuffer = [];

        console.log('🔌 [WebSocket] Статус после создания:',
            binanceWebSocket.readyState === WebSocket.CONNECTING ? 'CONNECTING' :
            binanceWebSocket.readyState === WebSocket.OPEN ? 'OPEN' :
            binanceWebSocket.readyState === WebSocket.CLOSING ? 'CLOSING' : 'CLOSED');

        // Функция обновления графика из буфера
        function updateChartFromBuffer() {
            if (webSocketBuffer.length === 0 || !chartInstance) {
                console.log('🔌 [WebSocket] Пропуск обновления: буфер пуст или нет chartInstance');
                return;
            }

            // Получаем последнюю цену из буфера
            const lastTrade = webSocketBuffer[webSocketBuffer.length - 1];
            const lastPrice = lastTrade.price;
            const lastTimestamp = lastTrade.timestamp;

            console.log('🔌 [WebSocket] Обновление графика: цена =', lastPrice.toFixed(2));

            // Добавляем новую точку на график
            currentChartLabels.push(lastTimestamp.toISOString());
            currentChartPrices.push(lastPrice);

            // Удаляем старые точки для оптимизации
            const maxPoints = 100; // Держим последние 100 точек
            while (currentChartLabels.length > maxPoints) {
                currentChartLabels.shift();
                currentChartPrices.shift();
            }

            // Проверяем и обновляем масштаб Y если цена вышла за границы
            if (chartYMin !== null && chartYMax !== null) {
                const threshold = 0.1; // 10% от границ
                if (lastPrice > chartYMax * (1 - threshold) || lastPrice < chartYMin * (1 + threshold)) {
                    console.log('🔌 [WebSocket] Пересчёт масштаба Y: цена вышла за границы');
                    recalculateYScale();
                }
            }

            // Обновляем график БЕЗ полной перерисовки
            updateChart();
            console.log('🔌 [WebSocket] График обновлён, точек на графике:', currentChartPrices.length);

            // Вызываем callback для обновления UI
            if (priceCallback) {
                priceCallback(lastPrice);
            }

            // Вызываем callback для каждой сделки
            if (onTrade) {
                onTrade(lastPrice, lastTimestamp);
            }

            // Очищаем буфер
            webSocketBuffer = [];
        }

        // Обработчик входящих сообщений
        binanceWebSocket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                const price = parseFloat(data.p);
                const timestamp = new Date(data.T);

                console.log('🔌 [WebSocket] Получено сообщение: price =', price.toFixed(2));

                // Добавляем в буфер
                webSocketBuffer.push({ price, timestamp });

                // Debounce обновления для плавности (обновляем каждые 200мс)
                if (webSocketUpdateTimeout) {
                    clearTimeout(webSocketUpdateTimeout);
                }

                webSocketUpdateTimeout = setTimeout(() => {
                    updateChartFromBuffer();
                }, 200);
            } catch (error) {
                console.error('❌ [WebSocket] Error parsing message:', error);
            }
        };

        // Обработчик ошибок
        binanceWebSocket.onerror = function(err) {
            console.error('❌ [WebSocket] Binance WebSocket error:', err);
        };

        // Обработчик открытия соединения
        binanceWebSocket.onopen = function() {
            console.log('✅ [WebSocket] WebSocket соединение открыто!');
        };

        // Обработчик закрытия - авто-реконнект
        binanceWebSocket.onclose = function() {
            console.log('🔌 [WebSocket] Binance WebSocket закрыт, переподключение через 5с...');
            if (webSocketUpdateTimeout) {
                clearTimeout(webSocketUpdateTimeout);
            }
            setTimeout(() => {
                if (binanceWebSocket && binanceWebSocket.readyState === WebSocket.CLOSED) {
                    connectWebSocket(symbol, onTrade);
                }
            }, 5000);
        };

        return binanceWebSocket;
    } catch (error) {
        console.error('❌ [WebSocket] Failed to create WebSocket:', error);
        return null;
    }
}

/**
 * Отключается от WebSocket
 */
function disconnectWebSocket() {
    if (binanceWebSocket) {
        console.log('🔌 [WebSocket] Disconnecting WebSocket...');
        binanceWebSocket.close();
        binanceWebSocket = null;
    }
    if (webSocketUpdateTimeout) {
        clearTimeout(webSocketUpdateTimeout);
        webSocketUpdateTimeout = null;
    }
    webSocketBuffer = [];
}

/**
 * Обновляет данные графика
 * @param {string[]} labels - Метки времени
 * @param {number[]} prices - Цены
 */
function updateChartData(labels, prices) {
    currentChartLabels = [...labels];
    currentChartPrices = [...prices];
    recalculateYScale();
    updateChart();
    console.log('📊 [Chart] Chart data updated:', prices.length, 'points');
}

/**
 * Пересчитывает масштаб Y оси
 */
function recalculateYScale() {
    if (currentChartPrices.length === 0) return;

    const minPrice = Math.min(...currentChartPrices);
    const maxPrice = Math.max(...currentChartPrices);
    const range = maxPrice - minPrice;
    const padding = range > 0 ? range * 0.15 : minPrice * 0.15;

    chartYMin = minPrice - padding;
    chartYMax = maxPrice + padding;

    if (chartInstance && chartInstance.options.scales?.y) {
        chartInstance.options.scales.y.min = chartYMin;
        chartInstance.options.scales.y.max = chartYMax;
    }
}

/**
 * Обновляет Chart.js график
 */
function updateChart() {
    if (!chartInstance) {
        console.warn('⚠️ [Chart] No chart instance to update');
        return;
    }

    chartInstance.data.labels = currentChartLabels;
    chartInstance.data.datasets[0].data = currentChartPrices;

    // Обновляем БЕЗ анимации для производительности
    chartInstance.update('none');
    console.log('📊 [Chart] Chart rendered');
}

/**
 * Получает текущие данные графика
 * @returns {{labels: string[], prices: number[]}}
 */
function getChartData() {
    return {
        labels: [...currentChartLabels],
        prices: [...currentChartPrices]
    };
}

/**
 * Устанавливает callback для обновления цены
 * @param {Function} callback - (price: number) => void
 */
function setPriceCallback(callback) {
    priceCallback = callback;
}

/**
 * Полный цикл: загрузка истории + подключение WebSocket
 * @param {string} symbol - Торговая пара
 * @param {string} interval - Таймфрейм
 * @param {Chart} chart - Chart.js инстанс
 * @param {Function} onPriceUpdate - Callback для обновления цены
 * @param {Function} onTrade - Callback для каждой сделки
 */
async function initializeChart(symbol, interval, chart, onPriceUpdate, onTrade) {
    console.log('🚀 [Chart] Initializing chart for', symbol, interval);
    
    // Инициализируем
    initBinanceWebSocket(chart, onPriceUpdate);

    // Загружаем исторические данные с timeout
    let historicalData;
    try {
        historicalData = await loadHistoricalCandles(symbol, interval);
    } catch (error) {
        console.error('❌ [Chart] Failed to load historical data:', error);
        throw error;
    }

    // Обновляем график
    updateChartData(historicalData.labels, historicalData.prices);

    // Подключаем WebSocket
    connectWebSocket(symbol, onTrade);

    return { 
        firstPrice: historicalData.firstPrice, 
        lastPrice: historicalData.lastPrice 
    };
}

/**
 * Сбрасывает состояние при смене таймфрейма
 */
function resetOnIntervalChange() {
    console.log('🔄 [Chart] Resetting on interval change');
    disconnectWebSocket();
    currentChartLabels = [];
    currentChartPrices = [];
    chartYMin = null;
    chartYMax = null;
    if (webSocketUpdateTimeout) {
        clearTimeout(webSocketUpdateTimeout);
    }
}

/**
 * Получает статус загрузки данных
 * @returns {{hasData: boolean, fromCache: boolean, error: string|null}}
 */
function getDataStatus() {
    const hasData = currentChartPrices.length > 0;
    const fromCache = lastCachedData !== null;
    
    return {
        hasData,
        fromCache,
        error: hasData ? null : 'No data available'
    };
}

// Экспорт для совместимости с существующим кодом
window.useBinanceWebSocket = {
    initBinanceWebSocket,
    loadHistoricalCandles,
    connectWebSocket,
    disconnectWebSocket,
    updateChartData,
    getChartData,
    setPriceCallback,
    initializeChart,
    resetOnIntervalChange,
    getDataStatus
};

console.log('✅ [WebSocket] useBinanceWebSocket module loaded');
